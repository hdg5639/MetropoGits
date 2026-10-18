"""Deterministic convex silhouettes, independent of local planning streams."""

import math

from metropogits.street_diagonals import hull
from .geometry import point
from .seed import derive, draw

VERSION = "seeded-convex/1"


def varied_outline(seed):
    stream = derive(seed, "world-outline", VERSION)
    family = ("compact", "elongated", "angular", "asymmetric")[int(draw(stream) * 4)]
    count = (6 if family == "angular" else 9) + int(draw(stream, 1) * 5)
    sx = (1.6 if family == "elongated" else 1.0) + draw(stream, 2) * 0.3
    sz = 0.75 + draw(stream, 3) * 0.3
    shear = (draw(stream, 4) - 0.5) * (0.9 if family == "asymmetric" else 0.25)
    rotation = draw(stream, 5) * math.tau
    c, s = math.cos(rotation), math.sin(rotation)
    vertices = []
    for i in range(count):
        theta = (i + (draw(stream, 6 + i * 2) - 0.5) * 0.4) * math.tau / count
        radius = 0.8 + draw(stream, 7 + i * 2) * 0.4
        x, z = math.cos(theta) * radius * sx, math.sin(theta) * radius * sz
        x += z * shear
        vertices.append(point([c * x - s * z, s * x + c * z]))
    return list(reversed(hull(vertices))), family
