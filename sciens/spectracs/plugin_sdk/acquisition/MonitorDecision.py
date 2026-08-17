class MonitorDecision:
    """What the EVALUATOR wants done after a decision row (SPEC_settled_measurement.md §14.4).

    ⭐ Every field here is the plugin's judgement; the engine only obeys. `promote` hands the row's
    already-reduced mean spectrum to the winner slot (§9.1a) — ⛔ and the engine latches it (§14.6), so a
    second promote after the answer is read is IGNORED rather than overwriting a settled value.
    """

    CONTINUE = "CONTINUE"

    def __init__(self, promote=False, stop=False, outcome=None, branch=None, readAs=None,
                 answer=None, note=None, promoteRow=None):
        self.promote = promote      # this row becomes the answer (first promote wins — §14.6)
        # ⚠ WHICH row, when it is not the current one. On the was-clearing branch the answer is the Q%
        # MINIMUM, which by the time the gate confirms it is two decision rows back — and the spectrum
        # that must be reported is THAT row's window mean, not the gate row's.
        self.promoteRow = promoteRow
        self.stop = stop            # end the run
        self.outcome = outcome      # a MonitorOutcome when stopping
        self.branch = branch        # "arrived-clear" / "was-clearing" — changes what the value MEANS
        self.readAs = readAs        # "FIRST_SETTLED_WINDOW" / "VERTEX"
        self.answer = answer        # optional refined scalar (e.g. a parabola vertex between two rows)
        self.note = note            # free text for the record (e.g. "TEST B reset the gate")

    @staticmethod
    def carryOn(note=None):
        return MonitorDecision(note=note)
