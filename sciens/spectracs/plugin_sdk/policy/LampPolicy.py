from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType


class LampPolicy:
    # Plugin-declared lamp switching (SPEC_lamp_switch.md §4.3, D1-D5). Qt-free plain data; the host's
    # LampService does the switching. On entering a phase the host switches the lamp ON if the phase is in
    # `onDuringPhases`, else OFF — enter hooks only, no leave hook (D5).
    #
    # Cap (D3): the plug switches itself off `maxMeasurementSeconds + marginSeconds` after the on. The margin is
    # the whole budget for warm-up + reference + jar swap; it is hard by design.
    #
    # Default = not switched: every plugin that does not opt in leaves the lamp alone (today's behaviour).

    DEFAULT_WARM_UP_SECONDS = 20
    DEFAULT_MARGIN_SECONDS = 300

    def __init__(self, switched=False, onDuringPhases=(SpectralWorkflowPhaseType.ACQUISITION,),
                 warmUpSeconds=DEFAULT_WARM_UP_SECONDS, maxMeasurementSeconds=1500,
                 marginSeconds=DEFAULT_MARGIN_SECONDS):
        self.switched = bool(switched)
        self.onDuringPhases = frozenset(onDuringPhases)
        self.warmUpSeconds = int(warmUpSeconds)
        self.maxMeasurementSeconds = int(maxMeasurementSeconds)
        self.marginSeconds = int(marginSeconds)

    @staticmethod
    def default():
        return LampPolicy()

    @staticmethod
    def duringAcquisition(maxMeasurementSeconds, warmUpSeconds=DEFAULT_WARM_UP_SECONDS,
                          marginSeconds=DEFAULT_MARGIN_SECONDS):
        """The usual opt-in: lamp on in ACQUISITION only, cap = the plugin's longest capture + margin."""
        return LampPolicy(switched=True, warmUpSeconds=warmUpSeconds,
                          maxMeasurementSeconds=maxMeasurementSeconds, marginSeconds=marginSeconds)

    def isSwitched(self):
        return self.switched

    def isOnDuring(self, phaseType):
        return phaseType in self.onDuringPhases

    def getWarmUpSeconds(self):
        return self.warmUpSeconds

    def getMaxMeasurementSeconds(self):
        return self.maxMeasurementSeconds

    def getCapSeconds(self):
        return self.maxMeasurementSeconds + self.marginSeconds
