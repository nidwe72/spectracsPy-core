import io
import json
import os
import tempfile

from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer


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

    __PHASE_LABELS = {
        SpectralWorkflowPhaseType.ACQUISITION: "Acquisition",
        SpectralWorkflowPhaseType.PROCESSING: "Processing",
        SpectralWorkflowPhaseType.EVALUATION: "Evaluation",
        SpectralWorkflowPhaseType.METADATA: "Metadata",
        SpectralWorkflowPhaseType.PUBLISHING: "Publishing",
    }

    def __init__(self, workflow, reportView):
        self.__workflow = workflow
        self.__reportView = reportView
        self.__figures = []
        self.__captures = []  # (attachmentName, pngBytes) for the flagged SpectrumCaptureViews

    def build(self):
        groups = self.__collectGroups()
        logo = self.__loadLogo()
        self.__figures = MatplotlibWorkflowRenderer().render(self.__reportView, groups, logoImage=logo)
        return self

    # --- collection: flagged items grouped by phase (workflow order); captures get a PIL rendition + name ---

    def __collectGroups(self):
        groups = []
        captureIndex = 0
        for phaseType in SpectralWorkflowPhaseType:
            phase = self.__workflow.getPhase(phaseType)
            if phase is None:
                continue
            items = []
            for step in phase.getSteps().values():
                for item in self.__stepItems(step):
                    if not getattr(item, "isShownInReport", False):
                        continue
                    if isinstance(item, SpectrumCaptureView):
                        captureIndex += 1
                        self.__prepareCapture(item, step, captureIndex)
                    items.append(item)
            if items:
                groups.append((self.__PHASE_LABELS.get(phaseType, str(phaseType)), items))
        return groups

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
        if not capture.attachmentName:
            role = step.getRole() if hasattr(step, "getRole") else None
            slug = (role or ("capture_%d" % index))
            capture.attachmentName = "capture_%s.png" % _slug(slug) if role else "capture_%d.png" % index
        pil = capture.reportImage
        if pil is None:
            return
        buffer = io.BytesIO()
        pil.convert("RGB").save(buffer, format="PNG")
        self.__captures.append((capture.attachmentName, buffer.getvalue()))

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
            payload = json.dumps(self.__workflow.toReportJson(), indent=2).encode("utf-8")
            writer.add_attachment("workflow.json", payload)
        for name, pngBytes in self.__captures:
            writer.add_attachment(name, pngBytes)
        with open(targetPath, "wb") as target:
            writer.write(target)


def _slug(text):
    return "".join(character if character.isalnum() else "_" for character in str(text)).strip("_").lower()
