"""A small composable massing system, not more synonyms for thin boxes."""

from .seed import derive

VERSION = "urban-architecture/0.2"


def modern_grammar(form, envelope, seed):
    from .architecture_catalog import part as b, grammar

    composition = int(derive(seed, VERSION, "composition"), 16) % 8
    variant = composition % 4
    width, depth = envelope["width"], envelope["depth"]
    if form in ('warehouse', 'sawtooth', 'shed', 'hall'):
        if variant == 0:
            return [b(.04, 0, .06, .92, .45, .72, material=4),
                    b(.07, .45, .18, .86, .16, .42, 'SAWTOOTH', 4),
                    b(.54, 0, .79, .40, .3, .17, material=2)], 'ROOFLIT_HALL_AND_ADMINISTRATION_WING'
        if variant == 1:
            return [b(.04, 0, .06, .43, .53, .76, 'GABLE', 4),
                    b(.53, 0, .06, .43, .63, .76, 'GABLE', 4),
                    b(.10, 0, .84, .80, .2, .12, material=2),
                    b(.47, 0, .45, .06, .19, .26)], 'MULTIBAY_LOGISTICS_HALLS'
        if variant == 2:
            return [b(.04, 0, .05, .92, .32, .2),
                    b(.04, 0, .25, .29, .58, .68, 'SAWTOOTH', 4),
                    b(.61, 0, .25, .35, .47, .68, 'GABLE', 4),
                    b(.33, 0, .25, .28, .14, .13, material=2)], 'INDUSTRIAL_COURTYARD_WORKS'
        return [b(.04, 0, .06, .27, .45, .74, 'SAWTOOTH', 4),
                b(.365, 0, .06, .27, .57, .74, 'SAWTOOTH', 4),
                b(.69, 0, .06, .27, .38, .74, 'SAWTOOTH', 4),
                b(.28, 0, .82, .68, .27, .14, material=2),
                b(.08, 0, .80, .77, .12, .05)], 'SHED_ROOF_BAYS_AND_LOWER_OFFICE'
    if form in ('verification', 'pavilions', 'pods'):
        if variant % 2 == 0:
            return [b(.04, 0, .06, .92, .23, .18, material=2),
                    b(.05, 0, .24, .24, .58, .70, 'SAWTOOTH', 4),
                    b(.38, 0, .24, .24, .72, .60, 'SAWTOOTH', 4),
                    b(.71, 0, .24, .24, .44, .70, 'GABLE', 4)], 'CONNECTED_RESEARCH_HALLS'
        return [b(.05, 0, .07, .32, .61, .76, 'CHAMFER', 2),
                b(.66, 0, .16, .29, .45, .68, 'CHAMFER', 2),
                b(.37, .26, .31, .29, .09, .20, material=2),
                b(.37, 0, .07, .29, .24, .22),
                b(.40, 0, .76, .20, .25, .18, 'DRUM', 4)], 'LABORATORY_WINGS_AND_SHARED_FORUM'
    if form in ('tower', 'twin') and composition >= 4:
        podium = b(.03, 0, .05, .94, .15, .9)
        if width < 10:
            return [podium, b(.14, .15, .14, .72, .62, .72, 'CHAMFER', 2),
                    b(.24, .77, .24, .52, .16, .52, 'CHAMFER', 2)], 'COMPACT_TOWER_WITH_SETBACK_CROWN'
        if composition == 4:
            return [podium, b(.26, .15, .17, .45, .78, .57, 'CHAMFER', 2),
                    b(.29, .93, .21, .39, .035, .49),
                    b(.71, .15, .42, .23, .20, .40, material=2)], 'SLENDER_CROWN_AND_LOW_STREET_WING'
        if composition == 5:
            return [podium, b(.06, .15, .10, .47, .7, .76, 'CHAMFER', 2),
                    b(.53, .15, .26, .40, .38, .51, material=2),
                    b(.09, .85, .13, .40, .05, .69),
                    b(.58, .53, .31, .29, .035, .39, material=4)], 'ASYMMETRIC_MIXED_USE_TOWER'
        if composition == 6:
            return [podium, b(.07, .15, .11, .86, .27, .76, material=2),
                    b(.22, .42, .11, .71, .23, .61, material=2),
                    b(.39, .65, .11, .54, .27, .45, 'CHAMFER', 2),
                    b(.08, .42, .14, .12, .035, .69, material=4),
                    b(.24, .65, .14, .13, .035, .52, material=4)], 'OFFSET_CASCADING_TOWER_TERRACES'
        if width >= 20 and depth >= 14:
            return [podium, b(.06, .15, .12, .23, .63, .60, 'CHAMFER', 2),
                    b(.37, .15, .31, .27, .8, .56, 'CHAMFER', 2),
                    b(.72, .15, .12, .23, .44, .65, 'CHAMFER', 2),
                    b(.29, .43, .48, .08, .07, .18, material=2),
                    b(.64, .33, .48, .08, .07, .18, material=2)], 'THREE_TOWERS_AND_CONNECTING_PODIUM'
        return [podium, b(.11, .15, .14, .78, .39, .71, 'CHAMFER', 2),
                b(.23, .54, .21, .54, .25, .57, 'CHAMFER', 2),
                b(.33, .79, .27, .34, .16, .43, 'CHAMFER', 2)], 'TAPERED_SETBACK_GLASS_TOWER'
    if form in ('bar', 'row') and composition >= 4:
        if composition == 4 and width >= 18:
            return [b(.04, 0, .06, .92, .35, .24, material=2),
                    b(.04, 0, .30, .24, .46, .62, material=2),
                    b(.71, 0, .30, .25, .3, .62, material=2),
                    b(.28, .21, .57, .43, .07, .15, material=2),
                    b(.29, 0, .79, .40, .16, .14)], 'HORIZONTAL_HEADQUARTERS_AND_GARDEN_COURT'
        if composition in (4, 5):
            return [b(.04, 0, .06, .29, .72, .88, material=2),
                    b(.33, 0, .06, .63, .40, .30),
                    b(.33, .40, .06, .63, .035, .30),
                    b(.74, 0, .54, .22, .25, .38, material=2)], 'L_SHAPED_STREET_BLOCK_AND_CORNER_ANCHOR'
        if composition == 6:
            return [b(.05, 0, .08, .39, .61, .36, 'CHAMFER', 2),
                    b(.57, 0, .08, .38, .42, .36, 'CHAMFER', 2),
                    b(.19, 0, .65, .64, .31, .28, material=2),
                    b(.44, .21, .18, .13, .10, .15, material=2),
                    b(.29, 0, .44, .13, .17, .21)], 'CONNECTED_OFFICE_PAVILIONS'
        return [b(.04, 0, .06, .92, .22, .88),
                b(.07, .22, .10, .22, .49, .78, material=2),
                b(.72, .22, .10, .21, .37, .78, material=2),
                b(.29, .22, .10, .43, .34, .22),
                b(.29, .51, .32, .43, .04, .43, material=2)], 'PERIMETER_ATRIUM_WITH_GLAZED_CONCOURSE'
    if form in ('court', 'atrium') and variant >= 2:
        if variant == 2:
            return [b(.04, 0, .06, .92, .49, .20),
                    b(.04, 0, .26, .23, .65, .68, material=2),
                    b(.73, 0, .26, .23, .65, .68, material=2),
                    b(.27, 0, .75, .46, .36, .19),
                    b(.27, .49, .28, .46, .035, .45, material=2)], 'COVERED_ATRIUM_PERIMETER_BLOCK'
        return [b(.05, 0, .07, .35, .72, .75, 'CHAMFER', 2),
                b(.63, 0, .19, .32, .47, .74),
                b(.40, 0, .07, .55, .24, .12, material=2),
                b(.40, .31, .54, .23, .07, .18, material=2),
                b(.08, 0, .84, .50, .17, .10)], 'SPLIT_COURTYARD_AND_ELEVATED_GALLERY'
    if form == "bar" and variant == 2 and width >= 12 and depth >= 10:
        return [b(.03, 0, .05, .94, .18, .9),
                b(.07, .18, .12, .37, .66, .72, "CHAMFER", 2),
                b(.57, .18, .2, .36, .5, .68, "CHAMFER", 2),
                b(.44, .36, .32, .13, .09, .3, material=2)], "LINKED_TOWERS_ON_PODIUM"
    if form in ("tower", "twin"):
        podium = b(.03, 0, .05, .94, .18, .9)
        if variant == 2 and width >= 12 and depth >= 10:
            return [podium,
                    b(.07, .18, .12, .37, .66, .72, "CHAMFER", 2),
                    b(.57, .18, .2, .36, .5, .68, "CHAMFER", 2),
                    b(.44, .36, .32, .13, .09, .3, material=2),
                    b(.09, .84, .14, .33, .04, .68)], "LINKED_TOWERS_ON_PODIUM"
        if variant == 1:
            return [podium,
                    b(.09, .18, .11, .82, .34, .76, material=2),
                    b(.19, .52, .15, .65, .24, .63, "CHAMFER", 2),
                    b(.31, .76, .21, .46, .16, .49, "CHAMFER", 2),
                    b(.1, .52, .78, .7, .025, .1, material=4)], "BROAD_SETBACK_TOWER"
        if variant == 3:
            return [podium,
                    b(.08, .18, .11, .62, .66, .72, material=2),
                    b(.7, .18, .36, .24, .37, .47, material=2),
                    b(.08, .84, .11, .62, .035, .72),
                    b(.71, .55, .4, .2, .025, .38, material=4)], "OFFSET_SLAB_AND_WING"
        return [podium,
                b(.09, .18, .13, .82, .62, .7, "CHAMFER", 2),
                b(.1, .8, .14, .8, .045, .68),
                b(.23, .845, .26, .54, .075, .44)], "CURTAIN_WALL_SLAB_ON_PODIUM"
    if form in ("bar", "row"):
        if variant % 2:
            return [b(.03, 0, .07, .94, .16, .86),
                    b(.07, .16, .12, .6, .59, .68, material=2),
                    b(.67, .16, .38, .27, .36, .42),
                    b(.08, .75, .14, .57, .035, .63),
                    b(.69, .52, .4, .22, .025, .36, material=4)], "OFFSET_MIDRISE_WINGS"
        return [b(.03, 0, .06, .94, .17, .88),
                b(.07, .17, .1, .86, .49, .6, material=2),
                b(.07, .66, .1, .86, .04, .6),
                b(.12, .17, .72, .38, .24, .21),
                b(.13, .41, .73, .36, .025, .18, material=4)], "STREETWALL_AND_ROOF_TERRACE"
    if form == "terrace":
        return [b(.03, 0, .06, .94, .18, .88),
                b(.07, .18, .1, .86, .24, .78, material=2),
                b(.07, .42, .1, .66, .24, .63, material=2),
                b(.07, .66, .1, .45, .2, .48, material=2),
                b(.08, .42, .75, .63, .025, .1, material=4),
                b(.54, .66, .12, .16, .025, .53, material=4)], "INHABITED_SETBACK_TERRACES"
    if form in ("court", "atrium"):
        return [b(.04, 0, .06, .28, .6, .88),
                b(.69, 0, .06, .27, .72, .88, material=2),
                b(.32, 0, .06, .37, .42, .26, material=2),
                b(.32, .36, .32, .37, .04, .18, material=2),
                b(.32, 0, .87, .37, .12, .08),
                b(.06, .6, .09, .24, .025, .8, material=4)], "OPEN_ATRIUM_AND_CONNECTED_WINGS"
    return grammar(form), "RETAINED_PURPOSE_FORM"
