class LampUnreachable(Exception):
    """The lamp switch did not answer (network error, timeout, unexpected reply). SPEC_lamp_switch.md §4.1."""


class LampAuthFailed(LampUnreachable):
    """The lamp switch answered 401: password missing or wrong. A subclass of LampUnreachable, so a caller that
    only cares about "could not switch" handles both."""


class ShellyRpcError(Exception):
    """The plug answered, but refused the call (JSON-RPC `error`, e.g. "Script length exceeded 65535 bytes limit!").
    Not a LampUnreachable: the plug is there."""

    def __init__(self, code, message):
        super().__init__("%s (%s)" % (message, code))
        self.code = code
        self.message = message
