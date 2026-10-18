from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl
from sciens.spectracs.plugin_sdk.camera.CameraSettings import CameraSettings


class CameraControlRange:
    """One control as THE CAMERA describes it: range, step, firmware default and — for a menu or a switch — the
    values it offers, all in MODEL units (SPEC_camera_settings.md §3.4).

    `quantise` is the backend's own rounding when the camera's grid is not linear (Windows exposure: whole log₂
    seconds, §3.3a); `resolve()` cannot derive that from a `step`. It takes and returns a model value."""

    def __init__(self, default, minimum=None, maximum=None, step=None, choices=None, quantise=None):
        self.default = default
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.choices = list(choices) if choices is not None else None
        self.quantise = quantise

    def isNumeric(self):
        return self.choices is None

    def snap(self, value):
        """(snapped, how) — `how` is None, "clamped" or "snapped"; a menu/switch value is checked, not snapped."""
        if not self.isNumeric():
            return (value, None) if value in self.choices else (self.default, "not offered")
        number = int(round(float(value)))
        if self.quantise is not None:
            snapped = self.quantise(number)
            return snapped, (None if snapped == number else "snapped")
        clamped = number
        if self.minimum is not None:
            clamped = max(self.minimum, clamped)
        if self.maximum is not None:
            clamped = min(self.maximum, clamped)
        snapped = clamped
        if self.step and self.step > 1 and self.minimum is not None:
            snapped = self.minimum + int(round((clamped - self.minimum) / float(self.step))) * self.step
            if self.maximum is not None and snapped > self.maximum:
                snapped -= self.step
        if snapped == number:
            return snapped, None
        return snapped, ("clamped" if clamped != number else "snapped")

    def toJson(self):
        return {"default": self.default, "min": self.minimum, "max": self.maximum, "step": self.step,
                "choices": self.choices}


class CameraDevice:
    """What one camera offers, read from its firmware — no stream needed (`readDeviceDefaults`, §3.4).

    ⭐ Nothing here is stored in code or in the DB: every number comes from the camera's own `GET_DEF` /
    `QUERYCTRL` answer. An EMPTY device (a camera that would not answer, or a backend that cannot ask yet) is a
    valid value — `resolve()` then lists every control as skipped and the record says so."""

    def __init__(self, ranges=None, name=None):
        self.ranges = {CameraControl.of(control): entry for control, entry in (ranges or {}).items()}
        self.name = name

    def offers(self, control):
        return CameraControl.of(control) in self.ranges

    def rangeOf(self, control):
        return self.ranges.get(CameraControl.of(control))

    def defaults(self):
        """The DEVICE DEFAULTS as a CameraSettings — what a plugin's `cameraSettings(deviceDefaults)` is handed."""
        return CameraSettings({control: entry.default for control, entry in self.ranges.items()})

    def toJson(self):
        return {control.value: entry.toJson() for control, entry in self.ranges.items()}
