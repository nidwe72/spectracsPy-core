from enum import Enum


class CameraControl(Enum):
    """The OS-neutral name of one camera control — SPEC_camera_settings.md §3.1.

    ⭐ ONE VOCABULARY FOR EVERY LAYER: the device defaults, the spectral profiles, a plugin's override and the
    record in the report all speak these names. The mapping to V4L2 ids (Linux) and DirectShow ids (Windows)
    lives in the backends, never in a plugin.

    Value kinds (what `CameraSettings` holds for each):
      EXPOSURE                 int, V4L2 units (100 µs) on every OS — the plugin contract; Windows converts
      AUTO_EXPOSURE            "MANUAL" | "AUTO"
      WHITE_BALANCE_AUTO       bool
      WHITE_BALANCE_KELVIN     int, K
      POWER_LINE_FREQUENCY     "DISABLED" | "50" | "60" | "AUTO"
      DYNAMIC_FRAMERATE        bool
      every other control      int, CAMERA units — Gamma 100 on the ELP is not Gamma 100 on another camera

    ⛔ THE MEMBER STRINGS ARE PERSISTED in every camera record of every report. Add, never rename.
    """

    EXPOSURE = "EXPOSURE"
    AUTO_EXPOSURE = "AUTO_EXPOSURE"
    WHITE_BALANCE_AUTO = "WHITE_BALANCE_AUTO"
    WHITE_BALANCE_KELVIN = "WHITE_BALANCE_KELVIN"
    GAIN = "GAIN"
    BACKLIGHT = "BACKLIGHT"
    BRIGHTNESS = "BRIGHTNESS"
    CONTRAST = "CONTRAST"
    HUE = "HUE"
    SATURATION = "SATURATION"
    SHARPNESS = "SHARPNESS"
    GAMMA = "GAMMA"
    POWER_LINE_FREQUENCY = "POWER_LINE_FREQUENCY"
    DYNAMIC_FRAMERATE = "DYNAMIC_FRAMERATE"

    @classmethod
    def of(cls, name):
        """A member from itself or its persisted string; ValueError for anything else."""
        if isinstance(name, cls):
            return name
        return cls(str(name))

    def label(self):
        return _LABELS[self]

    def isAutoLoop(self):
        """A control that switches a loop the camera regulates BY ITSELF, frame by frame (§6.1, Q8)."""
        return self in (CameraControl.AUTO_EXPOSURE, CameraControl.WHITE_BALANCE_AUTO, CameraControl.BACKLIGHT)


_LABELS = {
    CameraControl.EXPOSURE: "Exposure",
    CameraControl.AUTO_EXPOSURE: "Exposure mode",
    CameraControl.WHITE_BALANCE_AUTO: "White balance auto",
    CameraControl.WHITE_BALANCE_KELVIN: "White balance",
    CameraControl.GAIN: "Gain",
    CameraControl.BACKLIGHT: "Backlight compensation",
    CameraControl.BRIGHTNESS: "Brightness",
    CameraControl.CONTRAST: "Contrast",
    CameraControl.HUE: "Hue",
    CameraControl.SATURATION: "Saturation",
    CameraControl.SHARPNESS: "Sharpness",
    CameraControl.GAMMA: "Gamma",
    CameraControl.POWER_LINE_FREQUENCY: "Power line frequency",
    CameraControl.DYNAMIC_FRAMERATE: "Dynamic framerate",
}
