from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from sciens.spectracs.logic.spectral.report.WorkflowItemVisitor import WorkflowItemVisitor, dispatchItem
from sciens.spectracs.plugin_sdk.util.GaugeColorUtil import GaugeColorUtil


class MatplotlibWorkflowRenderer(WorkflowItemVisitor):
    # SPEC_bench_pdf_export.md §4 (D4) — M2's half of the M1 render seam: the SAME dispatchItem vocabulary as
    # QtWorkflowRenderer, but emitting matplotlib artists instead of Qt widgets, so screen and paper come from
    # one declaration and cannot drift. Qt-FREE (matplotlib + PIL only) — the report is a second render target,
    # not a Qt canvas. Produces a list of A4-portrait Figures (pages); the host shows them as a preview image
    # (which IS the PDF) and writes them to the PDF.
    #
    # Layout: a simple top-to-bottom flow with a per-block height budget and a y-cursor in figure-fraction
    # coordinates; when the next block would cross the bottom margin a new page starts (header repeated). Not a
    # typesetting engine — "good enough" per Edwin; plots/images get generous fixed budgets.

    __PAGE_W_IN = 8.27          # A4 portrait
    __PAGE_H_IN = 11.69
    __LEFT = 0.08               # content margins (figure fraction)
    __RIGHT = 0.95
    __BOTTOM = 0.05
    __HEADER_TOP = 0.955        # header band sits above the content area
    __CONTENT_TOP = 0.90        # first block starts here (below the header)
    __GAP_IN = 0.10             # vertical gap between blocks

    # Per-block height budgets (inches). Plots/captures get room to breathe; text rows are compact.
    __H_PHASE_IN = 0.34
    __H_LABEL_IN = 0.34
    __H_METRIC_IN = 0.30
    __H_VERDICT_IN = 0.50
    __H_GAUGE_IN = 1.15         # SPEC_roast_ampel.md §8.4 — caption + band + (swatch|pill) row
    __H_SWATCH_IN = 1.30
    __H_PLOT_IN = 3.20
    __H_CAPTURE_IN = 3.30

    # pyqtgraph short colour codes → matplotlib (both accept y/c/m/g/r; keep an explicit map for clarity)
    __COLORS = {"y": "y", "c": "c", "m": "m", "g": "g", "r": "r", "b": "b", "w": "0.2", None: None}

    def render(self, reportView, groups, logoImage=None):
        # groups: ordered list of (phaseLabel, [items]) — only phases that contributed flagged items.
        self.__figures = []
        self.__reportView = reportView
        self.__logoImage = logoImage
        self.__fig = None
        self.__y = 0.0
        self.__newPage()
        for phaseLabel, items in groups:
            self.__drawPhaseHeading(phaseLabel)
            for item in items:
                dispatchItem(item, self)
        return self.__figures

    # --- page + header ---

    def __newPage(self):
        fig = Figure(figsize=(self.__PAGE_W_IN, self.__PAGE_H_IN))
        FigureCanvasAgg(fig)  # attach an Agg canvas so savefig / buffer_rgba work without pyplot
        self.__fig = fig
        self.__figures.append(fig)
        self.__drawHeader()
        self.__y = self.__CONTENT_TOP

    def __drawHeader(self):
        fig = self.__fig
        if self.__logoImage is not None:
            # Logo top-left, sized to the header band height, aspect preserved (SPEC §4: every page header).
            logoHFrac = 0.030
            logoWFrac = logoHFrac * (self.__PAGE_H_IN / self.__PAGE_W_IN) * self.__aspect(self.__logoImage)
            ax = fig.add_axes([self.__LEFT, self.__HEADER_TOP - logoHFrac, logoWFrac, logoHFrac])
            ax.imshow(self.__logoImage)
            ax.axis("off")
        title = getattr(self.__reportView, "title", None) or "Measurement report"
        fig.text(self.__RIGHT, self.__HEADER_TOP - 0.010, title, ha="right", va="top",
                 fontsize=15, fontweight="bold")
        subtitle = getattr(self.__reportView, "subtitle", None)
        if subtitle:
            fig.text(self.__RIGHT, self.__HEADER_TOP - 0.032, subtitle, ha="right", va="top",
                     fontsize=9, color="0.35")
        # a hairline rule under the header (Line2D in figure-fraction coords)
        rule = Line2D([self.__LEFT, self.__RIGHT], [self.__HEADER_TOP - 0.050] * 2,
                      transform=fig.transFigure, color="0.75", lw=0.8)
        fig.add_artist(rule)

    @staticmethod
    def __aspect(pilImage):
        try:
            width, height = pilImage.size
            return (width / height) if height else 4.0
        except Exception:
            return 4.0

    # --- flow helpers ---

    def __frac(self, inches):
        return inches / self.__PAGE_H_IN

    def __ensureSpace(self, inches):
        # Start a new page if this block would cross the bottom margin (unless we are already at page top —
        # then the block is simply taller than a page and we let it clamp).
        if (self.__y - self.__frac(inches)) < self.__BOTTOM and self.__y < self.__CONTENT_TOP - 1e-6:
            self.__newPage()

    def __reserve(self, inches):
        # Reserve a block: return its axes rect [left, bottom, width, height] and advance the cursor.
        self.__ensureSpace(inches)
        height = self.__frac(inches)
        bottom = self.__y - height
        rect = [self.__LEFT, bottom, self.__RIGHT - self.__LEFT, height]
        self.__y = bottom - self.__frac(self.__GAP_IN)
        return rect

    def __textBlock(self, inches, text, fontsize=10, weight="normal", color="black"):
        rect = self.__reserve(inches)
        # place text at the top-left of the reserved rect (rect[1] is its bottom, rect[3] its height)
        self.__fig.text(rect[0], rect[1] + rect[3], text, ha="left", va="top",
                        fontsize=fontsize, fontweight=weight, color=color, wrap=True)

    def __drawPhaseHeading(self, phaseLabel):
        if not phaseLabel:
            return
        self.__textBlock(self.__H_PHASE_IN, str(phaseLabel).upper(), fontsize=11, weight="bold", color="0.25")

    # --- visitor methods (mirror QtWorkflowRenderer's vocabulary) ---

    def visitLabel(self, view):
        self.__textBlock(self.__H_LABEL_IN, view.text, fontsize=10)

    def visitVerdict(self, view):
        self.__textBlock(self.__H_VERDICT_IN, str(view.roastState), fontsize=15, weight="bold")

    def visitGauge(self, view):
        # SPEC_roast_ampel.md §8.4 — the VerdictGaugeView on paper: caption, an OKLab gradient band with a marker
        # (imshow of gradientStops), a swatch chip with the value on it, and the verdict pill. Render-mode aware.
        from sciens.spectracs.model.spectral.plugin.view.GaugeRender import GaugeRender
        util = GaugeColorUtil()
        rect = self.__reserve(self.__H_GAUGE_IN)
        left, bottom, width, height = rect
        components = view.render

        # Layout mirrors a metric row (Edwin 2026-07-24): caption is the left-column label; the band + swatch +
        # pill sit in the value column so the gauge lines up with the metric field values below.
        valueX = left + 0.30 * width
        valueW = 0.68 * width
        if view.caption:
            self.__fig.text(left, bottom + 0.5 * height, str(view.caption), ha="left", va="center",
                            fontsize=9, color="0.25", fontweight="bold")

        # --- band + marker (imshow a 1xN gradient) ---
        if GaugeRender.BAND in components and view.gradientAnchors:
            stops = util.gradientStops(view.gradientAnchors, view.bandLeft, view.bandRight, steps=64)
            row = [list(v / 255.0 for v in util.hexToRgb(hexColor)) for _pos, hexColor in stops]
            ax = self.__fig.add_axes([valueX, bottom + 0.55 * height, valueW, 0.22 * height])
            ax.imshow([row], extent=[0, 1, 0, 1], aspect="auto", origin="lower", interpolation="bilinear")
            for t in (view.thresholds or []):            # dashed threshold tick(s) — the decision line (Option A)
                ax.axvline(util.positionOf(t, view.bandLeft, view.bandRight), color="0.9", lw=1.2, ls=(0, (3, 2)))
            markerPos = util.positionOf(view.value, view.bandLeft, view.bandRight)
            ax.axvline(markerPos, color="0.12", lw=1.4)
            ax.plot([markerPos], [0.5], marker="o", markersize=5, markerfacecolor="white",
                    markeredgecolor="0.12", markeredgewidth=1.2)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

        # --- coarse ZONES bar (Option B): n equal class-coloured segments + dividers + zone marker ---
        if GaugeRender.ZONES in components and view.classes:
            ax = self.__fig.add_axes([valueX, bottom + 0.55 * height, valueW, 0.22 * height])
            n = len(view.classes)
            for i, cls in enumerate(view.classes):
                c = cls.get("colors", {})
                ax.add_patch(Rectangle((i / n, 0), 1 / n, 1, facecolor=c.get("zone", c.get("bg", "#888")),
                                       edgecolor="none"))
            for i in range(1, n):
                ax.axvline(i / n, color="0.9", lw=1.4)
            mp = util.zoneMarkerPosition(view.value, view.thresholds, view.bandLeft, view.bandRight)
            ax.plot([mp], [0.5], marker="o", markersize=6, markerfacecolor="white",
                    markeredgecolor="0.12", markeredgewidth=1.2)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

        # --- swatch chip (with the value on it) + verdict pill, in the value column ---
        rowY = bottom + 0.08 * height
        rowH = 0.34 * height
        cursorX = valueX
        if GaugeRender.SWATCH in components:
            swatchWidth = 0.16 * width
            ax = self.__fig.add_axes([cursorX, rowY, swatchWidth, rowH])
            swatchHex = view.swatchColor or util.gradientColorAt(view.value, view.gradientAnchors)
            ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=swatchHex, edgecolor="0.4"))
            ax.text(0.5, 0.5, self.__gaugeValueText(view), ha="center", va="center",
                    color=(view.valueColor or "#ffffff"), fontsize=9, fontweight="bold")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            cursorX += swatchWidth + 0.03 * width

        if GaugeRender.LABEL in components and view.verdictLabel:
            # a rounded text-bbox is the pill — it auto-sizes to the label and stays a clean pill regardless of
            # the page aspect (a FancyBboxPatch in a wide/short axes distorts into a bowtie).
            colors = self.__gaugeClassColors(view, util)
            self.__fig.text(cursorX, rowY + rowH / 2.0, view.verdictLabel.upper(), ha="left", va="center",
                            fontsize=8, fontweight="bold", color=colors["text"],
                            bbox=dict(boxstyle="round,pad=0.5", facecolor=colors["bg"], edgecolor="none"))
            cursorX += 0.36 * width

        if GaugeRender.VALUE in components:
            self.__fig.text(cursorX, rowY + rowH / 2.0, self.__gaugeValueText(view),
                            ha="left", va="center", fontsize=11, fontweight="bold")

    @staticmethod
    def __gaugeValueText(view):
        try:
            return "%.2f" % float(view.value)
        except (TypeError, ValueError):
            return str(view.value)

    @staticmethod
    def __gaugeClassColors(view, util):
        # the pill colours for the class this value falls in; PDF is white paper -> prefer print* variants if given
        colors = {"text": "#333333", "bg": "#dddddd"}
        if view.classes and view.thresholds is not None and view.bandLeft is not None:
            index = util.classify(view.value, view.thresholds, view.bandLeft, view.bandRight)
            index = max(0, min(index, len(view.classes) - 1))
            declared = view.classes[index].get("colors", {})
            colors = {"text": declared.get("printText", declared.get("text", colors["text"])),
                      "bg": declared.get("printBg", declared.get("bg", colors["bg"]))}
        return colors

    def visitMetricField(self, view):
        rect = self.__reserve(self.__H_METRIC_IN)
        bold = view.style is not None and getattr(view.style, "isLabelBold", False)
        yTop = rect[1] + rect[3]
        self.__fig.text(rect[0], yTop, str(view.label), ha="left", va="top", fontsize=10,
                        fontweight=("bold" if bold else "normal"))
        color = getattr(view, "color", None)
        if color is not None:
            # ‡ extended: value cell = a small filled swatch (mirrors QtWorkflowRenderer so screen and paper match).
            # Height-corrected for the A4 aspect so the patch reads square. If `value` is also set (a colour chip
            # with HSL text, SPEC_color_retrieval §F12), draw the text to the RIGHT of the swatch.
            red, green, blue = color
            side = min(rect[3], 0.12 * rect[2])
            swatchLeft = rect[0] + 0.42 * rect[2]
            swatchWidth = side * (self.__PAGE_H_IN / self.__PAGE_W_IN)
            ax = self.__fig.add_axes([swatchLeft, rect[1] + (rect[3] - side), swatchWidth, side])
            ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=(red / 255.0, green / 255.0, blue / 255.0),
                                   edgecolor="0.4"))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            if view.value is not None:
                self.__fig.text(swatchLeft + swatchWidth + 0.01, yTop, str(view.value),
                                ha="left", va="top", fontsize=9)
        else:
            self.__fig.text(rect[0] + 0.42 * rect[2], yTop, str(view.value), ha="left", va="top", fontsize=10)

    def visitColorSwatch(self, view):
        rect = self.__reserve(self.__H_SWATCH_IN)
        # a square swatch on the left of the reserved band, caption beside it
        side = min(rect[3], rect[2] * (self.__PAGE_H_IN / self.__PAGE_W_IN) * 0.9)
        ax = self.__fig.add_axes([rect[0], rect[1] + (rect[3] - side), side * (self.__PAGE_H_IN / self.__PAGE_W_IN), side])
        red, green, blue = view.rgb
        ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=(red / 255.0, green / 255.0, blue / 255.0),
                               edgecolor="0.4"))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        if view.label:
            self.__fig.text(rect[0] + 0.30 * rect[2], rect[1] + rect[3] * 0.5, view.label,
                            ha="left", va="center", fontsize=10)

    def visitSpectrumPlot(self, view):
        rect = self.__reserve(self.__H_PLOT_IN)
        # leave headroom for the title/axis labels inside the reserved band
        ax = self.__fig.add_axes([rect[0], rect[1] + 0.14 * rect[3], rect[2], 0.72 * rect[3]])
        traces = view.allTraces() if hasattr(view, "allTraces") else [(view.spectrum, None, None)]
        plotted = False
        for spectrum, label, color in traces:
            drawn = self.__plotSpectrum(ax, spectrum, label, self.__COLORS.get(color, color))
            plotted = plotted or drawn
        for band in (getattr(view, "bands", None) or []):
            ax.axvspan(band[0], band[1], color="0.5", alpha=0.15, zorder=-10)
        for marker in (getattr(view, "markers", None) or []):
            ax.axvline(marker[0], color="0.3", ls="--", lw=1)
            if len(marker) > 1 and marker[1]:
                ax.annotate(str(marker[1]), xy=(marker[0], 1), xycoords=("data", "axes fraction"),
                            ha="center", va="bottom", fontsize=8)
        if view.title:
            ax.set_title(view.title, fontsize=10)
        ax.set_xlabel("wavelength (nm)", fontsize=8)
        ax.tick_params(labelsize=7)
        if plotted and any(t[1] for t in traces):
            ax.legend(fontsize=7, loc="best")

    @staticmethod
    def __plotSpectrum(ax, spectrum, label, color):
        if spectrum is None:
            return False
        values = spectrum.valuesByNanometers
        if not values:
            return False
        nanometers = sorted(values.keys())
        ax.plot(nanometers, [values[nm] for nm in nanometers], color=color, lw=1.2,
                label=(label or None))
        return True

    def visitSpectrumCapture(self, view):
        rect = self.__reserve(self.__H_CAPTURE_IN)
        image = getattr(view, "reportImage", None)
        if image is None:
            self.__fig.text(rect[0], rect[1] + rect[3], view.caption or "(no image)",
                            ha="left", va="top", fontsize=9, color="0.4")
            return
        ax = self.__fig.add_axes([rect[0], rect[1] + 0.10 * rect[3], rect[2], 0.78 * rect[3]])
        ax.imshow(image)
        ax.axis("off")
        caption = view.caption
        if getattr(view, "attachmentName", None):
            caption = ("%s  [attachment: %s]" % (caption or "", view.attachmentName)).strip()
        if caption:
            self.__fig.text(rect[0] + 0.5 * rect[2], rect[1], caption, ha="center", va="bottom",
                            fontsize=8, color="0.35")

    # --- rasterisation (Qt-free): a figure -> (width, height, RGBA bytes). The host wraps this into a QImage
    # for the preview; matplotlib's PdfPages writes the same figures to the PDF. ---
    @staticmethod
    def rasterize(fig, scale=1.5):
        fig.set_dpi(100 * scale)
        canvas = fig.canvas
        canvas.draw()
        width, height = canvas.get_width_height()
        return width, height, bytes(canvas.buffer_rgba())
