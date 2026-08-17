import io
import json
import os
import tempfile

from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
from sciens.spectracs.logic.spectral.report.WorkflowItemVisitor import willDrawInReport


class WorkflowReportBuilder:
    # SPEC_bench_pdf_export.md §1/§5/§6 (D5/D6) — builds the report from a workflow: it collects the flagged
    # items, renders them through the matplotlib renderer, and on Save writes the pages to a PDF and embeds —
    # via pypdf — the whole-Workflow JSON plus each flagged capture as a named /EmbeddedFiles attachment
    # (extractable on command, §5b).
    #
    # QT-FREE (S2 — SPEC_project_structure.md). It used to be the host bridge as well ("Qt allowed"), doing the
    # QImage→PIL conversion and handing back preview QPixmaps. Both ends moved to the host:
    #   - the QImage→PIL conversion now happens where `.image` is set (the bench view), so the host fills BOTH
    #     `.image` and `.reportImage` — which is what SpectrumCaptureView's docstring always said it would;
    #   - the preview pixmaps are built by the host from figures() + MatplotlibWorkflowRenderer.rasterize(),
    #     which is already Qt-free.
    # This class now reads ONLY `capture.reportImage` (a PIL image) and never `.image`. A LIMS addon can
    # therefore build a report from a stored workflow with no Qt present at all: toJson() never serializes
    # pixels, so reportImage is simply absent and the capture is skipped.
    #
    # Visible body = the isShownInReport subset (curated, grouped by phase, workflow order).
    # Hidden payload = workflow.toReportJson() (the complete machine record).

    # Heading levels a group may ask for (D4). ⭐ §27.18/Z2 budgets THREE headings on a page — phase, step,
    # tab label — so there is no third level here and a tab group prints no title of its own.
    __LEVEL_PHASE = 0
    __LEVEL_STEP = 1

    __PHASE_LABELS = {
        SpectralWorkflowPhaseType.ACQUISITION: "Acquisition",
        SpectralWorkflowPhaseType.PROCESSING: "Processing",
        SpectralWorkflowPhaseType.EVALUATION: "Evaluation",
        SpectralWorkflowPhaseType.METADATA: "Details",   # match the chevron (Edwin 2026-07-25); a doc SECTION
        SpectralWorkflowPhaseType.PUBLISHING: "Publishing",  # heading — keep the plain word (nav says "Verdict/Publish")
    }

    def __init__(self, workflow, reportView):
        self.__workflow = workflow
        self.__reportView = reportView
        self.__figures = []
        self.__captures = []  # (attachmentName, pngBytes) for the flagged SpectrumCaptureViews
        self.__assignedNames = set()  # names handed out this build — a pixel-less capture still reserves one

    def build(self):
        groups = self.__collectGroups()
        logo = self.__loadLogo()
        self.__figures = MatplotlibWorkflowRenderer().render(self.__reportView, groups, logoImage=logo)
        return self

    # --- collection: flagged items grouped by phase (workflow order); captures get a PIL rendition + name ---

    def __collectGroups(self):
        # ⭐ D4 (SPEC_settled_measurement.md §27.14a): a phase the RECORD marks as sectioned contributes one
        # group PER STEP, headed by the step's label ("Reference" / "Sample"), instead of one flat group
        # under the phase name. ⛔ The declaration is read from the workflow, never from a plugin or a
        # navigation policy: a LIMS addon rebuilding a report has neither, and a document's shape must not
        # depend on whether a plugin happens to be loaded.
        sectioned = self.__workflow.getSectionedPhases() if hasattr(self.__workflow, "getSectionedPhases") \
            else frozenset()
        groups = []
        captureIndex = 0
        for phaseType in SpectralWorkflowPhaseType:
            phase = self.__workflow.getPhase(phaseType)
            if phase is None:
                continue
            phaseLabel = self.__PHASE_LABELS.get(phaseType, str(phaseType))
            phaseItems = []
            stepGroups = []
            for step in phase.getSteps().values():
                items = []
                for item in self.__stepItems(step):
                    if not willDrawInReport(item):
                        continue
                    captureIndex = self.__prepareCaptures(item, step, captureIndex)
                    items.append(item)
                if not items:
                    continue
                if phaseType in sectioned:
                    stepGroups.append((step.getLabel() or phaseLabel, items, self.__LEVEL_STEP))
                else:
                    phaseItems.extend(items)
            if phaseItems:
                groups.append((phaseLabel, phaseItems, self.__LEVEL_PHASE))
            elif stepGroups:
                # ⚠ The phase heading is emitted even though the phase itself contributes no loose items:
                # it is the parent of the step sections, and dropping it would leave "Reference"/"Sample"
                # floating with no statement of which phase they belong to.
                groups.append((phaseLabel, [], self.__LEVEL_PHASE))
            groups.extend(stepGroups)
        return groups

    def __prepareCaptures(self, item, step, captureIndex):
        # ⛔⛔ §27.14/W6 — A CAPTURE NESTED IN A PRINTED TAB GROUP USED TO BE DRAWN BUT NEVER ATTACHED. This
        # method only ever saw TOP-LEVEL items, while the renderer happily stacked a group's children ⇒ the
        # page would show an image the machine payload did not carry, and its caption would silently lose
        # the "[attachment: …]" marker. It never bit only because no tab group had ever been printed.
        # ⭐ Decided (F3): TRAVERSE — the same descent the bench already does to fill nested pixels. ⚠ Only
        # captures that WILL be drawn are attached, or the PDF would carry a PNG for an image it never shows.
        if isinstance(item, TabGroupView):
            for child in item.children():
                if willDrawInReport(child):
                    captureIndex = self.__prepareCaptures(child, step, captureIndex)
            return captureIndex
        if isinstance(item, SpectrumCaptureView):
            captureIndex += 1
            self.__prepareCapture(item, step, captureIndex)
        return captureIndex

    @staticmethod
    def __stepItems(step):
        items = []
        result = step.getEvaluationResult() if hasattr(step, "getEvaluationResult") else None
        if result is not None:
            items.extend(result.getItems())
        view = step.getView() if hasattr(step, "getView") else None
        if view is not None and hasattr(view, "isShownInReport"):  # a passive, reportable view (plot/capture)
            items.append(view)
        return items

    def __prepareCapture(self, capture, step, index):
        # Assign the /EmbeddedFiles name (role-based when known, else sequential) and take the PNG bytes pypdf
        # attaches from the host-supplied Qt-free rendition. `.reportImage` is a PIL image the host derived from
        # its QImage (S2); a workflow loaded from JSON has none — captures carry no pixels — so it is skipped.
        #
        # ⛔⛔ NAMES MUST BE UNIQUE, AND THEY WERE NOT (found while building F3, 2026-08-17). The name was
        # derived from the STEP'S ROLE alone, but an acquisition step declares TWO reportable captures (full
        # frame + cropped ROI, §7b) — so both were called `capture_sample.png`, and `pypdf.add_attachment`
        # keeps ONE entry per name. ⇒ MEASURED: three captures on one step produced a single
        # `/EmbeddedFiles` entry. Every report the app has written has been quietly dropping the cropped
        # frame from its machine payload, while printing it on the page.
        # ⭐ The FIRST capture of a role keeps exactly the name it has always had, so nothing that reads an
        # existing report by name breaks; the rest are suffixed.
        # ⚠ An archived report reconstructed by `report_reconstruct` arrives with `attachmentName` ALREADY
        # SET from its own JSON, so this branch is skipped and historical names are preserved untouched.
        if not capture.attachmentName:
            role = step.getRole() if hasattr(step, "getRole") else None
            base = "capture_%s" % _slug(role) if role else "capture_%d" % index
            capture.attachmentName = self.__uniqueAttachmentName(base)
        pil = capture.reportImage
        if pil is None:
            return
        buffer = io.BytesIO()
        pil.convert("RGB").save(buffer, format="PNG")
        self.__captures.append((capture.attachmentName, buffer.getvalue()))

    def __uniqueAttachmentName(self, base):
        # `capture_sample.png`, then `capture_sample_2.png`, … — the first of a role is unchanged.
        taken = {name for name, _bytes in self.__captures} | set(self.__assignedNames)
        candidate = "%s.png" % base
        suffix = 1
        while candidate in taken:
            suffix += 1
            candidate = "%s_%d.png" % (base, suffix)
        self.__assignedNames.add(candidate)
        return candidate

    def __loadLogo(self):
        from PIL import Image
        path = self.__resourcePath("logo.png")
        if path is None or not os.path.exists(path):
            return None
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            return None

    @staticmethod
    def __resourcePath(name):
        directory = os.path.dirname(os.path.abspath(__file__))
        while directory != os.path.dirname(directory):
            candidate = os.path.join(directory, "resource", name)
            if os.path.exists(candidate):
                return candidate
            directory = os.path.dirname(directory)
        return None

    # --- the rendered pages (the preview IS the PDF, page for page) ---

    def figures(self):
        # The matplotlib figures, in page order. The HOST turns these into whatever it paints with — the bench
        # rasterises each via MatplotlibWorkflowRenderer.rasterize() (Qt-free: width, height, rgba bytes) and
        # wraps it in a QPixmap. This class used to do that itself; that was its last Qt dependency (S2).
        return list(self.__figures)

    def pageCount(self):
        return len(self.__figures)

    # --- save: matplotlib pages -> PDF, then pypdf embeds workflow.json + capture attachments ---

    def savePdf(self, path):
        from matplotlib.backends.backend_pdf import PdfPages
        tempPath = None
        try:
            handle, tempPath = tempfile.mkstemp(suffix=".pdf")
            os.close(handle)
            with PdfPages(tempPath) as pdf:
                for figure in self.__figures:
                    pdf.savefig(figure)
            self.__embedAttachments(tempPath, path)
        finally:
            if tempPath is not None and os.path.exists(tempPath):
                os.remove(tempPath)
        return path

    def pdfBytes(self):
        # The finished PDF (pages + embedded workflow.json + capture PNGs) as bytes — for the LIMS publish
        # RPC, which ships the report to the server (SPEC_lims_integration.md L6). Reuses savePdf via a temp.
        handle, tempPath = tempfile.mkstemp(suffix=".pdf")
        os.close(handle)
        try:
            self.savePdf(tempPath)
            with open(tempPath, "rb") as source:
                return source.read()
        finally:
            if os.path.exists(tempPath):
                os.remove(tempPath)

    def __embedAttachments(self, sourcePdfPath, targetPath):
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        writer.append(PdfReader(sourcePdfPath))
        if getattr(self.__reportView, "embedMetadata", True):
            # Stamp the capture DECODE MODEL into the run's machine record (SPEC_capture_quality.md §17.6/8).
            # A post-§17 absorbance is ~2.2x a pre-§17 one, and every archived baseline is pre-§17 — band RATIOS
            # stay comparable across the boundary, absolute absorbance and colour do not. Stamping makes the era
            # readable off the artifact instead of inferred from its date. Injected here rather than in
            # SpectralWorkflow.toReportJson so the -model tier keeps no dependency on the decode util (and it
            # needs no DB column: the report IS the travelling record).
            from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
            report = self.__workflow.toReportJson()
            report.setdefault("header", {})["captureDecode"] = SpectralColorUtil().captureDecodeDescriptor()
            payload = json.dumps(report, indent=2).encode("utf-8")
            writer.add_attachment("workflow.json", payload)
        for name, pngBytes in self.__captures:
            writer.add_attachment(name, pngBytes)
        with open(targetPath, "wb") as target:
            writer.write(target)


def _slug(text):
    return "".join(character if character.isalnum() else "_" for character in str(text)).strip("_").lower()
