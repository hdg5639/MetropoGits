from app.shared import normalize_key


def export_name(name):
    return normalize_key(name) + ".txt"
