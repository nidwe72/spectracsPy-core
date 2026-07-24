from sciens.spectracs.plugin_sdk.version import SDK_VERSION
from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy


class SpectralPlugin:
    # One class, five per-phase hooks (concept §9.4). Qt-free; imports only plugin_sdk. Each hook mutates
    # the passed SpectralWorkflow: interactive phases DECLARE steps, computed phases CREATE+FILL them; a
    # hook that creates zero steps makes the host auto-skip that phase. (SPEC_pumpkin_integration.md B.4)

    title = None

    # The plugin_sdk this plugin was built against; the host refuses to load a mismatch with a clear message
    # (SPEC_plugin_distribution.md §4 / §8 A2). Defaults to the shipping SDK, so an in-app plugin that does
    # not override it always matches by construction.
    targetSdkVersion = SDK_VERSION

    def acquisition(self, workflow):
        raise NotImplementedError

    def processing(self, workflow):
        raise NotImplementedError

    def evaluation(self, workflow):
        raise NotImplementedError

    def metadata(self, workflow):
        # Return a list[MetadataField] describing the editable metadata form (empty = no metadata).
        # This hook DESCRIBES fields (it does not mutate the workflow like the others).
        return []

    def publishing(self, workflow):
        pass  # empty -> phase skipped

    def policy(self):
        # Cross-cutting FLOW/presentation policy (SPEC_simplified_plugin_navigation.md §4.2) — the ONE hook for
        # navigation mode, step-chevrons, etc. Default = today's behaviour (STEP navigation, no step-chevrons),
        # so a plugin that does not override it is unchanged. A plugin overrides to opt into auto-advance or
        # per-step chevrons. Content stays in the phase hooks; how the run flows lives here.
        return WorkflowPolicy.default()
