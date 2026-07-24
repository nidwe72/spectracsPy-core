from enum import Enum


class NavStopKind(str, Enum):
    PHASE = 'PHASE'   # a whole phase — the host renders its step-tabs (or, single-step, its content directly)
    STEP = 'STEP'     # one step of a phase surfaced as its own chevron (e.g. Reference / Sample)


class NavStop:
    # One navigation stop = one chevron entry (SPEC_simplified_plugin_navigation.md §4.1). A pure projection
    # over the workflow -> phase -> step graph; it carries no navigation state of its own (the cursor is the
    # host's). Qt-free.

    def __init__(self, kind, phaseType, label, step=None):
        self.kind = kind
        self.phaseType = phaseType
        self.label = label
        self.step = step            # the SpectralWorkflowStep for STEP kind; None for PHASE kind

    def isStep(self):
        return self.kind == NavStopKind.STEP

    def isPhase(self):
        return self.kind == NavStopKind.PHASE
