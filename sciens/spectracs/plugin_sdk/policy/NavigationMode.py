from enum import Enum


class NavigationMode(str, Enum):
    # How the host advances the cursor through the workflow's navigation stops
    # (SPEC_simplified_plugin_navigation.md §3.2 / §4.2). A plugin declares it via NavigationPolicy.
    STEP = 'STEP'                  # one phase per Next — today's behaviour
    AUTO_ADVANCE = 'AUTO_ADVANCE'  # completing ACQUISITION jumps the cursor forward, halting at the
    #                                metadata / final stop (the intermediate phases stay Back-reachable)
