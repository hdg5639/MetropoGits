from app.shared import normalize_key


def history_key(name, revision):
    return normalize_key(name) + ":" + str(revision)
