from app.shared import normalize_key


def selected_key(name, choices):
    return normalize_key(name) in choices
