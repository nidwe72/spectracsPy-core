from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode


class NavigationPolicy:
    # Plugin-declared FLOW policy (SPEC_simplified_plugin_navigation.md §4.2): the navigation mode plus which
    # phases surface their steps as individual chevron entries. Qt-free plain data — the host derives the
    # concrete NavigationModel (the chevron list) from it.
    #
    # Default = STEP navigation, no step-expansion = today's behaviour, so every existing plugin is unchanged.

    def __init__(self, mode=NavigationMode.STEP, stepChevronPhases=()):
        self.mode = mode
        # phases whose steps become one chevron each (e.g. {ACQUISITION} -> "Reference" / "Sample" chevrons)
        self.stepChevronPhases = frozenset(stepChevronPhases)

    @staticmethod
    def default():
        return NavigationPolicy()

    def getMode(self):
        return self.mode

    def expandsSteps(self, phaseType):
        return phaseType in self.stepChevronPhases
