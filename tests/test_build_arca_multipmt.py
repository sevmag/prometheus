"""Tests for the ARCA multi-PMT detector builder (Task 7).

The builder lives in ``examples/build_arca_multipmt.py``. ``examples`` is not an
importable package (no ``__init__.py``), so we load the module directly from its
file path via importlib, mirroring how the rest of the suite avoids depending on
``examples`` being on ``sys.path``.
"""

import importlib.util
import os

import pytest

from prometheus.detector.detector import Detector

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUILDER_PATH = os.path.join(_HERE, "..", "examples", "build_arca_multipmt.py")


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_arca_multipmt", _BUILDER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


@pytest.fixture(scope="module")
def detector(builder):
    return builder.build_arca_multipmt_detector()


class TestPmtDirLoading:
    def test_loads_31_dirs(self, builder):
        assert len(builder._load_pmt_dirs()) == 31

    def test_dirs_are_zen_az_pairs(self, builder):
        for zen, az in builder._load_pmt_dirs():
            assert 0.0 <= zen <= 180.0
            assert 0.0 <= az <= 360.0


class TestDetectorStructure:
    def test_is_detector(self, detector):
        assert isinstance(detector, Detector)

    def test_has_2070_modules(self, detector):
        assert len(detector.modules) == 2070

    def test_every_module_has_31_pmts(self, detector):
        assert all(m.n_pmts == 31 for m in detector.modules)

    def test_every_module_has_31_pmt_dirs(self, detector):
        assert all(len(m.pmt_dirs) == 31 for m in detector.modules)

    def test_module_type_is_1(self, detector):
        assert all(m.module_type == 1 for m in detector.modules)

    def test_rr_is_2159(self, detector):
        assert all(m.Rr == pytest.approx(0.2159) for m in detector.modules)

    def test_rz_is_2159(self, detector):
        assert all(m.Rz == pytest.approx(0.2159) for m in detector.modules)

    def test_rr_equals_rz(self, detector):
        assert all(m.Rr == m.Rz for m in detector.modules)

    def test_needs_nextgen_true(self, detector):
        assert detector.needs_nextgen() is True


class TestKeysMatchGeo:
    def test_keys_match_geofile_in_order(self, builder, detector):
        lines = open(builder.GEO).readlines()
        start = lines.index("### Modules ###\n") + 1
        expected = []
        for ln in lines[start:]:
            c = ln.strip("\n").split("\t")
            if len(c) < 5:
                continue
            expected.append((int(c[3]), int(c[4])))
        assert [m.key for m in detector.modules] == expected

    def test_keys_are_unique(self, detector):
        keys = [m.key for m in detector.modules]
        assert len(set(keys)) == len(keys)


class TestOmConfAndMap:
    def test_om_conf_one_type_block_with_31_dirs(self, detector, tmp_path):
        path = str(tmp_path / "om.conf")
        detector.to_om_conf(path)
        header_types = 0
        pmt_dir_lines = 0
        with open(path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                if not line[0].isspace():
                    header_types += 1
                pmt_dir_lines += 1
        assert header_types == 1
        assert pmt_dir_lines == 31

    def test_om_map_has_2070_rows(self, detector, tmp_path):
        path = str(tmp_path / "om.map")
        detector.to_om_map(path)
        with open(path) as f:
            rows = [ln for ln in f if ln.strip()]
        assert len(rows) == 2070
