"""Bounded internal geography prepass; no cached file or routed World required."""

from dataclasses import dataclass
from functools import wraps

VERSION = "campus-bootstrap/0.1"


@dataclass
class PlanningFrame:
    """Private transient layout hint, NOT a complete/exportable World artifact."""

    hint: dict


def cold_start(function):
    @wraps(function)
    def generate(scene, graph, **options):
        enabled = options.pop("campus_bootstrap", False)
        if not isinstance(enabled, bool):
            raise ValueError("campus bootstrap must be a boolean")
        if not enabled:
            return function(scene, graph, **options)
        if options.get("previous") is not None:
            raise ValueError("campus bootstrap cannot also use a previous World")
        if not options.get("campus") or options.get("campus_style") != "precinct":
            raise ValueError("campus bootstrap requires --campus --campus-style precinct")
        frame = function(scene, graph, **dict(options, campus_style="programmed", _planning_frame=True))
        if not isinstance(frame, PlanningFrame):
            raise ValueError("campus bootstrap did not produce a planning frame")
        world = function(scene, graph, **dict(options, previous=frame.hint))
        world["diagnostics"].append(dict(
            reason="deterministic internal geography bootstrap",
            version=VERSION, source="INTERNAL_PLANNING_NOT_CACHED_WORLD",
            baselineCampusStyle="programmed", requestedCampusStyle="precinct",
            actualCampusStyle=world.get("campusPlan", {}).get("style"),
            planningPasses=1, baselineRoutingPasses=0,
        ))
        return world
    return generate
