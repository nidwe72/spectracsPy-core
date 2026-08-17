from sciens.spectracs.model.spectral.plugin.view.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.plugin.view.LabelView import LabelView
from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SeriesPlotView import SeriesPlotView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.plugin.view.TableView import TableView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
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

    def visitTabGroup(self, view):
        raise NotImplementedError

    def visitSeriesPlot(self, view):
        # SPEC_settled_measurement.md §18.3 — a stacked TIME-SERIES plot. Built once, drawn on screen (the
        # Settling step-tab and the live convergence trace) and on paper (the report page).
        raise NotImplementedError

    def visitTable(self, view):
        # §18.8 — a generic self-describing table; its first customer is the [Decisions] sub-tab.
        raise NotImplementedError


def dispatchItem(item, visitor):
    # The ONE isinstance ladder. Routes a plugin view-model to the visitor method for its type. Types are
    # mutually exclusive, so order is irrelevant. Unknown types are ignored (return None).
    if isinstance(item, MetricFieldView):
        return visitor.visitMetricField(item)
    if isinstance(item, ColorSwatchView):
        return visitor.visitColorSwatch(item)
    if isinstance(item, TabGroupView):
        return visitor.visitTabGroup(item)
    if isinstance(item, VerdictGaugeView):
        return visitor.visitGauge(item)
    if isinstance(item, VerdictView):
        return visitor.visitVerdict(item)
    if isinstance(item, SpectrumCaptureView):
        return visitor.visitSpectrumCapture(item)
    if isinstance(item, SpectrumPlotView):
        return visitor.visitSpectrumPlot(item)
    if isinstance(item, SeriesPlotView):
        return visitor.visitSeriesPlot(item)
    if isinstance(item, TableView):
        return visitor.visitTable(item)
    if isinstance(item, LabelView):
        return visitor.visitLabel(item)
    return None


def willDrawInReport(item):
    """Will the REPORT draw this item? (SPEC_settled_measurement.md §27.13b/D1, §27.18/Z1.)

    ⭐⭐ ONE EMPTINESS RULE, THREE CALLERS: the tab-group renderer (skip an unflagged child, and skip its
    heading with it), the report collector (a nested capture is only worth an /EmbeddedFiles attachment if
    it is actually printed), and the step sub-heading (D4 — never head a section that draws nothing).
    ⛔ Two emptiness rules would eventually disagree, and the disagreement would show as an orphan heading
    or a missing attachment.

    ⚠ `isShownInReport` is the CANONICAL say-so (Edwin, 2026-08-17) and it is honoured at EVERY depth — a
    tab group used to be a hole in that rule, printing children that had explicitly declined the report.
    ⛔ THE GUI IGNORES THIS ENTIRELY: `ReportableView`'s contract is "the report includes only flagged
    items; the GUI ignores the flag", so `QtWorkflowRenderer.visitTabGroup` must NEVER call this — the
    Settling tab bar on screen shows every curve.
    """
    if item is None:
        return False
    if isinstance(item, TabGroupView):
        # A flagged group draws only if something inside it draws; an unflagged group draws nothing at all.
        return bool(item.isShownInReport) and any(willDrawInReport(child) for child in item.children())
    return bool(getattr(item, "isShownInReport", False))
