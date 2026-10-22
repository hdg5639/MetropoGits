"""Bounded comment/literal-aware tokens for structural (not compiler) adapters."""

import re
from dataclasses import dataclass

from .common import AnalysisError

MAX_TOKENS = 200_000
RAW = re.compile(r'r(#{0,32})"')
CPP_RAW = re.compile(r'R"([^ ()\\\t\r\n]{0,16})\(')
LIFETIME = re.compile(r"'[A-Za-z_][A-Za-z0-9_]*")
CHARACTER = re.compile(r"'(?:[^'\\]|\\.)'")
LUA_LONG = re.compile(r"\[(=*)\[")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


def tokenize(source, language):
    tokens = []
    i, line = 0, 1
    while i < len(source):
        c = source[i]
        if c.isspace():
            line += c == "\n"
            i += 1
            continue
        lua_start = i + 2 if source.startswith("--", i) else i
        long = LUA_LONG.match(source, lua_start) if language == "lua" else None
        if long:
            closing = "]" + long[1] + "]"
            stop = source.find(closing, long.end())
            if stop < 0:
                raise AnalysisError("unterminated Lua long literal/comment")
            line += source[i : stop + len(closing)].count("\n")
            i = stop + len(closing)
            continue
        if (
            language == "ruby"
            and source.startswith("=begin", i)
            and (i == 0 or source[i - 1] == "\n")
        ):
            end = re.search(r"(?m)^=end\b", source[i:])
            if not end:
                raise AnalysisError("unterminated Ruby block comment")
            stop = i + end.end()
            line += source[i:stop].count("\n")
            i = stop
            continue
        if (
            source.startswith("//", i)
            or (c == "#" and language in {"ruby", "php"})
            or (source.startswith("--", i) and language == "lua")
        ):
            stop = source.find("\n", i)
            while language in {"c", "cpp"} and stop > 0 and source[stop - 1] == "\\":
                stop = source.find("\n", stop + 1)
            i = len(source) if stop < 0 else stop
            continue
        if source.startswith("/*", i):
            start, depth = i, 1
            i += 2
            while i < len(source) and depth:
                if source.startswith("/*", i) and language in {
                    "rust",
                    "kotlin",
                    "swift",
                    "scala",
                }:
                    depth += 1
                    if depth > 64:
                        raise AnalysisError("comment nesting limit")
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise AnalysisError("unterminated block comment")
            line += source[start:i].count("\n")
            continue
        raw = RAW.match(source, i) if language == "rust" and c == "r" else None
        cpp_raw = CPP_RAW.match(source, i) if language == "cpp" and c == "R" else None
        if raw or cpp_raw:
            match = raw or cpp_raw
            closing = ('"' + match[1]) if raw else (")" + match[1] + '"')
            stop = source.find(closing, i + len(match[0]))
            if stop < 0:
                raise AnalysisError("unterminated raw string")
            line += source[i : stop + len(closing)].count("\n")
            i = stop + len(closing)
            continue
        if c in "\"'`":
            # Rust lifetimes are identifiers, not unterminated character strings.
            if (
                c == "'"
                and language == "rust"
                and LIFETIME.match(source, i)
                and not CHARACTER.match(source, i)
            ):
                tokens.append(Token("PUNCT", c, line))
                i += 1
                continue
            quote = c * 3 if source.startswith(c * 3, i) else c
            start_line, begin = line, i + len(quote)
            i = begin
            escaped = False
            while i < len(source) and not source.startswith(quote, i):
                if source[i] == "\\" and c != "`":
                    escaped = True
                    i += 2
                else:
                    i += 1
            if i >= len(source):
                raise AnalysisError("unterminated string")
            value = source[begin:i]
            line += value.count("\n")
            tokens.append(
                Token(
                    "LITERAL"
                    if escaped or len(quote) > 1 or "\n" in value
                    else "STRING",
                    value if len(value) < 500 else "",
                    start_line,
                )
            )
            i += len(quote)
        elif c.isalpha() or c in "_$":
            stop = i + 1
            while stop < len(source) and (
                source[stop].isalnum() or source[stop] in "_$"
            ):
                stop += 1
            tokens.append(Token("IDENT", source[i:stop], line))
            i = stop
        else:
            tokens.append(Token("PUNCT", c, line))
            i += 1
        if len(tokens) > MAX_TOKENS:
            raise AnalysisError("token limit")
    return tuple(tokens)


def qualified(tokens, start, separators=(".",)):
    """Read names without swallowing the following statement or quoted text."""
    result = []
    i = start
    while i < len(tokens):
        token = tokens[i]
        if token.kind == "IDENT" or token.value == "*":
            result.append(token.value)
            i += 1
            if i < len(tokens) and tokens[i].value in separators:
                sep = tokens[i].value
                i += 1
                if sep == ":" and i < len(tokens) and tokens[i].value == ":":
                    i += 1
                continue
            break
        break
    return ".".join(result), i
