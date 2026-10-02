class LampUnreachable(Exception):
    """The lamp switch did not answer (network error, timeout, unexpected reply). SPEC_lamp_switch.md §4.1."""


class LampAuthFailed(LampUnreachable):
    """The lamp switch answered 401: password missing or wrong. A subclass of LampUnreachable, so a caller that
    only cares about "could not switch" handles both."""
