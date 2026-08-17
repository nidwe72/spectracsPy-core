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
    # The view-model's `style` names -> matplotlib linestyles. Same vocabulary the screen renderer maps to Qt
    # pen styles (SPEC_soret_448_trim.md §12.2), so a dashed baseline is dashed on both.
    __LINE_STYLES = {"dashed": "--", "dotted": ":", None: "-"}
    __LEGEND_PADDING = 34.0    # points; the default when a view declares a position but no padding

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
        traces = view.allTraces() if hasattr(view, "allTraces") else [(view.spectrum, None, None, None)]
        # axis="dn" — same display-only inverse decode the screen uses, so paper and screen cannot drift
        # (SPEC_capture_quality.md §16.7.2e).
        asDn = getattr(view, "axis", None) == "dn"
        if asDn:
            from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
            util = SpectralColorUtil()
        plotted = False
        for spectrum, label, color, style in traces:
            drawn = self.__plotSpectrum(ax, util.toDisplayDnSpectrum(spectrum) if asDn else spectrum,
                                        label, self.__COLORS.get(color, color), style)
            plotted = plotted or drawn
        levels = getattr(view, "levels", None) or []
        if asDn:
            ax.set_ylabel("camera DN", fontsize=8)
            if not levels:   # legacy blob (no declared guards) — same fallback rule as the screen renderer
                ax.axhline(16.0, color="#c87a3c", ls="--", lw=0.8)
        for band in (getattr(view, "bands", None) or []):
            color = self.__COLORS.get(band[3], band[3]) if len(band) > 3 and band[3] else "0.5"
            ax.axvspan(band[0], band[1], color=color, alpha=0.15, zorder=-10)
            if len(band) > 2 and band[2]:
                # INSIDE the axes, hanging from the top spine — the strip ABOVE the axes belongs to the marker
                # labels, and with four bands plus a Q marker the two rows collide (§18 S9/defect 10).
                # ⚠ EDGE CLAMP (§25.3): a caption centred on a band near the window edge overflows and is cut.
                centre = (band[0] + band[1]) / 2.0
                low, high = ax.get_xlim()
                margin = 0.06 * (high - low)
                align = "right" if centre > high - margin else ("left" if centre < low + margin else "center")
                ax.annotate(str(band[2]), xy=(centre, 0.985), xycoords=("data", "axes fraction"),
                            ha=align, va="top", fontsize=6.5, color="0.45")
        for level in levels:
            # SPEC_soret_448_trim.md §12.2 — unranged = a full-width guide line (the DN guards), ranged = a bar
            # over the band at that height (a band mean). ⚠ NOT gamma-encoded on a dn plot: only the CURVE is.
            value, lowNm, highNm, label, color, style, number = tuple(level) + (None,) * (7 - len(level))
            barColor = self.__COLORS.get(color, color) or "0.35"
            lineStyle = self.__LINE_STYLES.get(style, "-")
            if lowNm is None or highNm is None:
                ax.axhline(value, color=barColor, ls=lineStyle, lw=0.8)
                if label:
                    ax.annotate(str(label), xy=(0.005, value), xycoords=("axes fraction", "data"),
                                ha="left", va="bottom", fontsize=6, color=barColor)
            else:
                ax.plot([lowNm, highNm], [value, value], color=barColor, ls=lineStyle, lw=1.8)
                if number is not None:
                    # §25.2 — the numbered badge, on paper a real circle. Fill darkened so the white numeral
                    # is legible; ring in the bar's own colour so the badge belongs to its bar.
                    ax.annotate(str(number), xy=((lowNm + highNm) / 2.0, value), ha="center", va="center",
                                fontsize=6, color="white", zorder=6,
                                bbox=dict(boxstyle="circle,pad=0.32", fc=self.__darken(color) or barColor,
                                          ec=barColor, lw=0.8))
                elif label:
                    ax.annotate(str(label), xy=((lowNm + highNm) / 2.0, value), ha="center", va="bottom",
                                fontsize=6, color=barColor)
        for marker in (getattr(view, "markers", None) or []):
            ax.axvline(marker[0], color="0.3", ls="--", lw=1)
            if len(marker) > 1 and marker[1]:
                # ⚠ BOTTOM row, matching the screen: a marker usually sits inside a band (λmax lives in the Q
                # window), and band captions own the top row. Two captions on one row overprint.
                ax.annotate(str(marker[1]), xy=(marker[0], 0.015), xycoords=("data", "axes fraction"),
                            ha="center", va="bottom", fontsize=7, color="0.35")
        if view.title:
            ax.set_title(view.title, fontsize=10)
        ax.set_xlabel("wavelength (nm)", fontsize=8)
        ax.tick_params(labelsize=7)
        drewLegend = self.__drawLegend(ax, view)
        # ⚠ A view with a DECLARED legend must not also get matplotlib's own trace legend — the curves are
        # already named in ours, and the baseline would appear TWICE on paper (§23.3 duck #7).
        if plotted and not drewLegend and any(t[1] for t in traces):
            ax.legend(fontsize=7, loc="best")

    @classmethod
    def __darken(cls, color, factor=0.55):
        # The badge fill (SPEC_soret_448_trim.md §25.2). Shares the rule with the screen renderer via
        # SpectralColorUtil, so a badge is the same colour on paper as on screen.
        from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
        darkened = SpectralColorUtil().darkenHex(color, factor)
        return darkened if isinstance(darkened, str) and darkened.startswith("#") else None

    def __drawLegend(self, ax, view):
        # §25.2 — the declared legend box: square corners, semitransparent, anchored to a corner with a
        # padding MAGNITUDE whose signs come from the enum. Rows are derived from the view, so paper and
        # screen list the same things in the same order.
        from sciens.spectracs.model.spectral.plugin.view.LegendPosition import LegendPosition
        position = LegendPosition.parse(getattr(view, "legendPosition", None))
        rows = view.legendRows() if position is not None and hasattr(view, "legendRows") else []
        if not rows:
            return False
        from matplotlib.patches import Rectangle
        cornerX, cornerY = position.corner()
        padding = (getattr(view, "legendPadding", None) or self.__LEGEND_PADDING) / 72.0   # points -> inches
        figureWidth, figureHeight = ax.figure.get_size_inches()
        axesWidth = ax.get_position().width * figureWidth
        axesHeight = ax.get_position().height * figureHeight
        # ⭐ ONE ax.text PER ROW, because each row carries its OWN colour — a curve is named by its colour
        # (§25.2) and matplotlib paints a whole text block in one. ⚠ The colours are DARKENED for paper: the
        # screen's yellow #e8e337 on white is unreadable. Same two-ground rule as the badge fills.
        fontSize = 6.0
        lineHeight = (fontSize * 1.7 / 72.0) / axesHeight          # points -> axes fraction
        boxWidth = (max(len(row[1]) for row in rows) * fontSize * 0.62 + 22.0) / 72.0 / axesWidth
        boxHeight = lineHeight * len(rows) + lineHeight * 0.5
        left = (1.0 - padding / axesWidth - boxWidth) if cornerX == 1.0 else (padding / axesWidth)
        top = (1.0 - padding / axesHeight) if cornerY == 0.0 else (padding / axesHeight + boxHeight)
        ax.add_patch(Rectangle((left, top - boxHeight), boxWidth, boxHeight, transform=ax.transAxes,
                               facecolor=(1, 1, 1, 0.82), edgecolor="0.45", linewidth=0.6,
                               zorder=8, clip_on=False))
        for index, (number, label, color) in enumerate(rows):
            rowY = top - lineHeight * (index + 0.85)
            paperColor = self.__darken(self.__COLORS.get(color, color)) or "0.25"
            if number is not None:
                ax.annotate(str(number), xy=(left + 0.012, rowY + lineHeight * 0.3),
                            xycoords=ax.transAxes, ha="center", va="center", fontsize=fontSize - 1.2,
                            color="white", zorder=10,
                            bbox=dict(boxstyle="circle,pad=0.3", fc=paperColor,
                                      ec=self.__COLORS.get(color, color) or "0.45", lw=0.6))
            ax.text(left + 0.028, rowY, str(label), transform=ax.transAxes, fontsize=fontSize,
                    ha="left", va="baseline", color="0.15" if number is not None else paperColor, zorder=10)
        return True

    @classmethod
    def __plotSpectrum(cls, ax, spectrum, label, color, style=None):
        if spectrum is None:
            return False
        values = spectrum.valuesByNanometers
        if not values:
            return False
        nanometers = sorted(values.keys())
        ax.plot(nanometers, [values[nm] for nm in nanometers], color=color, lw=1.2,
                ls=cls.__LINE_STYLES.get(style, "-"), label=(label or None))
        return True

    def visitTabGroup(self, view):
        # T2 (SPEC_simplified_plugin_navigation.md §7b): paper has no tabs — stack the children under their tab
        # headings so the reader sees every grouped image/plot (e.g. full-frame + cropped-ROI raster).
        for label, child in view.tabs:
            if label:
                self.__textBlock(self.__H_LABEL_IN, str(label), fontsize=10, weight="bold", color="0.3")
            for item in (child if isinstance(child, list) else [child]):
                dispatchItem(item, self)

    def visitSeriesPlot(self, view):
        """The stacked time-series plot on PAPER (SPEC_settled_measurement.md §18.3).

        ⭐ The same declaration the screen draws, so a settling curve in the report and one on the bench
        cannot drift — which matters more here than usual: ⭐⭐ a `Q%` that carries its own settling curve
        is a different object from a bare number. It shows the reader that the value was CHOSEN, when,
        and on what evidence (§18.6).
        ⚠ Per-panel log scale is honoured (§18.7): `A_valley` falls 40x, and on a linear axis the part the
        gate judges would be invisible.
        """
        panels = getattr(view, "panels", None) or []
        if not panels:
            return
        if view.title:
            self.__textBlock(self.__H_LABEL_IN, str(view.title), fontsize=10, weight="bold")
        for label, value in (getattr(view, "header", None) or []):
            self.__textBlock(self.__H_METRIC_IN, "%s:  %s" % (label, value), fontsize=9)

        heightPerPanel = self.__H_PLOT_IN * 0.62
        for panelSpec in panels:
            rect = self.__reserve(heightPerPanel)
            ax = self.__fig.add_axes([rect[0], rect[1] + 0.16 * rect[3], rect[2], 0.70 * rect[3]])
            for series in panelSpec.get("series", []):
                ax.plot(series["xs"], series["ys"], marker="o", markersize=3, linewidth=1.2,
                        color=self.__COLORS.get(series.get("color"), series.get("color")) or "#e08000",
                        label=series.get("label"))
            for level in panelSpec.get("levels", []):
                ax.axhline(level["value"], color="0.5", ls="--", lw=0.8)
                if level.get("label"):
                    ax.annotate(level["label"], xy=(0.99, level["value"]), xycoords=("axes fraction", "data"),
                                fontsize=6, color="0.4", ha="right", va="bottom")
            for marker in panelSpec.get("markers", []):
                ax.axvline(marker["x"], color="#4aa3df", ls=":", lw=0.9)
                if marker.get("label"):
                    ax.annotate(marker["label"], xy=(marker["x"], 0.98), xycoords=("data", "axes fraction"),
                                fontsize=6, color="#4aa3df", ha="left", va="top", rotation=90)
            for point in panelSpec.get("points", []):
                ax.plot([point["x"]], [point["y"]], marker="*", markersize=11, color="#1f9d55", linestyle="")
                if point.get("label"):
                    ax.annotate(point["label"], xy=(point["x"], point["y"]), fontsize=7, color="#1f9d55",
                                xytext=(4, 4), textcoords="offset points")
            if panelSpec.get("scale") == "log":
                ax.set_yscale("log")
            ax.set_ylabel(panelSpec.get("label") or panelSpec.get("key") or "", fontsize=8)
            ax.set_xlabel(getattr(view, "xLabel", "") or "", fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.25, linewidth=0.5)

        for label, value in (getattr(view, "footer", None) or []):
            # ⭐ §18.7: the audit line travels onto the paper too — a graph without it is a picture.
            self.__textBlock(self.__H_METRIC_IN * 0.9, "%s:  %s" % (label, value), fontsize=7, color="0.45")

    def visitTable(self, view):
        # §18.8 — the generic table on paper. ⚠ It is DIAGNOSTIC content: a plugin decides whether to
        # include the tab at all, so a customer's report never carries 34 rows of decision arithmetic.
        rows = view.textRows()
        if not rows:
            return
        if view.title:
            self.__textBlock(self.__H_LABEL_IN, str(view.title), fontsize=10, weight="bold")
        height = min(self.__H_PLOT_IN, self.__H_METRIC_IN * (len(rows) + 2))
        rect = self.__reserve(height)
        ax = self.__fig.add_axes([rect[0], rect[1], rect[2], rect[3]])
        ax.axis("off")
        table = ax.table(cellText=rows, colLabels=view.headerLabels(), loc="upper center", cellLoc="right")
        table.auto_set_font_size(False)
        table.set_fontsize(6)
        table.scale(1.0, 1.1)
        if view.caption:
            self.__textBlock(self.__H_METRIC_IN, view.caption, fontsize=7, color="0.45")

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
