"""Exclude JSX subtrees from lexical module/call matching, never parse UI text.

Embedded JSX expressions also need an expression parser; omit them explicitly.
"""


def code_without_jsx(tokens):
    def tag(i):
        if i >= len(tokens) or tokens[i].value != "<":
            return None
        j = i + 1
        closing = j < len(tokens) and tokens[j].value == "/"
        j += closing
        name = []
        if j < len(tokens) and tokens[j].kind == "IDENT":
            name.append(tokens[j].value)
            j += 1
            while (
                j + 1 < len(tokens)
                and tokens[j].value in {".", "-", ":"}
                and tokens[j + 1].kind == "IDENT"
            ):
                name.extend((tokens[j].value, tokens[j + 1].value))
                j += 2
        if not name and (j >= len(tokens) or tokens[j].value != ">"):
            return None
        depth = 0
        for end in range(j, min(len(tokens), j + 256)):
            value = tokens[end].value
            depth += value == "{"
            depth -= value == "}"
            if value == ">" and depth == 0:
                return "".join(name), closing, end, tokens[end - 1].value == "/"
            if value == ";" and depth == 0:
                break
        return None

    closers = set()
    for i, token in enumerate(tokens):
        if token.value == "<":
            parsed = tag(i)
            if parsed and parsed[1]:
                closers.add(parsed[0])
    result, regions = [], []
    i = 0
    while i < len(tokens):
        parsed = tag(i) if tokens[i].value == "<" else None
        if not parsed or parsed[1] or (not parsed[3] and parsed[0] not in closers):
            result.append(tokens[i])
            i += 1
            continue
        name, _, end, single = parsed
        start = i
        i = end + 1
        if not single:
            depth = 1
            while i < len(tokens) and depth:
                nested = tag(i) if tokens[i].value == "<" else None
                if nested and nested[0] == name:
                    depth += -1 if nested[1] else (not nested[3])
                    i = nested[2] + 1
                else:
                    i += 1
        regions.append((tokens[start].line, tokens[i - 1].line))
    return tuple(result), regions
