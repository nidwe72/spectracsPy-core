import copy

from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModule import FlatOffsetBaselineLogicModule
from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModuleParameters import FlatOffsetBaselineLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer


class BaselineOffsetOp:
    # container -> container: flat-offset baseline every spectrum (subtract the transparent-window floor). Thin,
    # role-agnostic adapter over FlatOffsetBaselineLogicModule — like MeanOp, it applies to each bag in the
    # container. NON-DESTRUCTIVE: each spectrum is deep-copied before the LogicModule mutates it, so a caller can
    # safely improve a spectrum it is still displaying/measuring in raw form (SPEC_capability_proof.md §7.0.1 /
    # §8.1, Entry 0).

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        result = SpectraContainer()
        for role, spectrum in container.getSpectra().items():
            clone = copy.deepcopy(spectrum)
            parameters = FlatOffsetBaselineLogicModuleParameters()
            parameters.setSpectrum(clone)
            corrected = FlatOffsetBaselineLogicModule().flatOffsetBaseline(parameters).getSpectrum()
            result.addToSpectra(corrected, role)
        result.addToInputs(container)
        return result
