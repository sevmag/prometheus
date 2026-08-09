"""Tests for the detector-vs-earth-model consistency check."""

import copy
import pathlib

import pytest

from prometheus.config import config as DEFAULT_CONFIG
from prometheus.detector.detector_factory import detector_from_geo
from prometheus.utils.config_mims import config_mims
from prometheus.utils.earth_consistency import (
    EarthLayer,
    check_detector_earth_consistency,
    parse_earth_layers,
)

REPO_ROOT = pathlib.Path(__file__).parent.parent.resolve()
GEO_DIR = REPO_ROOT / "resources" / "geofiles"
DENSITY_DIR = REPO_ROOT / "resources" / "earthparams" / "densities"

# Rock up to 6371324 m, a single 2000 m water column, then atmosphere —
# the same shell structure as the shipped PREM_water.dat.
WATER_EARTH_BODY = """\
# comment line
   # indented comment, must be skipped

6356000 inner_crust ROCK 1 2.900
6371324 rockice_boundary ROCK 1 2.650 # inline comment
6373324 sea WATER 1 1.0
6478000 atmo_radius AIR 1 0.000811
"""

# Two stacked ICE shells (clear ice + firn) like PREM_south_pole.dat.
ICE_EARTH_BODY = """\
6371324 rockice_boundary ROCK 1 2.650
6373934 clearice_boundary ICE 1 0.921585
6374134 iceair_boundary ICE 1 0.762944
6478000 atmo_radius AIR 1 0.000811
"""


def _write_earth(tmp_path, body):
    path = tmp_path / "earth.dat"
    path.write_text(body)
    return path


def _detector_at(tmp_path, medium, z_values):
    """Build a single-string detector with modules at the given depths."""
    lines = ["### Metadata ###", f"Medium:\t{medium}", "DOM Radius [cm]:\t30", "### Modules ###"]
    lines += [f"0.0\t0.0\t{z}\t0\t{i}" for i, z in enumerate(z_values)]
    geo = tmp_path / "det.geo"
    geo.write_text("\n".join(lines) + "\n")
    return detector_from_geo(str(geo))


# ---------------------------------------------------------------------------
# Shipped detector / earth model combinations
# ---------------------------------------------------------------------------


class TestShippedCombinations:
    """The geo/earth pairings resolved by config_mims pass the check."""

    @pytest.mark.parametrize(
        "geo, earth",
        [
            ("icecube.geo", "PREM_south_pole.dat"),
            ("icecube_gen2.geo", "PREM_south_pole.dat"),
            ("deepcore.geo", "PREM_south_pole.dat"),
            ("upgrade.geo", "PREM_south_pole.dat"),
            ("arca.geo", "PREM_arca.dat"),
            ("gvd.geo", "PREM_gvd.dat"),
        ],
    )
    def test_matching_combination_passes(self, geo, earth):
        detector = detector_from_geo(str(GEO_DIR / geo))
        check_detector_earth_consistency(detector, DENSITY_DIR / earth)

    def test_arca_under_generic_water_model_raises(self):
        """ARCA at 3500 m depth is inside the ROCK shell of the 2000 m generic model."""
        detector = detector_from_geo(str(GEO_DIR / "arca.geo"))
        with pytest.raises(ValueError) as excinfo:
            check_detector_earth_consistency(detector, DENSITY_DIR / "PREM_water.dat")
        message = str(excinfo.value)
        assert "ROCK" in message
        assert "-3500" in message
        assert "PREM_water.dat" in message
        assert "earth_model_location" in message

    def test_ice_detector_against_water_model_raises(self):
        detector = detector_from_geo(str(GEO_DIR / "icecube.geo"))
        with pytest.raises(ValueError) as excinfo:
            check_detector_earth_consistency(detector, DENSITY_DIR / "PREM_arca.dat")
        message = str(excinfo.value)
        assert "ICE" in message
        assert "WATER" in message
        assert "PREM_arca.dat" in message


# ---------------------------------------------------------------------------
# Boundary criterion
# ---------------------------------------------------------------------------


class TestBoundaryCriterion:
    """Modules must lie inside the contiguous medium-matching shell stack."""

    def test_module_exactly_on_seabed_passes(self, tmp_path):
        earth = _write_earth(tmp_path, WATER_EARTH_BODY)
        detector = _detector_at(tmp_path, "water", [-2000.0, -1000.0, 0.0])
        check_detector_earth_consistency(detector, earth)

    def test_module_below_seabed_raises(self, tmp_path):
        earth = _write_earth(tmp_path, WATER_EARTH_BODY)
        detector = _detector_at(tmp_path, "water", [-2000.5, -1000.0])
        with pytest.raises(ValueError, match="ROCK"):
            check_detector_earth_consistency(detector, earth)

    def test_module_above_surface_raises(self, tmp_path):
        earth = _write_earth(tmp_path, WATER_EARTH_BODY)
        detector = _detector_at(tmp_path, "water", [-1000.0, 10.0])
        with pytest.raises(ValueError, match="AIR"):
            check_detector_earth_consistency(detector, earth)

    def test_detector_spanning_stacked_ice_shells_passes(self, tmp_path):
        earth = _write_earth(tmp_path, ICE_EARTH_BODY)
        detector = _detector_at(tmp_path, "ice", [-2810.0, -100.0])
        check_detector_earth_consistency(detector, earth)

    def test_ice_detector_below_stacked_ice_shells_raises(self, tmp_path):
        earth = _write_earth(tmp_path, ICE_EARTH_BODY)
        detector = _detector_at(tmp_path, "ice", [-2810.5])
        with pytest.raises(ValueError, match="ROCK"):
            check_detector_earth_consistency(detector, earth)

    def test_unset_medium_raises(self, tmp_path):
        earth = _write_earth(tmp_path, WATER_EARTH_BODY)
        detector = _detector_at(tmp_path, "water", [-1000.0])
        detector._medium = None
        with pytest.raises(ValueError, match="medium"):
            check_detector_earth_consistency(detector, earth)


# ---------------------------------------------------------------------------
# Earth file parser
# ---------------------------------------------------------------------------


class TestParseEarthLayers:
    """The boundary parser reads the earth file format and rejects bad input."""

    def test_layers_comments_and_boundaries(self, tmp_path):
        layers = parse_earth_layers(_write_earth(tmp_path, WATER_EARTH_BODY))

        assert layers == [
            EarthLayer(0.0, 6356000.0, "inner_crust", "ROCK"),
            EarthLayer(6356000.0, 6371324.0, "rockice_boundary", "ROCK"),
            EarthLayer(6371324.0, 6373324.0, "sea", "WATER"),
            EarthLayer(6373324.0, 6478000.0, "atmo_radius", "AIR"),
        ]

    def test_non_ascending_radii_raise(self, tmp_path):
        body = "6371324 rock ROCK 1 2.650\n6371324 sea WATER 1 1.0\n"
        with pytest.raises(ValueError, match="ascending"):
            parse_earth_layers(_write_earth(tmp_path, body))

    def test_short_line_raises(self, tmp_path):
        with pytest.raises(ValueError, match="expected"):
            parse_earth_layers(_write_earth(tmp_path, "6371324 rock\n"))

    def test_invalid_radius_raises(self, tmp_path):
        with pytest.raises(ValueError, match="invalid outer radius"):
            parse_earth_layers(_write_earth(tmp_path, "radius rock ROCK 1 2.650\n"))

    def test_comment_only_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="no layer"):
            parse_earth_layers(_write_earth(tmp_path, "# nothing here\n\n"))


# ---------------------------------------------------------------------------
# config_mims wiring
# ---------------------------------------------------------------------------


class TestConfigMimsWiring:
    """config_mims runs the check on the resolved earth model paths."""

    def _config(self, tmp_path):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.run.storage_prefix = str(tmp_path / "output") + "/"
        cfg.detector.geo_file = str(GEO_DIR / "arca.geo")
        return cfg

    def test_default_resolution_passes(self, tmp_path):
        detector = detector_from_geo(str(GEO_DIR / "arca.geo"))
        config_mims(self._config(tmp_path), detector)

    def test_user_earth_model_override_is_validated(self, tmp_path):
        cfg = self._config(tmp_path)
        lp_paths = cfg.lepton_propagator[cfg.lepton_propagator.name].paths
        lp_paths.earth_model_location = str(DENSITY_DIR / "PREM_water.dat")
        detector = detector_from_geo(str(GEO_DIR / "arca.geo"))
        with pytest.raises(ValueError, match="ROCK"):
            config_mims(cfg, detector)

    def test_escape_hatch_disables_check(self, tmp_path):
        cfg = self._config(tmp_path)
        lp_paths = cfg.lepton_propagator[cfg.lepton_propagator.name].paths
        lp_paths.earth_model_location = str(DENSITY_DIR / "PREM_water.dat")
        cfg.detector.check_earth_consistency = False
        detector = detector_from_geo(str(GEO_DIR / "arca.geo"))
        config_mims(cfg, detector)
