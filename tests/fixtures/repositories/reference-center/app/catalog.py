from app.shared import normalize_key


def catalog_key(name):
    return "catalog/" + normalize_key(name)
