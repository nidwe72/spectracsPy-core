from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl
from sciens.spectracs.plugin_sdk.camera.CameraSettings import CameraSettings
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile

# The write order (§5, D6): an auto loop goes MANUAL before its value is written — on V4L2 the exposure and the
# white-balance temperature are INACTIVE (unwritable) while their auto mode is on. Then the rest, enum order.
WRITE_ORDER = [CameraControl.AUTO_EXPOSURE, CameraControl.EXPOSURE,
               CameraControl.WHITE_BALANCE_AUTO, CameraControl.WHITE_BALANCE_KELVIN] + \
              [control for control in CameraControl
               if control not in (CameraControl.AUTO_EXPOSURE, CameraControl.EXPOSURE,
                                  CameraControl.WHITE_BALANCE_AUTO, CameraControl.WHITE_BALANCE_KELVIN)]

# Sources a requested value can come from. The live ones (auto-exposure, operator, locked-from-reference) are
# written by the video thread when exposure changes mid-stream (§3.3a); resolve() only ever says these three.
DEVICE, PROFILE, PLUGIN = "device", "profile", "plugin"


class CameraResolution:
    """What one open ASKS the camera for, and why — the output of `CameraSettingsResolver.resolve` (§3.3).

    requested   CameraSettings of every ACTIVE control the camera offers (the values written, in WRITE_ORDER)
    sources     {CameraControl: "device" | "profile" | "plugin"}
    adjusted    {CameraControl: "requested 7000 → 6500 (clamped)"} — said, never silent
    skipped     controls a layer named that the camera does not offer
    inactive    controls the resolved state makes unwritable (WB temperature under auto WB, exposure under AE)
    rejected    plugin entries that are not a control, or not a usable value, with the reason
    autoLoopsOn controls that leave an auto loop running in a MEASUREMENT (Q8: accepted, badged ⛔)
    """

    def __init__(self, profile, requested, sources, adjusted, skipped, inactive, rejected, autoLoopsOn):
        self.profile = profile
        self.requested = requested
        self.sources = sources
        self.adjusted = adjusted
        self.skipped = skipped
        self.inactive = inactive
        self.rejected = rejected
        self.autoLoopsOn = autoLoopsOn

    def writes(self):
        """[(control, value)] in the order a backend must write them."""
        return [(control, self.requested.get(control)) for control in WRITE_ORDER if self.requested.has(control)]

    def exposure(self):
        return self.requested.get(CameraControl.EXPOSURE)

    def exposureSource(self):
        return self.sources.get(CameraControl.EXPOSURE)

    def mismatches(self, applied):
        """[(control, requested, applied)] for every requested control the read-back does not confirm.

        ⛔ A control that does not read back at all counts: a camera that will not say is not proof (§6.4b)."""
        applied = CameraSettings.of(applied)
        found = []
        for control, value in self.writes():
            readBack = applied.get(control)
            if readBack is None or not _same(value, readBack):
                found.append((control, value, readBack))
        return found

    def toJson(self):
        return {"profile": self.profile.value,
                "requested": self.requested.toJson(),
                "sources": {control.value: source for control, source in self.sources.items()},
                "adjusted": {control.value: note for control, note in self.adjusted.items()},
                "skipped": [control.value for control in self.skipped],
                "inactive": [control.value for control in self.inactive],
                "rejected": list(self.rejected),
                "autoLoopsOn": [control.value for control in self.autoLoopsOn]}


def _same(requested, applied):
    if isinstance(requested, bool) or isinstance(applied, bool):
        return bool(requested) == bool(applied)
    try:
        return int(round(float(requested))) == int(round(float(applied)))
    except (TypeError, ValueError):
        return str(requested) == str(applied)


class CameraSettingsResolver:
    """`device default ← spectral profile ← plugin override`, clamped and snapped — pure, Qt-free (§3.3).

    ⭐ EXPOSURE IS A LIVE CONTROL (§3.3a): what resolve() gives it is only the SEED of the open —
    plugin pin › host seed (`exposureSeed`, e.g. `calibrationExposure`) › profile fallback › device default.
    Every later change (AE sweep, slider, the lock onto the sample) carries its own source in the video thread.
    """

    @staticmethod
    def resolve(device, profile, pluginOverride=None, exposureSeed=None):
        profile = CameraProfile.of(profile)
        layers = {}                                    # control -> (value, source)
        for control, value in device.defaults().items():
            layers[control] = (value, DEVICE)
        for control, value in profile.values().items():
            layers[control] = (value, PROFILE)
        seed = exposureSeed if exposureSeed is not None else profile.exposureFallback()
        if seed is not None:
            layers[CameraControl.EXPOSURE] = (seed, PROFILE)

        rejected = []
        if pluginOverride is not None and profile.acceptsPluginOverride():
            for name, value in (pluginOverride.items() if hasattr(pluginOverride, "items") else []):
                try:
                    control = CameraControl.of(name)
                except ValueError:
                    rejected.append("%s: not a camera control" % (name,))
                    continue
                if value is None:
                    rejected.append("%s: no value" % control.value)
                    continue
                layers[control] = (value, PLUGIN)

        requested, sources, adjusted, skipped, inactive = {}, {}, {}, [], []
        for control, (value, source) in layers.items():
            entry = device.rangeOf(control)
            if entry is None:
                skipped.append(control)
                continue
            try:
                snapped, how = entry.snap(_coerce(control, value))
            except (TypeError, ValueError):
                rejected.append("%s: %r is not a usable value" % (control.value, value))
                snapped, how, source = entry.default, None, DEVICE
            if how is not None:
                adjusted[control] = "requested %s → %s (%s)" % (value, snapped, how)
            requested[control] = snapped
            sources[control] = source

        if requested.get(CameraControl.WHITE_BALANCE_AUTO) is True and CameraControl.WHITE_BALANCE_KELVIN in requested:
            inactive.append(CameraControl.WHITE_BALANCE_KELVIN)
        if requested.get(CameraControl.AUTO_EXPOSURE) == "AUTO" and CameraControl.EXPOSURE in requested:
            inactive.append(CameraControl.EXPOSURE)
        for control in inactive:
            requested.pop(control)
            sources.pop(control, None)

        autoLoopsOn = []
        if profile is CameraProfile.MEASUREMENT:
            if requested.get(CameraControl.AUTO_EXPOSURE) == "AUTO":
                autoLoopsOn.append(CameraControl.AUTO_EXPOSURE)
            if requested.get(CameraControl.WHITE_BALANCE_AUTO) is True:
                autoLoopsOn.append(CameraControl.WHITE_BALANCE_AUTO)
            if requested.get(CameraControl.BACKLIGHT) not in (None, 0):
                autoLoopsOn.append(CameraControl.BACKLIGHT)

        order = {control: index for index, control in enumerate(WRITE_ORDER)}
        return CameraResolution(
            profile, CameraSettings(dict(sorted(requested.items(), key=lambda item: order[item[0]]))),
            sources, adjusted, sorted(skipped, key=order.get), inactive, rejected, autoLoopsOn)


def _coerce(control, value):
    if control in (CameraControl.WHITE_BALANCE_AUTO, CameraControl.DYNAMIC_FRAMERATE):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "on", "yes")
        return bool(value)
    if control is CameraControl.AUTO_EXPOSURE:
        return str(value).upper()
    if control is CameraControl.POWER_LINE_FREQUENCY:
        text = str(value).upper()
        return {"50HZ": "50", "60HZ": "60", "0": "DISABLED", "OFF": "DISABLED"}.get(text, text)
    if isinstance(value, bool):
        raise ValueError(value)
    return int(round(float(value)))


def pluginOverrideOf(plugin, deviceDefaults):
    """(override as a plain {name: value} dict or None, problem text or None) — SPEC_camera_settings.md §6.1.

    `cameraSettings(deviceDefaults)` wins; a plugin that only has the `exposure` attribute (every signed v1.x row)
    gets `{EXPOSURE: exposure}`. ⛔ A plugin that raises or answers something that is not camera settings must not
    break capture: the MEASUREMENT profile alone, and the problem is said."""
    if plugin is None:
        return None, None
    problem = None
    override = None
    if hasattr(plugin, "cameraSettings"):
        try:
            override = plugin.cameraSettings(deviceDefaults)
        except Exception as error:
            problem = "the plugin's cameraSettings() raised (%s: %s)" % (type(error).__name__, error)
    if override is None and getattr(plugin, "exposure", None) is not None:
        override = {"EXPOSURE": plugin.exposure}
    if override is None:
        return None, problem
    try:
        return CameraSettings.of(override).toJson(), problem
    except (TypeError, ValueError, AttributeError) as error:
        return None, "the plugin's override %r is not camera settings (%s)" % (override, error)
