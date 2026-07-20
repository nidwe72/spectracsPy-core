import copy
import json
import os
from datetime import datetime

import numpy

from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters


def _num(value):
    # JSON has no NaN — map NaN/None to null so the file is valid and replayable.
    if value is None:
        return None
    value = float(value)
    return None if numpy.isnan(value) else value


class CaptureDiagnosticsLogger:
    # Env-gated per-capture diagnostic log (SPEC_capability_proof.md §7.0.1 — the reference gray-outlier / jitter
    # investigation). When SPECTRACS_LOG_SPECTRA=<dir> is set, each capture writes ONE JSON with every captured
    # frame's spectrum, the C1 dim-frame rejection KEEP-mask + per-frame brightness (which frames were skipped and
    # HOW dim), and the robust reduced mean. Off by default (no env → no file, no cost). Qt-free + import-light so
    # the headless engine and the diagnosis script log identically.
    ENV_DIR = "SPECTRACS_LOG_SPECTRA"

    def isEnabled(self):
        return bool(os.environ.get(self.ENV_DIR))

    def log(self, role, spectrum, extra=None):
        if not self.isEnabled() or spectrum is None:
            return None
        frames = spectrum.getCapturedValuesByNanometers() or []
        if not frames:
            return None

        keys = list(frames[0].keys())
        stack = numpy.array([[frame.get(key, numpy.nan) for key in keys] for frame in frames], dtype=float)
        kept = RobustReductionLogicModule().rejectDimFrames(stack)      # 1-D bool over frames (True = kept)
        brightness = numpy.nanmean(stack, axis=1)

        directory = os.environ.get(self.ENV_DIR)
        os.makedirs(directory, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(directory, "%s_%s.json" % (stamp, role))

        record = {
            "role": role,
            "timestamp": stamp,
            "frameCount": len(frames),
            "rejectedCount": int(numpy.sum(~kept)),
            "keysNm": [float(key) for key in keys],
            "frames": [[_num(value) for value in row] for row in stack.tolist()],
            "kept": [bool(flag) for flag in kept.tolist()],
            "frameBrightness": [_num(value) for value in brightness.tolist()],
            "reducedMean": self.__reducedMean(spectrum),
        }
        if extra:
            record["extra"] = extra
        with open(path, "w") as handle:
            json.dump(record, handle)

        print("CAPTURE-SPECTRA role=%s frames=%d rejected=%d brightness=[%.1f..%.1f] -> %s"
              % (role, len(frames), record["rejectedCount"],
                 float(numpy.nanmin(brightness)), float(numpy.nanmax(brightness)), path))
        return path

    def __reducedMean(self, spectrum):
        # The mean AS THE PIPELINE reduces it (robust reject + sigma-clip), computed on a throwaway copy so the
        # caller's captured frames are untouched.
        clone = copy.deepcopy(spectrum)
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(clone)
        reduced = MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()
        return {str(key): _num(value) for key, value in reduced.valuesByNanometers.items()}
