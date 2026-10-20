"""Code-purpose nonradial commons, with actual role/relationship anchors."""

from .campus_fabric import Fabric
from .source_programs import member_programs, program_summary

VERSION = "campus-plan/0.7"


class ProgrammedFabric(Fabric):
    def __init__(self, zone, polygon, axis, seed, roads):
        super().__init__(polygon, axis, seed, roads)
        self.summary = program_summary(zone)
        self.members = member_programs(zone)
        self.first = dict(
            VALIDATION=1, DATA=2, INTERFACE=0, APPLICATION=1, COMPUTE=2, TOOLING=0
        ).get(self.summary["kind"], self.first)

    def outline(self, center, axis, index, outer):
        # Shape the commons by source purpose while retaining fitted street axes.
        # Convex transforms keep the existing feasibility/fallback gates exact.
        from .geometry import point
        import math

        original = super().outline(center, axis, index, outer)
        yaw = self.bearing(center, index)
        c, s = math.cos(yaw), math.sin(yaw)
        u, v = dict(
            VALIDATION=(0.95, 0.9),
            DATA=(1.15, 0.72),
            INTERFACE=(1.05, 1.05),
            APPLICATION=(1.0, 0.85),
            COMPUTE=(0.9, 1.0),
            TOOLING=(1.1, 0.8),
        ).get(self.summary["kind"], (1, 1))
        return [
            point(
                [
                    center[0]
                    + c * ((p[0] - center[0]) * c + (p[1] - center[1]) * s) * u
                    - s * (-(p[0] - center[0]) * s + (p[1] - center[1]) * c) * v,
                    center[1]
                    + s * ((p[0] - center[0]) * c + (p[1] - center[1]) * s) * u
                    + c * (-(p[0] - center[0]) * s + (p[1] - center[1]) * c) * v,
                ]
            )
            for p in original
        ]

    def anchor(self, ids, degree, links, chosen):
        def score(key):
            kinds = set(self.members.get(key, {}).get("kinds", ()))
            previous = {
                k for a in chosen for k in self.members.get(a, {}).get("kinds", ())
            }
            # First anchor represents dominant use; later anchors retain mixed,
            # related supporting roles rather than sorting every role into a bin.
            purpose = (
                (1.8 if self.summary["kind"] in kinds else 1)
                if not chosen
                else (1.5 if kinds - previous else 1)
            )
            linked = sum(links[key].get(a, 0) for a in chosen)
            return (
                -purpose * (degree[key] + min(3, linked)) / (1 + linked * 0.25),
                key,
            )

        return min((k for k in ids if k not in chosen), key=score)


def programmed_layout(zone, polygon, axis, seed, roads, terrain, pairs, stats):
    from .campus_neighborhood import neighborhood_layout

    form = ProgrammedFabric(zone, polygon, axis, seed, roads)
    result = neighborhood_layout(
        zone, polygon, axis, seed, roads, terrain, pairs, stats, _form=form
    )
    if result is None:
        from .campus_fabric import fabric_layout

        result = fabric_layout(zone, polygon, axis, seed, roads, terrain, pairs, stats)
        stats["programFallback"] = "FULL_CAPACITY_OR_ACCESS"
    annotate_program(zone, result)
    return result


def annotate_program(zone, result):
    if result is not None:
        site = result[2]
        members = member_programs(zone)
        site["sourceProgram"] = program_summary(zone)
        for group in site["activityCenters"]:
            member = members.get(group["anchorEntityId"], {})
            group["programRoles"] = member.get("roles", [])
            group["programEvidenceIds"] = member.get("evidenceIds", [])
