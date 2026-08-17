from enum import Enum


class MonitorMode(Enum):
    """PRODUCT stops at the read; DIAGNOSTIC keeps observing to a fixed arc (SPEC_settled_measurement.md §11.9c).

    ⭐ This is the ONE algorithmic difference between a bench measurement and a diagnostic run — and it is
    safe only because the answer is LATCHED at the read (§14.6): later rows join the trajectory but can
    never become the answer.
    ⛔ It is a HOST argument, never a plugin constant (§17/D3) — otherwise the DEV plugin would run in
    diagnostic mode inside an end user's wizard.
    """

    PRODUCT = "PRODUCT"
    DIAGNOSTIC = "DIAGNOSTIC"
