from enum import Enum


class MonitorOutcome(Enum):
    """How a monitored acquisition ended (SPEC_settled_measurement.md §12.3). The set is CLOSED, and every
    member is said out loud to the operator — ⛔ an outcome without a value must always say WHY, or the
    operator learns to read a missing number as a bug."""

    RUNNING = "RUNNING"

    SETTLED_IMMEDIATE = "SETTLED_IMMEDIATE"            # the fill arrived clear (§9.6) — value stands
    SETTLED_AFTER_CLEARING = "SETTLED_AFTER_CLEARING"  # it cleared in the beam — vertex read
    COMPLETED = "COMPLETED"                            # a plain burst finished its N frames (§10.6)

    NEVER_SETTLED = "NEVER_SETTLED"        # a cap was hit with the gate never firing — ⛔ NO value
    MEASUREMENT_BROKEN = "MEASUREMENT_BROKEN"  # below the plugin's own floor — ⛔ NO value, abort early
    CANCELLED = "CANCELLED"                # the operator stopped it — ⛔ no value unless the evaluator says so
    STALLED = "STALLED"                    # frames stopped arriving (the HOST detects this, §12.2 L3)
    FAILED = "FAILED"                      # the evaluator raised (§25/X5) — partial trajectory still kept

    def hasValue(self):
        return self in (MonitorOutcome.SETTLED_IMMEDIATE, MonitorOutcome.SETTLED_AFTER_CLEARING,
                        MonitorOutcome.COMPLETED)
