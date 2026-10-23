"""Contemporary / near-future compositions chosen by district character.

A district's derived planning typology and its position in the height field
decide which architectural vocabulary appears: supertall spires in a
metropolitan core, wedge-roof glass and sky-bridges in a technology district,
terraced mid-rise in mixed use, rotunda and pavilion fabric in a campus.
All of this is presentation massing inside the allocated source envelope, never
additional source evidence. Industrial halls keep their purpose-built sheds
unless the district shows verified data/compute character.
"""

GLASS, STONE, METAL = 2, 1, 4

TOWER_PREFERENCE = {
    "METROPOLITAN_CORE": ("spire", "twist", "crown", "twins", "pairs", "finned"),
    "DENSE_BUSINESS": ("crown", "terraced", "spire", "finned", "twins", "slope"),
    "TECHNOLOGY_BUSINESS": ("slope", "twins", "stack", "finned", "twist", "pairs"),
    "POLYCENTRIC": ("terraced", "crown", "stack", "spire", "slope"),
    "CONVENTIONAL_MIXED_USE": ("terraced", "stack", "slope", "finned"),
    "COMMERCIAL_CULTURAL": ("terraced", "finned", "slope", "stack"),
}
BAR_PREFERENCE = {
    "METROPOLITAN_CORE": ("canopy", "cantilever"),
    "DENSE_BUSINESS": ("canopy", "cantilever", "wedge"),
    "TECHNOLOGY_BUSINESS": ("wedge", "cantilever", "canopy"),
    "POLYCENTRIC": ("cantilever", "wedge", "canopy"),
    "CONVENTIONAL_MIXED_USE": ("cantilever", "canopy"),
    "COMMERCIAL_CULTURAL": ("canopy", "wedge", "cantilever"),
}
ALL_TOWERS = ("spire", "twist", "twins", "terraced", "slope", "crown", "pairs", "stack", "finned")
ALL_BARS = ("canopy", "wedge", "cantilever")


def _towers(b, width):
    podium = b(.02, 0, .03, .96, .09, .94, "ROUNDED", STONE)
    wide = width >= 11
    return {
        "spire": ("TAPERED_SPIRE_TOWER", [podium,
            b(.15, .09, .15, .70, .78, .70, "TAPER", GLASS),
            b(.27, .87, .27, .46, .035, .46, "ROUNDED", METAL),
            b(.44, .905, .44, .12, .095, .12, "SPIRE", METAL),
            b(.30, .09, .05, .40, .12, .10, "ROUNDED", GLASS)]),
        "twist": ("TWISTED_GLASS_TOWER", [podium,
            b(.13, .09, .13, .74, .80, .74, "TWIST", GLASS),
            b(.32, .89, .32, .36, .03, .36, "ROUNDED", METAL),
            b(.455, .92, .455, .09, .08, .09, "SPIRE", METAL)]),
        "twins": ("LEANING_TWIN_TOWERS_WITH_SKYBRIDGES", [podium,
            b(.04, .09, .14, .40, .86, .66, "LEAN", GLASS),
            b(.56, .09, .14, .38, .66, .66, "TAPER", GLASS),
            b(.40, .42, .38, .22, .05, .20, "ROUNDED", METAL),
            b(.40, .30, .38, .22, .05, .20, "ROUNDED", METAL),
            b(.62, .75, .30, .06, .13, .06, "SPIRE", METAL)]) if wide else None,
        "terraced": ("TERRACED_SKY_GARDEN_TOWER", [podium,
            b(.09, .09, .11, .82, .32, .78, "ROUNDED", GLASS),
            b(.17, .41, .17, .66, .27, .66, "ROUNDED", GLASS),
            b(.25, .68, .24, .50, .20, .52, "TAPER", GLASS),
            b(.13, .41, .72, .60, .02, .14, "ROUNDED", METAL),
            b(.20, .68, .78, .52, .02, .12, "ROUNDED", METAL),
            b(.44, .88, .45, .12, .12, .10, "SPIRE", METAL)]),
        "slope": ("SLOPED_CROWN_GLASS_SLAB", [podium,
            b(.10, .09, .16, .80, .78, .64, "WEDGE", GLASS),
            b(.10, .09, .80, .80, .16, .16, "ROUNDED", GLASS)]),
        "crown": ("TAPERED_TWISTED_CROWN_TOWER", [podium,
            b(.18, .09, .18, .64, .60, .64, "TAPER", GLASS),
            b(.28, .69, .28, .44, .17, .44, "TWIST", GLASS),
            b(.46, .86, .46, .08, .14, .08, "SPIRE", METAL),
            b(.04, .09, .40, .18, .26, .30, "ROUNDED", GLASS)]),
        "pairs": ("PAIRED_CURVED_TOWERS_ON_SHARED_PODIUM", [podium,
            b(.05, .09, .12, .42, .74, .70, "TAPER", GLASS),
            b(.54, .09, .20, .40, .52, .62, "TAPER", GLASS),
            b(.44, .30, .36, .14, .05, .26, "ROUNDED", METAL),
            b(.12, .83, .30, .06, .17, .06, "SPIRE", METAL)]) if wide else None,
        "stack": ("SHIFTED_CANTILEVER_STACK_TOWER", [podium,
            b(.10, .09, .14, .62, .34, .66, "ROUNDED", GLASS),
            b(.22, .43, .14, .72, .30, .66, "ROUNDED", GLASS),
            b(.12, .73, .16, .62, .20, .62, "ROUNDED", GLASS),
            b(.12, .93, .18, .58, .03, .58, "ROUNDED", METAL),
            b(.30, .43, .80, .50, .02, .16, "ROUNDED", METAL)]),
        "finned": ("FINNED_ELLIPTICAL_TOWER", [podium,
            b(.18, .09, .14, .64, .80, .72, "ROUNDED", GLASS),
            b(.14, .09, .30, .04, .70, .40, "ROUNDED", METAL),
            b(.82, .09, .30, .04, .70, .40, "ROUNDED", METAL),
            b(.26, .89, .26, .48, .03, .48, "ROUNDED", METAL),
            b(.46, .92, .46, .08, .08, .08, "SPIRE", METAL)]),
    }


def _bars(b):
    return {
        "canopy": ("CURVED_GLASS_BAR_WITH_CANOPY", [
            b(.03, 0, .08, .94, .08, .84, "ROUNDED", STONE),
            b(.05, .08, .10, .90, .50, .62, "ROUNDED", GLASS),
            b(.02, .58, .06, .96, .035, .78, "ROUNDED", METAL),
            b(.30, .08, .70, .40, .22, .24, "ROUNDED", GLASS)]),
        "wedge": ("WEDGE_ATRIUM_BLOCK", [
            b(.04, 0, .08, .92, .14, .84, "ROUNDED", STONE),
            b(.06, .14, .10, .60, .62, .70, "WEDGE", GLASS),
            b(.64, .14, .36, .30, .34, .50, "ROUNDED", GLASS),
            b(.64, .48, .30, .34, .03, .62, "ROUNDED", METAL)]),
        "cantilever": ("CANTILEVERED_CURTAIN_WALL_BAR", [
            b(.04, 0, .10, .34, .50, .80, "ROUNDED", STONE),
            b(.10, .30, .10, .88, .36, .80, "ROUNDED", GLASS),
            b(.10, .66, .12, .84, .03, .76, "ROUNDED", METAL),
            b(.52, 0, .20, .12, .30, .60, "ROUNDED", METAL)]),
    }


def _campus(b, pick):
    """Low, landscaped research fabric: rotundas, pavilions and glazed forums."""
    variants = [
        ("CAMPUS_ROTUNDA_AND_WINGS", [
            b(.04, 0, .12, .28, .36, .76, "ROUNDED", GLASS),
            b(.68, 0, .12, .28, .44, .76, "ROUNDED", GLASS),
            b(.30, 0, .24, .40, .40, .52, "DOME", GLASS),
            b(.30, .40, .30, .40, .035, .40, "ROUNDED", METAL),
            b(.34, 0, .84, .32, .06, .12, "ROUNDED", STONE)]),
        ("RESEARCH_PAVILION_RING", [
            b(.04, 0, .06, .40, .30, .38, "ROUNDED", GLASS),
            b(.56, 0, .06, .40, .38, .38, "ROUNDED", GLASS),
            b(.04, 0, .58, .40, .26, .36, "ROUNDED", GLASS),
            b(.56, 0, .58, .40, .30, .36, "ROUNDED", GLASS),
            b(.36, 0, .36, .28, .20, .28, "DOME", GLASS),
            b(.44, .02, .44, .12, .30, .12, "SPIRE", METAL)]),
        ("LABORATORY_SPINE_WITH_FORUM", [
            b(.04, 0, .30, .92, .34, .36, "ROUNDED", GLASS),
            b(.10, .34, .34, .50, .03, .28, "ROUNDED", METAL),
            b(.06, 0, .66, .26, .22, .28, "WEDGE", GLASS),
            b(.68, 0, .04, .26, .46, .26, "TAPER", GLASS),
            b(.40, 0, .66, .22, .16, .26, "ROUNDED", STONE)]),
    ]
    return variants[pick % len(variants)]


def _works(b, pick):
    """Data/compute works: arched halls, stacks and a glazed control wing."""
    return ("ROUNDED_WORKS_WITH_STACKS", [
        b(.04, 0, .10, .92, .30, .56, "ROUNDED", METAL),
        b(.08, .30, .14, .84, .06, .48, "ROUNDED", METAL),
        b(.08, 0, .72, .09, .62, .12, "ROUNDED", METAL),
        b(.22, 0, .72, .09, .50, .12, "ROUNDED", METAL),
        b(.58, 0, .70, .36, .26, .26, "WEDGE", GLASS)])


def _choose(preferred, available, composition, fallback):
    pool = [name for name in preferred if available.get(name)] or [
        name for name in fallback if available.get(name)]
    return available[pool[composition % len(pool)]]


def contemporary_grammar(form, envelope, composition, character=None):
    """Return (specs, layout) for a contemporary form, or None to keep legacy."""
    from .architecture_catalog import part as b

    width = envelope["width"]
    typology = (character or {}).get("typology")
    intensity = (character or {}).get("intensity", 0.5)
    campus = (character or {}).get("campus", 0)
    industrial = (character or {}).get("industrial", 0)
    if form in ("pavilions", "pods", "verification") or (
            form in ("bar", "row", "court", "atrium", "terrace") and campus >= 0.35):
        name, specs = _campus(b, composition)
        return specs, name
    if form in ("warehouse", "sawtooth", "shed", "hall") and industrial >= 0.22:
        name, specs = _works(b, composition)
        return specs, name
    if form in ("tower", "twin"):
        preferred = TOWER_PREFERENCE.get(typology, ALL_TOWERS)
        if typology in ("METROPOLITAN_CORE", "DENSE_BUSINESS", "TECHNOLOGY_BUSINESS") and intensity < 0.3:
            preferred = TOWER_PREFERENCE["CONVENTIONAL_MIXED_USE"]  # fringe mid-rise
        elif intensity > 0.75 and typology in ("METROPOLITAN_CORE", "DENSE_BUSINESS"):
            preferred = ("spire", "twist", "crown") + tuple(preferred)
        name, specs = _choose(preferred, _towers(b, width), composition, ALL_TOWERS)
        return specs, name
    if form in ("bar", "row", "terrace"):
        name, specs = _choose(BAR_PREFERENCE.get(typology, ALL_BARS), _bars(b), composition, ALL_BARS)
        return specs, name
    if form in ("court", "atrium"):
        return [b(.04, 0, .06, .28, .62, .88, "ROUNDED", GLASS),
                b(.68, 0, .06, .28, .74, .88, "TAPER", GLASS),
                b(.32, 0, .22, .36, .40, .56, "DOME", GLASS),
                b(.30, .50, .30, .40, .045, .24, "ROUNDED", METAL),
                b(.32, 0, .86, .36, .08, .10, "ROUNDED", STONE)], "GLAZED_DOME_ATRIUM_BETWEEN_TOWERS"
    return None
