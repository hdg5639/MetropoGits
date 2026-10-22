from app.shared import normalize_key


def relative_name(name):
    return "./" + normalize_key(name)
