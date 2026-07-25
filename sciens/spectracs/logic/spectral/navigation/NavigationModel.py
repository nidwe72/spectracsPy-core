from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.logic.spectral.navigation.NavStop import NavStop, NavStopKind


class NavigationModel:
    # Derives the flat list of navigation stops (chevrons) from a workflow + a NavigationPolicy — the single,
    # generic navigation model both hosts render from (SPEC_simplified_plugin_navigation.md §4). Pure and
    # Qt-free: no host, no engine. A phase becomes one PHASE stop, or (when the policy expands it) one STEP stop
    # per step; empty phases produce no stop. The mode (STEP vs AUTO_ADVANCE) does NOT change the list — only the
    # host's cursor behaviour (the auto-advance jump) does — so `stops()` is mode-independent by construction.
    #
    # METADATA needs no special case here: upstream the engine materialises its declared fields into a real step
    # (Change E), so by the time `stops()` runs every phase is described uniformly by its step count.

    # Canonical phase spine order — mirrors SpectralWorkflowEngine.PHASE_ORDER, kept here so this module stays
    # Qt-free (the engine imports Qt). The order is a stable domain fact, not host chrome.
    PHASE_ORDER = [
        SpectralWorkflowPhaseType.ACQUISITION,
        SpectralWorkflowPhaseType.PROCESSING,
        SpectralWorkflowPhaseType.EVALUATION,
        SpectralWorkflowPhaseType.METADATA,
        SpectralWorkflowPhaseType.PUBLISHING,
    ]

    # Default human labels for PHASE stops. The host may override, but centralising them keeps the two hosts in
    # step and gives the chevron a label without the phase entity carrying display text.
    PHASE_LABELS = {
        SpectralWorkflowPhaseType.ACQUISITION: "Acquisition",
        SpectralWorkflowPhaseType.PROCESSING: "Processing",
        SpectralWorkflowPhaseType.EVALUATION: "Evaluation",
        SpectralWorkflowPhaseType.METADATA: "Details",          # Edwin 2026-07-25: was "Metadata"
        SpectralWorkflowPhaseType.PUBLISHING: "Verdict/Publish",  # Edwin 2026-07-25: was "Publishing"
    }

    @staticmethod
    def stops(workflow, policy=None, hasMetadataFields=False):
        # policy: a NavigationPolicy (or None -> default STEP, no step-expansion). Returns the ordered list of
        # NavStop, one per chevron.
        #
        # METADATA carve-out: the metadata phase has no ENGINE steps (its content is the plugin's field list,
        # rendered as a transient form — not a persisted step, so saved runs are unchanged). The host passes
        # hasMetadataFields (from the plugin's metadata() in a new run, or the persisted rows when viewing one)
        # so the METADATA chevron appears exactly when there is a form to fill.
        stops = []
        for phaseType in NavigationModel.PHASE_ORDER:
            phase = workflow.getPhase(phaseType)
            if phase is None:
                continue
            steps = list(phase.getSteps().values())
            if not steps:
                if phaseType == SpectralWorkflowPhaseType.METADATA and hasMetadataFields:
                    stops.append(NavStop(NavStopKind.PHASE, phaseType, NavigationModel.__phaseLabel(phaseType)))
                continue  # otherwise an empty phase -> no stop
            if policy is not None and policy.expandsSteps(phaseType):
                for step in steps:
                    stops.append(NavStop(NavStopKind.STEP, phaseType,
                                         NavigationModel.__stepLabel(step, phaseType), step=step))
            else:
                stops.append(NavStop(NavStopKind.PHASE, phaseType, NavigationModel.__phaseLabel(phaseType)))
        return stops

    @staticmethod
    def __stepLabel(step, phaseType):
        label = step.getLabel() if hasattr(step, "getLabel") else None
        return label if label else NavigationModel.__phaseLabel(phaseType)

    @staticmethod
    def __phaseLabel(phaseType):
        return NavigationModel.PHASE_LABELS.get(phaseType, str(phaseType))
