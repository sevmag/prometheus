"""Tests for PPC nextgen QE-file staging + NEXTGENDIR env (Task 6).

These tests mock ``subprocess.Popen`` so they do not require the PPC binary.
They verify that a ``needs_nextgen()`` detector causes
``om.conf``/``om.map``/``om.dirs``/``om.wv_*``/``eff-f2k`` to be staged into the
PPC tmpdir, that ``NEXTGENDIR`` (and ``PPCTABLESDIR``) are exported to the
subprocess environment pointing at that tmpdir, and that a legacy detector
stages none of the nextgen input files.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from prometheus.detector.detector import Detector
from prometheus.detector.medium import Medium
from prometheus.detector.module import Module
from prometheus.photon_propagation.ppc_photon_propagator import ppc_sim


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _nextgen_det(n=3):
    """A multi-PMT nextgen detector (module_type != -1, 31 PMTs each)."""
    mods = [
        Module(
            pos=np.array([0.0, 0.0, float(i) * 17.0]),
            key=(1, i + 1),  # PPC isinice() requires dom >= 1
            module_type=1,
            n_pmts=31,
            pmt_dirs=[(180.0, 0.0)] * 31,
        )
        for i in range(n)
    ]
    return Detector(mods, Medium.ICE)


def _legacy_det(n=3):
    """A legacy detector (all modules module_type == -1)."""
    mods = [
        Module(pos=np.array([0.0, 0.0, float(i) * 17.0]), key=(1, i + 1))
        for i in range(n)
    ]
    return Detector(mods, Medium.ICE)


def _make_config(ppc_tmpdir, ppctables):
    """Minimal ppc_config with *distinct* tmpdir and ppctables dirs.

    They must differ so that copying ``om.wv_*``/``eff-f2k`` from ``ppctables``
    into ``ppc_tmpdir`` is never a same-file copy.
    """
    return {
        "paths": {
            "ppc_tmpdir": str(ppc_tmpdir),
            "ppc_tmpfile": "hits.tmp",
            "f2k_tmpfile": "losses.f2k",
            "ppctables": str(ppctables),
            "ppc_exe": "/nonexistent/ppc",
            "om_dirs": "",
        },
        "simulation": {
            "device": 0,
            "supress_output": True,
        },
    }


def _dummy_particle():
    """A particle-like object that lands a point-deposition loss in-detector."""

    class _FakeParticle:
        e = 100.0
        position = np.zeros(3)
        direction = np.array([0.0, 0.0, 1.0])
        children = []
        losses = []
        hits = []

        def __int__(self):
            return 211  # charged pion -> point deposition branch

        def __abs__(self):
            return 211

        def __str__(self):
            return "PiPlus"

    return _FakeParticle()


class _CapturePopen:
    """Popen stub: writes an empty hit file and records the subprocess env."""

    def __init__(self):
        self.env = {}

    def __call__(self, cmd, shell=None, stdout=None, stderr=None, env=None, **kwargs):
        self.env.clear()
        self.env.update(env or {})
        # Command form: "ppc N < input > output"
        output_path = cmd.split("2>")[0].split(">")[-1].strip().split()[0]
        open(output_path, "w").close()
        mock = MagicMock()
        mock.returncode = 0
        mock.communicate = lambda: (b"", b"")
        return mock


def _run(det, cfg, popen):
    """Drive ppc_sim with the PPC binary + serializers mocked out."""
    particle = _dummy_particle()
    with patch(
        "prometheus.photon_propagation.ppc_photon_propagator.subprocess.Popen", popen
    ):
        with patch(
            "prometheus.photon_propagation.ppc_photon_propagator.serialize_to_f2k"
        ):
            with patch.object(det, "to_f2k"):
                try:
                    ppc_sim(particle, det, None, cfg)
                except Exception:
                    # geo/f2k tmpfiles are never written (serializers mocked),
                    # so the final os.remove cleanup may raise; irrelevant here.
                    pass


@pytest.fixture
def dirs(tmp_path):
    """Create distinct ppctables (with dummy inputs) and ppc_tmpdir."""
    ppctables = tmp_path / "ppctables"
    ppctables.mkdir()
    (ppctables / "om.dirs").write_text("1 0.0 0.0 1.0\n")
    (ppctables / "om.wv_1.0").write_text("dummy wv\n")
    (ppctables / "eff-f2k").write_text("dummy eff\n")
    ppc_tmpdir = tmp_path / "ppc_tmp"
    ppc_tmpdir.mkdir()
    return ppc_tmpdir, ppctables


# ---------------------------------------------------------------------------
# Nextgen staging
# ---------------------------------------------------------------------------


class TestNextgenStaging:
    def test_all_five_files_staged(self, dirs):
        ppc_tmpdir, ppctables = dirs
        det = _nextgen_det()
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        for name in ("om.conf", "om.map", "om.dirs", "om.wv_1.0", "eff-f2k"):
            assert (ppc_tmpdir / name).exists(), f"{name} was not staged"

    def test_km3net_as_staged(self, dirs):
        ppc_tmpdir, ppctables = dirs
        (ppctables / "km3net_as.dat").write_text("-1.00 1.0000\n0.25 0.0000\n")
        det = _nextgen_det()
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        assert (ppc_tmpdir / "km3net_as.dat").exists(), "km3net_as.dat was not staged"

    def test_om_wv_content_copied(self, dirs):
        ppc_tmpdir, ppctables = dirs
        det = _nextgen_det()
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        assert (ppc_tmpdir / "om.wv_1.0").read_text() == "dummy wv\n"

    def test_multiple_om_wv_globbed(self, dirs):
        ppc_tmpdir, ppctables = dirs
        (ppctables / "om.wv_2.0").write_text("wv2\n")
        det = _nextgen_det()
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        assert (ppc_tmpdir / "om.wv_1.0").exists()
        assert (ppc_tmpdir / "om.wv_2.0").exists()

    def test_nextgendir_env_set(self, dirs):
        ppc_tmpdir, ppctables = dirs
        det = _nextgen_det()
        popen = _CapturePopen()
        _run(det, _make_config(ppc_tmpdir, ppctables), popen)
        assert popen.env.get("NEXTGENDIR") == str(ppc_tmpdir)

    def test_ppctablesdir_env_still_set(self, dirs):
        ppc_tmpdir, ppctables = dirs
        det = _nextgen_det()
        popen = _CapturePopen()
        _run(det, _make_config(ppc_tmpdir, ppctables), popen)
        assert popen.env.get("PPCTABLESDIR") == str(ppc_tmpdir)

    def test_missing_wv_and_eff_no_error(self, dirs):
        ppc_tmpdir, ppctables = dirs
        (ppctables / "om.wv_1.0").unlink()
        (ppctables / "eff-f2k").unlink()
        det = _nextgen_det()
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        # Remaining nextgen files still staged; absent optionals are skipped.
        assert (ppc_tmpdir / "om.conf").exists()
        assert (ppc_tmpdir / "om.map").exists()
        assert (ppc_tmpdir / "om.dirs").exists()
        assert not (ppc_tmpdir / "om.wv_1.0").exists()
        assert not (ppc_tmpdir / "eff-f2k").exists()


# ---------------------------------------------------------------------------
# Legacy path unchanged
# ---------------------------------------------------------------------------


class TestLegacyPathUnchanged:
    def test_legacy_stages_no_nextgen_files(self, dirs):
        ppc_tmpdir, ppctables = dirs
        det = _legacy_det()
        assert det.needs_nextgen() is False
        _run(det, _make_config(ppc_tmpdir, ppctables), _CapturePopen())
        for name in ("om.conf", "om.map", "om.dirs", "om.wv_1.0", "eff-f2k"):
            assert not (
                ppc_tmpdir / name
            ).exists(), f"{name} must not be staged for a legacy detector"
