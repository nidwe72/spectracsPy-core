from enum import Enum


class Solvent(Enum):
    """What the oil was diluted INTO (SPEC_settled_measurement.md, 2026-08-26).

    ⭐⭐ WHY THIS EXISTS AT ALL. Until now nothing recorded the solvent — every cross-solvent question had
    to infer it from a FOLDER NAME, and the 2026-08-26 session lost an evening to questions the archive
    could not answer about itself. One field per run makes them answerable forever.

    ⭐ IT ALSO SELECTS THE READ RULE. The settling monitor waits for the Q% curve to stop moving, which is
    the right question in isopropanol and the wrong one in sunflower: an index-matched solvent hides
    incomplete mixing from the turbidity channel, and the curve can decline without ever turning. So the
    plugin reads a sunflower run off the CLEARING GATE instead. ⛔ The enum decides which answer is
    REPORTED, never which is COMPUTED — both are recorded on every run, so nothing is lost and the
    archive stays re-analysable under either rule.

    ⛔ THE MEMBER STRINGS ARE PERSISTED into every report's header. Renaming one silently orphans every
    run that carries it, exactly as MonitorOutcome.SETTLED_IMMEDIATE's comment records. Add, never rename.
    """

    ISOPROPANOL = "ISOPROPANOL"          # the shipping recipe; the whole pre-2026-08-22 archive
    SUNFLOWER_OIL = "SUNFLOWER_OIL"      # index-matched and food-safe; the chosen solvent (DOC ch.4A)
    WHITE_SPIRIT = "WHITE_SPIRIT"        # de-aromatised; the 2026-08-20/21 arm only
    UNKNOWN = "UNKNOWN"                  # ⚠ for runs made before this field existed — never for new ones
