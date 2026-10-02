from sciens.spectracs.plugin_sdk.policy.LampPolicy import LampPolicy
from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy


class WorkflowPolicy:
    # The cross-cutting policy CONTAINER a plugin declares (SPEC_simplified_plugin_navigation.md §4.2). It
    # composes NavigationPolicy and LampPolicy (SPEC_lamp_switch.md §4.3); future cross-cutting concerns
    # (report / guidance / publish / save) join as further composed fields, so the plugin surface stays a single `policy()` hook rather than a growing
    # set of hooks. Content stays in the phase methods; cross-cutting flow/presentation lives here.

    def __init__(self, navigation=None, lamp=None):
        self.navigation = navigation if navigation is not None else NavigationPolicy.default()
        self.lamp = lamp if lamp is not None else LampPolicy.default()

    @staticmethod
    def default():
        return WorkflowPolicy()

    def getNavigation(self):
        return self.navigation

    def getLamp(self):
        return self.lamp
