# spectracsPy-core

**The Qt-free shared tier.** The spectral science, the `plugin_sdk` façade, and the workflow render seam —
everything the app, the plugins and a future LIMS addon all consume, and that none of them should have to drag a
GUI in to use.

Extracted from `spectracsPy` on 2026-07-17. Design + rationale:
[`spectracsPy/docs/SPEC_project_structure.md`](../spectracsPy/docs/SPEC_project_structure.md) (phase S3b).

## What's in here

```
sciens/spectracs/plugin_sdk/                 the facade — THE published contract (M3)
sciens/spectracs/logic/spectral/
    absorption/ transmission/ meanSpectrum/  the science
    spectrumToColor/ verdict/ feature/
    smoothSpectrum/ removeBaseline/          the conditioning chain
    rebinSpectrum/ normalizeSpectrum/
    spectralLine/                            peak selection
    synthesis/                               LED-reference + oil-sample synthesis
    util/SpectrumUtil.py                     the conditioning-chain facade
    util/SpectralColorUtil.py                colour maths
    util/SpectralWorkflowUtil.py             workflow phase/step helpers
    acquisition/RobustReductionLogicModule   Tukey biweight / sigma-clipped mean
    acquisition/ExtendedRoiLogicModule       ROI clamp (the PLUGIN declares the ROI)
    report/                                  the M1 visitor seam + M2's matplotlib renderer/builder
```

## The rule

**Qt-free, for real.** This must return nothing:

```bash
grep -rE 'PySide6|pyqtgraph|shiboken' sciens/
```

Nothing here may import the app (`view/`, `controller/`, `session/`, `server/`, `persistence/`). Allowed: `numpy`,
`scipy`, `colour-science`, `rgbxy`, `spectres`, `matplotlib`, `Pillow`, `pypdf`, plus `spectracsPy-model` and
`spectracsPy-base`.

The seam is a claim to **verify, not assume** — S3a's re-derivation caught a file the design doc had wrong
(`SpectrallineUtil`, DB-bound via master data). Re-derive by grep before trusting any list.

**`plugin_sdk` is the contract; the rest is not.** A class in here that the façade does not export is invisible to
plugins and cheap to reshape. An exported one is frozen the moment a plugin imports it.

## Layout

Repos are **namespace-merged**, not pip-installed — every one contributes to the `sciens.*` tree via PEP 420
(hence no `__init__.py` outside `plugin_sdk/`). Three directories are deliberately split across this repo and
`spectracsPy`: `logic/spectral/{util,acquisition,synthesis}`. `ls` therefore shows you half a package; that is
expected.

    spectracsPy-base  <-  spectracsPy-model  <-  spectracsPy-core  <-  spectracsPy (app)
                                                                   <-  spectracs-plugins  (planned, S5)
                                                                   <-  senaite-spectracs  (future)

## Running

No venv, no requirements, no test suite of its own — deliberately. **Tests live in `spectracsPy/tests/`**, which is
this project's convention for every tier (`-model` owns `Spectrum`, `SpectralWorkflow` and every view-model, and
has zero tests of its own). Run them from the app repo:

```bash
cd ../spectracsPy
PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
    QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/ -q
```

The Android APK assembles the tiers with `spectracsPy/android/spike/stage_app_src.sh`, which rsyncs each repo's
`sciens/` into one merged tree.

## Reading the history

History was carried over with `git filter-repo`, so `git log --follow` and `git blame` work back to 2026 —
including through S1b's colour port.

**But the commit messages are app-centric**, because they were written in `spectracsPy` for changes that mostly
landed elsewhere. `S3b phase 0: re-home the render trio ... and teach every path -core` is in this log, yet the
PYTHONPATH sweep it describes isn't in this repo at all. Read messages as *"what was happening in the project when
this file changed"*, not *"what this commit did here"*. For the full narrative, see `spectracsPy`.
