from app.shared import normalize_key


def report_heading(name):
    return "Report: " + normalize_key(name)
