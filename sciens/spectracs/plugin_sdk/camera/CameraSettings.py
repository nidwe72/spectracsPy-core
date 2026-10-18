from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl


class CameraSettings:
    """`{CameraControl: value}`, partial or complete, immutable — SPEC_camera_settings.md §3.2.

    One type for three things: the camera's DEVICE DEFAULTS (what its firmware reports), a REQUESTED state (the
    resolved target) and an APPLIED one (a read-back). A plugin's override may be one of these or a plain
    `{name: value}` dict — `of()` accepts both, so a plugin row never has to import this class (§6.1, D10b: an
    import an older app cannot satisfy would fail the whole row).

    ⭐ JSON keys are the plain control strings: -model and a LIMS addon read a record with no enum at all.
    """

    def __init__(self, values=None):
        self.__values = {}
        for name, value in (values or {}).items():
            self.__values[CameraControl.of(name)] = value

    @classmethod
    def of(cls, settings):
        """A CameraSettings from itself, a `{name|CameraControl: value}` dict, or None (= empty)."""
        if isinstance(settings, CameraSettings):
            return settings
        return cls(settings or {})

    def get(self, control, default=None):
        return self.__values.get(CameraControl.of(control), default)

    def has(self, control):
        return CameraControl.of(control) in self.__values

    def controls(self):
        return list(self.__values.keys())

    def items(self):
        return list(self.__values.items())

    def merged(self, other):
        """A new CameraSettings: these values, overwritten by `other`'s."""
        values = dict(self.__values)
        values.update(CameraSettings.of(other).__values)
        return CameraSettings(values)

    def __len__(self):
        return len(self.__values)

    def __eq__(self, other):
        return isinstance(other, CameraSettings) and self.__values == other.__values

    def __hash__(self):
        return hash(tuple(sorted((control.value, repr(value)) for control, value in self.__values.items())))

    def __repr__(self):
        return "CameraSettings(%s)" % ", ".join("%s=%r" % (control.value, value)
                                                for control, value in self.__values.items())

    def toJson(self):
        return {control.value: value for control, value in self.__values.items()}

    @classmethod
    def fromJson(cls, entry):
        """Unknown names are dropped: a record written by a newer app must still load on this one."""
        values = {}
        for name, value in (entry or {}).items():
            try:
                values[CameraControl.of(name)] = value
            except ValueError:
                continue
        return cls(values)
