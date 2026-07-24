from sciens.spectracs.model.spectral.plugin.view.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.plugin.view.LabelView import LabelView
from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.plugin.view.VerdictView import VerdictView
from sciens.spectracs.model.spectral.plugin.view.VerdictGaugeView import VerdictGaugeView


class WorkflowItemVisitor:
    # SPEC_plugin_driven_convergence.md §2A — the target-agnostic render seam. One method per renderable
    # plugin view-model; each render TARGET (Qt now, matplotlib in M2) implements this interface. The single
    # isinstance ladder lives ONCE, in dispatchItem() below, so every target renders the same vocabulary in
    # lock-step — screen and PDF cannot drift, and a new view-model type is a one-place change.

    def visitLabel(self, view):
        raise NotImplementedError

    def visitMetricField(self, view):
        raise NotImplementedError

    def visitColorSwatch(self, view):
        raise NotImplementedError

    def visitVerdict(self, view):
        raise NotImplementedError

    def visitGauge(self, view):
        raise NotImplementedError

    def visitSpectrumPlot(self, view):
        raise NotImplementedError

    def visitSpectrumCapture(self, view):
        raise NotImplementedError


def dispatchItem(item, visitor):
    # The ONE isinstance ladder. Routes a plugin view-model to the visitor method for its type. Types are
    # mutually exclusive, so order is irrelevant. Unknown types are ignored (return None).
    if isinstance(item, MetricFieldView):
        return visitor.visitMetricField(item)
    if isinstance(item, ColorSwatchView):
        return visitor.visitColorSwatch(item)
    if isinstance(item, VerdictGaugeView):
        return visitor.visitGauge(item)
    if isinstance(item, VerdictView):
        return visitor.visitVerdict(item)
    if isinstance(item, SpectrumCaptureView):
        return visitor.visitSpectrumCapture(item)
    if isinstance(item, SpectrumPlotView):
        return visitor.visitSpectrumPlot(item)
    if isinstance(item, LabelView):
        return visitor.visitLabel(item)
    return None
