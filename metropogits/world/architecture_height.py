"""Derived architectural capacity, independent of the legacy source height."""

import math

from .geometry import inside, q, rectangle

VERSION = "physical-height/0.1"
# Envelope aspect ratios, NOT file metrics, incoming counts or importance.
# Large footprints can support larger volumes; there is no universal10-unit cap.
RATIOS = dict(
    tower=7,
    twin=6,
    mast=6,
    terrace=4.5,
    bar=3.5,
    court=3,
    atrium=3,
    gate=3.2,
    terminal=2,
    hall=1.6,
    vault=2,
    warehouse=1.5,
    sawtooth=1.5,
    archive=2.6,
    pods=2.2,
    hub=2,
    silos=2.8,
    dome=1.8,
    gantry=3,
    containers=1.1,
    gallery=2,
    arena=2,
    row=2.2,
    shed=1.4,
    pavilions=2.2,
    verification=2,
)


def height_capacity(source, form):
    if not all(math.isfinite(source[k]) and source[k] > 0 for k in ("width", "depth")):
        raise ValueError("invalid architectural height capacity")
    span = min(source["width"], source["depth"])
    if not math.isfinite(span) or span <= 0 or form not in RATIOS:
        raise ValueError("invalid architectural height capacity")
    result = q(span * RATIOS[form])
    if not math.isfinite(result) or result <= 0:
        raise ValueError("invalid architectural height capacity")
    return result


def validate_architectural_heights(original, styled, profiles):
    """Independent derived-view check, not a relaxation of World source checks."""
    from .architecture_catalog import CATALOG

    sources = {p["entityId"]: p for p in original["parcels"]}
    models = {p["entityId"]: p for p in styled["parcels"]}
    if (
        len(models) != len(styled["parcels"])
        or sources.keys() != models.keys()
        or sources.keys() != profiles.keys()
    ):
        raise ValueError("architectural height source conservation")
    for identity, source in sources.items():
        model, profile = models[identity], profiles[identity]
        policy = profile["heightPolicy"]
        if policy["form"] != CATALOG[profile["archetypeId"]]["grammar"]:
            raise ValueError("architectural height form mismatch")
        capacity = height_capacity(source, policy["form"])
        if policy != dict(
            version=VERSION,
            form=policy["form"],
            smallerSpan=q(min(source["width"], source["depth"])),
            ratio=RATIOS[policy["form"]],
            capacity=capacity,
            basis="ARCHITECTURAL_FORM_AND_FOOTPRINT",
            derived=True,
        ):
            raise ValueError("architectural height policy mismatch")
        if model["height"] != capacity or model["sourceHeight"] != source["height"]:
            raise ValueError("architectural height capacity mismatch")
        if any(
            model[k] != v for k, v in source.items() if k not in ("parts", "height")
        ):
            raise ValueError("architectural height changed source geography")
        footprint = rectangle(
            source["center"], source["angle"], source["width"], source["depth"]
        )
        for part in model["parts"]:
            if (
                not all(math.isfinite(part[k]) for k in ("y", "height"))
                or part["y"] < 0
                or part["height"] <= 0
                or part["y"] + part["height"] > capacity + 0.0004
            ):
                raise ValueError("architectural part escaped height capacity")
            if not all(inside(p, footprint, -0.0005) for p in part["footprint"]):
                raise ValueError("architectural part escaped footprint")
            for face in part.get("meshFaces", []):
                for x, y, z in face["points"]:
                    if (
                        not all(math.isfinite(v) for v in (x, y, z))
                        or not 0 <= y <= capacity + 0.0004
                        or not inside([x, z], footprint, -0.0005)
                    ):
                        raise ValueError("architectural mesh escaped capacity")
        if profile["renderedHeight"] != q(
            max(p["y"] + p["height"] for p in model["parts"])
        ):
            raise ValueError("architectural rendered height mismatch")
