"""A small composable massing system, not more synonyms for thin boxes."""

from .seed import derive

VERSION = "urban-architecture/0.1"


def modern_grammar(form, envelope, seed):
    from .architecture_catalog import part as b, grammar

    variant = int(derive(seed, VERSION, "composition"), 16) % 4
    width, depth = envelope["width"], envelope["depth"]
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
