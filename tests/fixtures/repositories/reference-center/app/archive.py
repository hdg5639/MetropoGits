from app.shared import normalize_key


def archive_key(name):
    return "archive/" + normalize_key(name)
