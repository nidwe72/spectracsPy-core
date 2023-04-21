from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.workflow.phase.acquireView.AcquireViewSpectralWorkflowPhase import \
    AcquireViewSpectralWorkflowPhase
from sciens.spectracs.model.spectral.workflow.phase.setp.AcquireViewSpectralWorkflowStep import AcquireViewSpectralWorkflowStep


class SpectralWorkflowUtil(Singleton):

    def getWorkflow(self):
        result=SpectralWorkflow()
        acquireViewPhase = AcquireViewSpectralWorkflowPhase()
        result.addToPhases(acquireViewPhase)

        acquireViewSpectralWorkflowStep = AcquireViewSpectralWorkflowStep()
        acquireViewPhase.addToSteps(acquireViewSpectralWorkflowStep)

        return result
