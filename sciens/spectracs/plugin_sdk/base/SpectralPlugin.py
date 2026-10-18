from sciens.spectracs.plugin_sdk.version import SDK_VERSION
from sciens.spectracs.plugin_sdk.acquisition.Solvent import Solvent
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

    # ⭐⭐ WHAT WAS IN THE JAR, AND HOW IT GOT THERE (2026-08-26). Both are pure PROVENANCE — they are
    # stamped into the report header and change no behaviour here. `solvent` additionally selects which
    # read rule the plugin REPORTS; see Solvent.
    # ⛔ `prepProtocol` exists for the same reason `evaluatorVersion` does. The read rule is versioned so
    # the archive can say which algorithm produced a number; the LAB RECIPE deserves the same, because on
    # 2026-08-26 the recipe changed, the numbers moved, and nothing recorded which runs were made which
    # way — so the question could not be answered retrospectively at all.
    # ⚠ Free-form on purpose: a recipe is not an enum, and forcing one would just stop it being written.
    solvent = Solvent.UNKNOWN
    prepProtocol = None

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

    def createMonitor(self, reference=None, mode=None, frames=None):
        # Monitored acquisition (SPEC_settled_measurement.md §10.1a-bis). The plugin ASSEMBLES the object
        # — engine + ring + ITS OWN evaluator — and hands it over; the host only pushes frames into it via
        # `offer(frameSpectrum, timestamp)` and never calls back into the plugin during a run.
        #
        # ⭐ ADDITIVE BY DESIGN, and returning None is the whole point (§10.6): a plugin that needs no
        # intermediate evaluation writes nothing, and the host gives it a plain BurstEvaluator monitor —
        # byte-for-byte today's N-frame burst. ⛔ Which is also why SDK_VERSION does NOT bump for this
        # (§19/I2): every sealed, DB-served plugin keeps loading unchanged.
        #
        # `mode` is a HOST argument (MonitorMode.PRODUCT / DIAGNOSTIC), never a plugin constant (§17/D3).
        return None

    def cameraSettings(self, deviceDefaults):
        # The plugin's CAMERA OVERRIDE (SPEC_camera_settings.md §6) — the top layer of
        # `device default ← spectral profile ← plugin override`, applied to a MEASUREMENT open only (§6.2).
        # `deviceDefaults` is the camera's firmware state (a CameraSettings), handed in by the host so a plugin can
        # say "device contrast + 4" without touching hardware.
        # Return a PARTIAL override: a CameraSettings or a plain {name: value} dict, e.g.
        #     {"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500}
        # ⭐ The plain dict is the safe form for a DB-served row: importing `plugin_sdk.camera` would fail on an app
        # that predates it, and SDK_VERSION cannot see that (D10b). Exposure is in V4L2 units on every OS.
        # ⚠ Image controls (gamma, contrast, …) are in CAMERA units — an override of one is camera-specific, and
        # the record says which camera it ran on. Switching an auto loop on is accepted and badged ⛔ (Q8).
        # None = the profile alone. A plugin that still declares only `exposure` gets {EXPOSURE: exposure}.
        return None

    def showsCameraTab(self):
        # Q9: whether the capture panel shows the "Camera" inner tab (the settings each leg ran under). Off by
        # default — an end user gets the table in the PDF; the dev bench plugin turns it on.
        return False

    def policy(self):
        # Cross-cutting FLOW/presentation policy (SPEC_simplified_plugin_navigation.md §4.2) — the ONE hook for
        # navigation mode, step-chevrons, etc. Default = today's behaviour (STEP navigation, no step-chevrons),
        # so a plugin that does not override it is unchanged. A plugin overrides to opt into auto-advance or
        # per-step chevrons. Content stays in the phase hooks; how the run flows lives here.
        return WorkflowPolicy.default()
