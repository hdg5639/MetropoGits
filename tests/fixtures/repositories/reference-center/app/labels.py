from app.shared import normalize_key


def label_keys(values):
    return [normalize_key(value) for value in values]
