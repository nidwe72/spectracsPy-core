from base.Singleton import Singleton
from spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from spectracs.model.spectral.workflow.phase.acquireView.AcquireViewSpectralWorkflowPhase import \
    AcquireViewSpectralWorkflowPhase


class SpectralWorkflowUtil(Singleton):

    def getWorkflow(self):
        result=SpectralWorkflow()
        acquireViewPhase = AcquireViewSpectralWorkflowPhase()
        result.addToPhases(acquireViewPhase)
        return result
