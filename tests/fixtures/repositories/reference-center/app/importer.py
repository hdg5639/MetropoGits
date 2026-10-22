from app.shared import normalize_key


def import_name(name):
    return normalize_key(name.removesuffix(".txt"))
