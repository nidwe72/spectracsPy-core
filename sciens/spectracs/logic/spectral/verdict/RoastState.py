from enum import Enum


class RoastState(str, Enum):
    # Perfect-centred quality axis (concept §5). Quality peaks at the perfect hue; deviation either way
    # is worse — too green = under-roasted, too brown = over-roasted.
    PERFECT_ROASTED = "PERFECT-ROASTED"
    UNDER_ROASTED = "UNDER-ROASTED"
    OVER_ROASTED = "OVER-ROASTED"
