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
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.plugin.view.VerdictView import VerdictView
from sciens.spectracs.model.spectral.plugin.view.LabelView import LabelView
from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
from sciens.spectracs.model.spectral.plugin.view.MetricFieldViewStyle import MetricFieldViewStyle
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.CaptureView import CaptureView
from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
from sciens.spectracs.model.spectral.plugin.view.LimsPublishView import LimsPublishView

# --- ops (container -> container adapters) + Qt-free util ---
from sciens.spectracs.plugin_sdk.ops.MeanOp import MeanOp
from sciens.spectracs.plugin_sdk.ops.TransmissionOp import TransmissionOp
from sciens.spectracs.plugin_sdk.ops.AbsorptionOp import AbsorptionOp
from sciens.spectracs.plugin_sdk.ops.VerdictOp import VerdictOp
from sciens.spectracs.plugin_sdk.ops.BaselineOffsetOp import BaselineOffsetOp
from sciens.spectracs.plugin_sdk.ops.SmoothOp import SmoothOp
from sciens.spectracs.plugin_sdk.ops.MedianFilterOp import MedianFilterOp
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil

# --- base + roles ---
from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
from sciens.spectracs.plugin_sdk.base.MeasurementStep import MeasurementStep
from sciens.spectracs.plugin_sdk.base.MetadataField import MetadataField
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, TRANSMISSION, ABSORPTION

# --- version / compatibility gate ---
from sciens.spectracs.plugin_sdk.version import (
    SDK_VERSION, PluginSdkVersionError, checkSdkCompatible, checkSdkCompatibleVersion)

__all__ = [
    "SpectraContainer", "Spectrum", "SpectrumSampleType", "SpectralWorkflow", "SpectralWorkflowPhaseType",
    "SpectralWorkflowStep",
    "EvaluationResult", "ColorSwatchView", "VerdictView", "LabelView", "MetricFieldView", "MetricFieldViewStyle",
    "SpectrumPlotView", "SpectrumCaptureView", "CaptureView", "ReportView", "LimsPublishView",
    "MeanOp", "TransmissionOp", "AbsorptionOp", "VerdictOp", "BaselineOffsetOp", "SmoothOp", "MedianFilterOp",
    "EvaluationColorUtil", "SpectrumFeatureUtil",
    "SpectralPlugin", "MeasurementStep", "MetadataField",
    "REFERENCE", "SAMPLE", "TRANSMISSION", "ABSORPTION",
    "SDK_VERSION", "PluginSdkVersionError", "checkSdkCompatible", "checkSdkCompatibleVersion",
]
