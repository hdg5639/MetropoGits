from app.shared import normalize_key


def index_key(name):
    return "index/" + normalize_key(name)
