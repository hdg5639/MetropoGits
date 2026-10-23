"""Closed, outward-facing lofted meshes for contemporary and near-future massing.

Every mesh lives in the unit cube like the older primitives, so the existing
envelope, collision and yaw handling stay valid. These are presentation shapes
for source-backed envelopes; they never claim extra source entities.
"""

import math

ROUND_SIDES = 12


def _rounded(scale=1.0, sides=ROUND_SIDES, exponent=0.5):
    """Squircle ring (rounded-rectangle plan), increasing angle like DRUM."""
    ring = []
    for i in range(sides):
        angle = math.tau * (i + 0.5) / sides
        c, s = math.cos(angle), math.sin(angle)
        x = math.copysign(abs(c) ** exponent, c)
        z = math.copysign(abs(s) ** exponent, s)
        ring.append([0.5 + 0.5 * scale * x, 0.5 + 0.5 * scale * z])
    return ring


def _square(scale=1.0, turn=0.0, cx=0.5, cz=0.5, half_x=0.5, half_z=0.5):
    """Four-corner ring, shrunk so any turn stays inside the unit footprint."""
    fit = 1 / (abs(math.cos(turn)) + abs(math.sin(turn)))
    ring = []
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, z = sx * half_x * scale * fit, sz * half_z * scale * fit
        ring.append(
            [
                cx + x * math.cos(turn) - z * math.sin(turn),
                cz + x * math.sin(turn) + z * math.cos(turn),
            ]
        )
    return ring


def _loft(levels, apex=None):
    """levels: [(y, ring)] bottom to top. apex closes the top to one point."""
    faces = [([[x, levels[0][0], z] for x, z in levels[0][1]], "wall")]
    for (y0, low), (y1, high) in zip(levels, levels[1:]):
        for i in range(len(low)):
            j = (i + 1) % len(low)
            faces.append(
                (
                    [
                        [low[i][0], y0, low[i][1]],
                        [high[i][0], y1, high[i][1]],
                        [high[j][0], y1, high[j][1]],
                        [low[j][0], y0, low[j][1]],
                    ],
                    "wall",
                )
            )
    top_y, top = levels[-1]
    if apex is None:
        faces.append((list(reversed([[x, top_y, z] for x, z in top])), "roof"))
    else:
        for i in range(len(top)):
            j = (i + 1) % len(top)
            faces.append(
                (
                    [[top[i][0], top_y, top[i][1]], [apex[0], apex[1], apex[2]], [top[j][0], top_y, top[j][1]]],
                    "roof",
                )
            )
    return faces


def _wedge():
    """Glass block with one sloped roof plane (high on -z, low on +z)."""
    hi, lo = 1.0, 0.52
    p = lambda x, y, z: [x, y, z]
    return [
        ([p(0, 0, 0), p(1, 0, 0), p(1, 0, 1), p(0, 0, 1)], "wall"),
        ([p(0, 0, 0), p(0, hi, 0), p(1, hi, 0), p(1, 0, 0)], "wall"),
        ([p(1, 0, 1), p(1, lo, 1), p(0, lo, 1), p(0, 0, 1)], "wall"),
        ([p(0, 0, 1), p(0, lo, 1), p(0, hi, 0), p(0, 0, 0)], "wall"),
        ([p(1, 0, 0), p(1, hi, 0), p(1, lo, 1), p(1, 0, 1)], "wall"),
        ([p(0, hi, 0), p(0, lo, 1), p(1, lo, 1), p(1, hi, 0)], "roof"),
    ]


def contemporary_faces(shape):
    """Return unit meshes, or None when the primitive is not a contemporary one."""
    if shape == "ROUNDED":
        return _loft([(0, _rounded()), (1, _rounded())])
    if shape == "TAPER":
        return _loft([(0, _rounded()), (0.5, _rounded(0.86)), (1, _rounded(0.62))])
    if shape == "TWIST":
        steps = 6
        return _loft(
            [(i / steps, _square(1 - 0.34 * i / steps, math.radians(46) * i / steps)) for i in range(steps + 1)]
        )
    if shape == "LEAN":
        return _loft(
            [
                (0, _square(1, 0, 0.35, 0.5, 0.35, 0.5)),
                (1, _square(1, 0, 0.65, 0.5, 0.35, 0.5)),
            ]
        )
    if shape == "SPIRE":
        return _spire()
    if shape == "WEDGE":
        return _wedge()
    return None


def _spire():
    base = _square(1)
    faces = [([[x, 0, z] for x, z in base], "wall")]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(([[base[i][0], 0, base[i][1]], [0.5, 1, 0.5], [base[j][0], 0, base[j][1]]], "wall"))
    return faces


CONTEMPORARY_SHAPES = ("ROUNDED", "TAPER", "TWIST", "LEAN", "SPIRE", "WEDGE")
