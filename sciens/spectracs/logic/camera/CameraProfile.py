from enum import Enum

from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl


class CameraProfile(Enum):
    """The SPECTRAL PROFILE of a camera open — Spectracs' settings for one USE CASE (SPEC_camera_settings.md §2, §3.3).

    The middle of the three layers `device default ← spectral profile ← plugin override`. Owned by the host, never
    by a plugin: a profile edit is host policy, not an SDK change, which is why this lives outside `plugin_sdk`.

      CALIBRATION  the master authors a px→nm profile: auto white balance (the peak detection is tuned for it),
                   backlight at the device default; opened at the legacy exposure 150, then the AE sweep;
      MEASUREMENT  a plugin evaluates a sample: every auto loop frozen (WB 6500 K = the lamp, backlight off,
                   gain 0); the only profile a plugin override is applied on (§6.2);
      IDLE         the warm-keeper between sessions = MEASUREMENT minus the plugin (D1), so a measurement open
                   finds white balance, backlight, gain and the image controls already in place.

    A control a profile does not name stays at the DEVICE DEFAULT — which is still WRITTEN on every open: UVC
    values persist in the camera, and whatever another program left there must not reach a spectrum.
    ⛔ The member strings are persisted in every camera record. Add, never rename.
    """

    CALIBRATION = "CALIBRATION"
    MEASUREMENT = "MEASUREMENT"
    IDLE = "IDLE"

    @classmethod
    def of(cls, name):
        return name if isinstance(name, cls) else cls(str(name))

    def values(self):
        """{CameraControl: value} this profile sets (exposure excluded — it is a live control, §3.3a)."""
        return dict(_VALUES[self])

    def exposureFallback(self):
        """The exposure seed when neither the plugin nor the host gives one; None = the device default."""
        return _EXPOSURE_FALLBACK[self]

    def acceptsPluginOverride(self):
        return self is CameraProfile.MEASUREMENT

    def refusesOnMismatch(self):
        """Q4: a MEASUREMENT whose read-back differs from the request is refused; the others only warn."""
        return self is CameraProfile.MEASUREMENT


_FROZEN = {
    CameraControl.AUTO_EXPOSURE: "MANUAL",
    CameraControl.WHITE_BALANCE_AUTO: False,
    # The lamp's colour temperature — an instrument fact, so the profile carries it; a plugin may and
    # DevSpectralPlugin does declare it explicitly as well (Q7, Edwin: "both").
    CameraControl.WHITE_BALANCE_KELVIN: 6500,
    CameraControl.GAIN: 0,
    # ⭐ Backlight compensation is an in-camera brightness correction that reacts to the scene; the ELP ships it
    # ON (1), so left alone it would change the frame between reference and sample (Edwin's question, §3.3).
    CameraControl.BACKLIGHT: 0,
}

_VALUES = {
    CameraProfile.CALIBRATION: {
        CameraControl.AUTO_EXPOSURE: "MANUAL",
        CameraControl.WHITE_BALANCE_AUTO: True,
        CameraControl.GAIN: 0,
    },
    CameraProfile.MEASUREMENT: dict(_FROZEN),
    CameraProfile.IDLE: dict(_FROZEN),
}

# ⚠ 150 is the LEGACY open value the calibration views have always used before their own AE sweep (D2), and the
# ELP's `calibrationExposure`; the host normally passes its own seed, this only covers a caller that does not.
_EXPOSURE_FALLBACK = {
    CameraProfile.CALIBRATION: 150,
    CameraProfile.MEASUREMENT: None,
    CameraProfile.IDLE: 150,
}
