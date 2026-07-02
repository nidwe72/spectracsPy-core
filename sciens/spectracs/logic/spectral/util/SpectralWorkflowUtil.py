from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep


class SpectralWorkflowUtil(Singleton):
    # Legacy stub for the old SpectralJob screen — builds a one-phase workflow. The former AcquireView*
    # subclasses were retired (they broke the Option-A declarative conversion); base classes carry the same
    # data (type = ACQUIREMENT_VIEW).

    def getWorkflow(self):
        result = SpectralWorkflow()
        acquireViewPhase = SpectralWorkflowPhase()
        acquireViewPhase.setType(SpectralWorkflowPhaseType.ACQUIREMENT_VIEW)
        result.addToPhases(acquireViewPhase)
        acquireViewPhase.addToSteps(SpectralWorkflowStep())
        return result
