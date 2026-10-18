"""Narrow module-local output declaration, not a general gitignore engine."""
from fnmatch import fnmatchcase

MAX_DECLARATION_BYTES = 64 * 1024
JVM_MANIFESTS = frozenset({"pom.xml", "build.gradle", "build.gradle.kts"})


def declares_local_bin_output(content: bytes) -> bool:
    """Only exact bin/ declarations qualify; respect later root-bin negations.

    The only candidate is the immediate directory `bin`, so patterns requiring
    a named parent (e.g. **/src/**/bin/) cannot match it. Unknown escapes in a
    negation fail open for scanning: preserve files, never guess an exclusion.
    """
    if len(content) > MAX_DECLARATION_BYTES:
        raise ValueError("Output declaration exceeds limit")
    text = content.decode("utf-8-sig")
    if "\x00" in text:
        raise ValueError("Invalid output declaration")
    declared = False
    for line in text.splitlines():
        pattern = line.rstrip(" ")
        if pattern in {"bin/", "/bin/"}:
            declared = True
        elif pattern.startswith("!"):
            pattern = pattern[1:]
            if "\\" in pattern or "[" in pattern or "]" in pattern:
                return False
            parts = pattern.removeprefix("/").removesuffix("/").split("/")
            # ** matches zero directories; any other parent requires a depth
            # unavailable to the immediate module-root `bin` candidate.
            if all(part == "**" for part in parts[:-1]) and fnmatchcase("bin", parts[-1]):
                declared = False
    return declared
