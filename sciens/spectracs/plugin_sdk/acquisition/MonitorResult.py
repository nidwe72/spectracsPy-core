class MonitorResult:
    """What a finished (or stopped) monitored acquisition hands back (SPEC_settled_measurement.md §15).

    ⭐ `spectrum` is the ANSWER's spectrum — the winning window's mean — and it goes exactly where a
    spectrum always went (`step.container[role]`), which is why PROCESSING, EVALUATION, the gauge, the
    PDF and the LIMS publish need no changes at all.

    ⭐ `columns` + `rows` are SELF-DESCRIBING (§15.2): the host knows only `t` and `answer["valueKey"]`,
    never what `Q%` is. ⛔ Fixed columns would hard-code one plugin's physics into the app's persistence.
    """

    def __init__(self, outcome, rows=None, spectrum=None, answer=None, columns=None, policy=None,
                 evaluatorId=None, evaluatorVersion=None, clearingSeconds=None, cancelled=False,
                 capsHit=False, distinctFraction=None, notes=None, error=None):
        self.outcome = outcome
        self.rows = rows or []
        self.spectrum = spectrum
        self.answer = answer                       # {"valueKey", "value", "t", "frameIndex", "readAs", "branch"}
        self.columns = columns or []               # [{"key", "label", "unit"}]
        self.policy = policy
        self.evaluatorId = evaluatorId
        self.evaluatorVersion = evaluatorVersion
        self.clearingSeconds = clearingSeconds     # ⭐ §2.4 — a sigma_fill component, not a curiosity
        self.cancelled = cancelled
        self.capsHit = capsHit
        # ⭐ §23/V1: the fraction of offered frames that were NOT a repeat of their predecessor. Measured
        # at 82 % on the 2026-07-20 archive, which is a x1.10 noise inflation. A run whose duplicate rate
        # drifted is a run whose noise budget drifted with it, so it is recorded rather than assumed.
        self.distinctFraction = distinctFraction
        self.notes = notes or []
        self.error = error                         # the traceback when outcome is FAILED (§25/X5)

    def hasValue(self):
        return self.answer is not None and self.outcome.hasValue()

    def decisionRows(self):
        # ⭐ Only these are persisted (§15.2): ~35 for a 20-minute run, against ~1700 display rows.
        return [row for row in self.rows if row.isDecisionRow]

    def toRecord(self):
        """The generic, self-describing MonitorRecord (§15.2) — plain JSON-able types only.

        ⚠ `rows` is a LIST of dicts with `t` as a VALUE, never a dict keyed by a float: the float-key
        gotcha of SPEC_workflow_persistence.md turns such keys into strings on the way back."""
        return {
            "outcome": self.outcome.value if hasattr(self.outcome, "value") else self.outcome,
            "cancelled": self.cancelled, "capsHit": self.capsHit,
            "evaluatorId": self.evaluatorId, "evaluatorVersion": self.evaluatorVersion,
            "policy": self.policy.toDict() if self.policy is not None else None,
            "clearingSeconds": self.clearingSeconds,
            "distinctFraction": self.distinctFraction,
            "columns": list(self.columns),
            "answer": dict(self.answer) if self.answer else None,
            "rows": [row.toDict() for row in self.decisionRows()],
            "notes": list(self.notes),
        }
