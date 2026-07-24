from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy


class WorkflowPolicy:
    # The cross-cutting policy CONTAINER a plugin declares (SPEC_simplified_plugin_navigation.md §4.2). It
    # composes NavigationPolicy today; future cross-cutting concerns (report / guidance / publish / save) join
    # as further composed fields, so the plugin surface stays a single `policy()` hook rather than a growing
    # set of hooks. Content stays in the phase methods; cross-cutting flow/presentation lives here.

    def __init__(self, navigation=None):
        self.navigation = navigation if navigation is not None else NavigationPolicy.default()

    @staticmethod
    def default():
        return WorkflowPolicy()

    def getNavigation(self):
        return self.navigation
