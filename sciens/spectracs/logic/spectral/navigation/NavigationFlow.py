from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode


class NavigationFlow:
    # Pure navigation DECISIONS over a stops list + cursor + mode (SPEC_simplified_plugin_navigation.md §4.4).
    # No Qt, no side effects: the host runs the phase hooks, captures, and saves — this class only decides
    # WHERE the cursor should land. Proven in isolation so the Qt hosts (M2 B2/B3) inherit correct flow.
    #
    # The cursor walks the CURRENT stops list. Two things grow that list, and the host owns them:
    #   - after ACQUISITION completes, the host runs the remaining phase hooks (which populate PROCESSING /
    #     EVALUATION / METADATA / PUBLISHING) and recomputes NavigationModel.stops();
    #   - so the AUTO_ADVANCE jump target must be read from the ALREADY-regrown (full) stops list.

    @staticmethod
    def isTerminal(stops, cursor):
        # The last stop -> Next is a FINISH action (save/close), not a move.
        return (not stops) or cursor >= len(stops) - 1

    @staticmethod
    def lastAcquisitionIndex(stops):
        # Index of the last ACQUISITION stop (the boundary whose Next triggers the auto-advance jump), or None.
        last = None
        for index, stop in enumerate(stops):
            if stop.phaseType == SpectralWorkflowPhaseType.ACQUISITION:
                last = index
        return last

    @staticmethod
    def haltIndex(stops):
        # Where an AUTO_ADVANCE jump lands: the FIRST METADATA stop (a required form halts the jump), else the
        # final stop. Read from the full (post-hooks) stops list.
        for index, stop in enumerate(stops):
            if stop.phaseType == SpectralWorkflowPhaseType.METADATA:
                return index
        return (len(stops) - 1) if stops else 0

    @staticmethod
    def isAtAcquisitionBoundary(stops, cursor):
        # True when the cursor sits on the last ACQUISITION stop — the one whose forward Next may jump.
        last = NavigationFlow.lastAcquisitionIndex(stops)
        return last is not None and cursor == last

    @staticmethod
    def forwardTarget(stops, cursor, mode):
        # The cursor index a forward Next should land on given the CURRENT (already-regrown) stops list, or None
        # to FINISH. AUTO_ADVANCE jumps from the acquisition boundary to the halt stop; otherwise a plain step.
        if NavigationFlow.isTerminal(stops, cursor):
            return None
        if mode == NavigationMode.AUTO_ADVANCE and NavigationFlow.isAtAcquisitionBoundary(stops, cursor):
            halt = NavigationFlow.haltIndex(stops)
            return halt if halt > cursor else cursor + 1
        return cursor + 1
