class MeasurementStep:
    # A declared interactive acquisition step the host fills from the (virtual) device. `role` is the
    # VirtualCaptureRole / bag role, `frames` the capture count (>=5 to satisfy the preview gate — D14/N).
    # (SPEC_pumpkin_integration.md §9.4 / B.4)

    def __init__(self, role, label, frames=5, mandatory=True):
        self.role = role
        self.label = label
        self.frames = frames
        self.mandatory = mandatory
