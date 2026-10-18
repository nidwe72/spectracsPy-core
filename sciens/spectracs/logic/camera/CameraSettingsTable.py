from sciens.spectracs.logic.camera.CameraSettingsResolver import WRITE_ORDER
from sciens.spectracs.model.spectral.plugin.view.CameraSettingsRecordView import CameraSettingsRecordView
from sciens.spectracs.model.spectral.plugin.view.TableView import TableView
from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl

C = CameraControl
TITLE = "Camera settings"


def cameraRecordsOf(steps):
    """The `CameraSettingsRecordView` of each step that has one, in step order — harvested by TYPE (§7)."""
    records = []
    for step in steps or []:
        result = step.getEvaluationResult() if hasattr(step, "getEvaluationResult") else None
        for item in (result.getItems() if result is not None else []):
            if isinstance(item, CameraSettingsRecordView):
                records.append(item)
    return records


def cameraSettingsTable(records):
    """The camera state of a measurement as ONE TableView — SPEC_camera_settings.md §7 (E9).

    ⭐ ONE BUILDER, THREE CONSUMERS: the PDF (the report builder appends it after ACQUISITION), the live "Camera"
    inner tab and the Camera sub-tab of a re-opened run. Qt-free and plugin-free, so a LIMS addon rebuilding a
    report from JSON gets the same table.

    `records` are the legs' `CameraSettingsRecordView`s in leg order (reference, sample). One `applied` column while
    every leg agrees with itself and with the others; on ANY difference `applied` splits into one column per leg and
    the row is marked `⛔ ref ≠ sample` — the PDF has no per-row colour, so the mark is text (§7).
    """
    records = [record for record in (records or []) if record is not None]
    if not records:
        return None
    table = TableView(title=TITLE)
    table.setShownInReport(True)
    virtual = next((record.openRecord.virtual for record in records if record.openRecord.virtual), None)
    if virtual:
        table.addColumn("control", "", align="left")
        table.addRow({"control": virtual})
        return table

    opening = records[0].openRecord
    legs = [record.leg for record in records]
    controls = _controlsOf(records)
    split = any(_legValues(legs, control)[1] for control in controls)
    # The heading above the table says "Camera settings" (the PDF group, the tab label); the title names the camera.
    table.title = "%s%s" % (_identity(opening), "    ⛔ reference ≠ sample" if split
                            else ("    reference = sample ✓" if len(legs) > 1 else ""))

    table.addColumn("control", "control", align="left")
    table.addColumn("device", "device default")
    table.addColumn("requested", "requested")
    if split:
        for leg in legs:
            table.addColumn("leg:%s" % leg.role, str(leg.role).lower())
        table.addColumn("check", "", align="left")
    else:
        table.addColumn("applied", "applied")
    table.addColumn("source", "source", align="left")

    for control in controls:
        values, differs = _legValues(legs, control)
        row = {"control": control.label(),
               "device": _format(control, opening.deviceDefaults.get(control.value)),
               "requested": _requested(opening, control, legs),
               "source": _source(opening, control, legs)}
        if split:
            for leg, value in zip(legs, values):
                row["leg:%s" % leg.role] = value
            row["check"] = "⛔ ref ≠ sample" if differs else ""
        else:
            row["applied"] = _applied(control, values[0], legs[0])
        if control.value in (opening.autoLoopsOn or []):
            row["source"] = "%s  ⛔ auto loop on" % row["source"]
        table.addRow(row)
    table.caption = _caption(records)
    return table


def _controlsOf(records):
    seen = set()
    for record in records:
        seen.update(record.openRecord.requested or {})
        seen.update(record.openRecord.deviceDefaults or {})
        seen.update(record.leg.atStart or {})
    return [control for control in WRITE_ORDER if control.value in seen]


def _legValues(legs, control):
    """([cell per leg], differs) — a cell reads `start → end` when the value drifted within the leg."""
    cells, starts = [], []
    differs = False
    for leg in legs:
        start = (leg.atStart or {}).get(control.value)
        end = (leg.atEnd or {}).get(control.value, start)
        starts.append(start)
        if end != start:
            differs = True
            cells.append("%s → %s" % (_format(control, start), _format(control, end)))
        else:
            cells.append(_format(control, start))
    if len(set(repr(value) for value in starts)) > 1:
        differs = True
    return cells, differs


def _requested(opening, control, legs):
    if control.value in (opening.inactive or []):
        return "— (inactive)"
    if control is C.EXPOSURE:
        requested = {leg.requestedExposure for leg in legs if leg.requestedExposure is not None}
        if requested:
            return " / ".join(_format(control, value) for value in sorted(requested))
    return _format(control, (opening.requested or {}).get(control.value))


def _applied(control, cell, leg):
    native = ((leg.exposureNative or {}).get("start") or {}) if control is C.EXPOSURE else {}
    if native.get("unit") == "log2_s" and native.get("value") is not None:
        return "%s → applied %s (%.1f ms, nearest whole log₂ step)" % (
            leg.requestedExposure, native["value"], 1000.0 * 2 ** float(native["value"]))
    return cell


def _source(opening, control, legs):
    if control is C.EXPOSURE:
        sources = []
        for leg in legs:
            if leg.exposureSource and leg.exposureSource not in sources:
                sources.append(leg.exposureSource)
        if sources:
            return " / ".join(sources)
    return (opening.sources or {}).get(control.value, "—")


def _format(control, value):
    if value is None:
        return ""
    if control is C.EXPOSURE:
        try:
            return "%d (%.1f ms)" % (int(value), int(value) / 10.0)
        except (TypeError, ValueError):
            return str(value)
    if control is C.WHITE_BALANCE_KELVIN:
        return "%s K" % value
    if control is C.AUTO_EXPOSURE:
        return str(value).lower()
    if control is C.POWER_LINE_FREQUENCY:
        return "%s Hz" % value if str(value) in ("50", "60") else str(value).lower()
    if isinstance(value, bool):
        return "on" if value else "off"
    if control is C.BACKLIGHT:
        return "%s (%s)" % (value, "off" if value == 0 else "on")
    return str(value)


def _identity(opening):
    camera, host = opening.camera or {}, opening.host or {}
    ids = ":".join(part for part in (camera.get("vendorId"), camera.get("modelId")) if part)
    conversion = {"own": "own conversion", "backend": "backend conversion"}.get(host.get("conversion"), "")
    parts = [" ".join(part for part in (camera.get("name"), ids) if part),
             " ".join(part for part in (host.get("os"), host.get("backend")) if part),
             ", ".join(part for part in (host.get("pixelFormat"), conversion) if part)]
    return " · ".join(part for part in parts if part) or "camera"


def _caption(records):
    opening = records[0].openRecord
    lines = ["%s profile · held back %d frames after open · skipped: %s"
             % (opening.profile or "?", opening.heldBackFrames or 0, ", ".join(opening.skipped or []) or "—")]
    for record in records:
        if record.leg.heldBackFrames:
            lines.append("%s: held back %d frames after the last change" % (record.getRole(), record.leg.heldBackFrames))
    for note in list((opening.adjusted or {}).values()) + list(opening.rejected or []):
        lines.append("⚠ %s" % note)
    if opening.autoLoopsOn:
        lines.append("⛔ auto loop on — not a frozen instrument state: %s" % ", ".join(opening.autoLoopsOn))
    for entry in opening.mismatches or []:
        lines.append("⛔ at open: %(control)s requested %(requested)s, applied %(applied)s" % entry)
    if opening.refusal:
        lines.append("⛔ refused: %s" % opening.refusal)
    for note in opening.notes or []:
        lines.append(note)
    return "\n".join(lines)
