"""
plugin_sdk — the single curated namespace a SpectralPlugin imports from (concept §10 /
SPEC_pumpkin_integration.md B.2). A convenience + decoupling boundary (NOT a security sandbox, §11):
data types + Qt-free result view-models + container->container op adapters + the plugin base.
"""

# --- data / result models (model layer) ---
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.evaluation.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.evaluation.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.evaluation.VerdictView import VerdictView
from sciens.spectracs.model.spectral.evaluation.LabelView import LabelView
from sciens.spectracs.model.spectral.evaluation.MetricFieldView import MetricFieldView
from sciens.spectracs.model.spectral.evaluation.SpectrumPlotView import SpectrumPlotView

# --- ops (container -> container adapters) + Qt-free util ---
from sciens.spectracs.plugin_sdk.ops.MeanOp import MeanOp
from sciens.spectracs.plugin_sdk.ops.TransmissionOp import TransmissionOp
from sciens.spectracs.plugin_sdk.ops.AbsorptionOp import AbsorptionOp
from sciens.spectracs.plugin_sdk.ops.VerdictOp import VerdictOp
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil

# --- base + roles ---
from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
from sciens.spectracs.plugin_sdk.base.MeasurementStep import MeasurementStep
from sciens.spectracs.plugin_sdk.base.MetadataField import MetadataField
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, TRANSMISSION, ABSORPTION

__all__ = [
    "SpectraContainer", "Spectrum", "SpectrumSampleType", "SpectralWorkflow", "SpectralWorkflowPhaseType",
    "SpectralWorkflowStep",
    "EvaluationResult", "ColorSwatchView", "VerdictView", "LabelView", "MetricFieldView", "SpectrumPlotView",
    "MeanOp", "TransmissionOp", "AbsorptionOp", "VerdictOp", "EvaluationColorUtil", "SpectrumFeatureUtil",
    "SpectralPlugin", "MeasurementStep", "MetadataField",
    "REFERENCE", "SAMPLE", "TRANSMISSION", "ABSORPTION",
]
