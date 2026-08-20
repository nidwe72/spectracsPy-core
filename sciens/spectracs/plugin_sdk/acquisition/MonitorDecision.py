class MonitorDecision:
    """What the EVALUATOR wants done after a decision row (SPEC_settled_measurement.md §14.4).

    ⭐ Every field here is the plugin's judgement; the engine only obeys. `promote` hands the row's
    already-reduced mean spectrum to the winner slot (§9.1a) — ⛔ and the engine latches it (§14.6), so a
    second promote after the answer is read is IGNORED rather than overwriting a settled value.
    """

    CONTINUE = "CONTINUE"

    def __init__(self, promote=False, stop=False, outcome=None, branch=None, readAs=None,
                 answer=None, note=None, promoteRow=None, diagnostics=None, withdraw=False):
        self.promote = promote      # this row becomes the answer (first promote wins — §14.6)
        # ⭐⭐ WITHDRAW — only meaningful from `finalize()` (SPEC_settled_measurement.md §46/B1, §40.4).
        # ⛔ A finalize that REFUSES must take the gate's answer with it. Without this the run keeps a
        # number the end-of-run read has just judged unsound: run 003's gate promoted 8.450 off the dark
        # floor, finalize refuses, and leaving 8.450 in the record would be the §32.2 defect surviving the
        # very fix written for it. ⚠ The rows and the trajectory are kept; only the ANSWER goes.
        self.withdraw = withdraw
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
        # ⭐⭐ WHAT THE RUN SAYS ABOUT ITSELF — an OPAQUE dict the engine carries into the answer without
        # reading it (SPEC_settled_measurement.md §30/R2.1). The dev plugin puts `browningPerMinute`, the
        # depth it measured and the threshold it measured against in here; ⛔ the engine must never learn
        # what any of those mean, which is the same rule that keeps `values` opaque on a MonitorRow.
        # ⭐ It rides inside `answer`, which `MonitorResult.toRecord()` already serialises wholesale — so a
        # plugin can record a new diagnostic without a record key, a result field or a migration.
        self.diagnostics = dict(diagnostics) if diagnostics else None

    @staticmethod
    def carryOn(note=None):
        return MonitorDecision(note=note)
