"""Extract actual HTML script data, not script-looking comments or templates."""

from html.parser import HTMLParser

from .common import AnalysisError


def script_source(source):
    offsets = [0]
    for i, char in enumerate(source):
        if char == "\n":
            offsets.append(i + 1)
    result = ["\n" if char == "\n" else " " for char in source]

    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.active = False
            self.blocks = 0

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.blocks += 1
                if self.blocks > 64:
                    raise AnalysisError("component script block limit")
                self.active = True

        def handle_endtag(self, tag):
            if tag == "script":
                self.active = False

        def handle_data(self, data):
            if self.active:
                row, col = self.getpos()
                start = offsets[row - 1] + col
                result[start : start + len(data)] = data

    parser = Scripts()
    parser.feed(source)
    parser.close()
    if parser.active:
        raise AnalysisError("unterminated component script")
    return "".join(result)
