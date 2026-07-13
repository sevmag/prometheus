"""Tests for the WATER/PPC routing branch of ``config_mims`` (Task 5).

The WATER branch of :func:`prometheus.utils.config_mims.config_mims` must only
default the photon propagator to ``olympus`` when *no* propagator has been set
explicitly. An explicit ``PPC``/``PPC_CUDA`` choice on a water detector must be
honoured (no ``olympus`` override), while ICE behaviour (unset -> ``PPC``) is
unchanged.

``config_mims`` does considerably more than the medium branch: it also calls
``injection_config_mims``, ``lepton_prop_config_mims``,
``photon_prop_config_mims`` and ``check_consistency``. Those module-level
helpers are monkeypatched to no-ops so these tests exercise only the
medium-routing logic with minimal ``SimpleNamespace`` stand-ins.
"""

import importlib
import tempfile
from types import SimpleNamespace

from prometheus.detector.medium import Medium

# ``prometheus.utils.__init__`` re-exports the ``config_mims`` *function*, which
# shadows the submodule of the same name. Grab the module object explicitly so
# ``monkeypatch.setattr`` patches the module globals the function looks up.
config_mims_module = importlib.import_module("prometheus.utils.config_mims")
config_mims = config_mims_module.config_mims

_DOWNSTREAM_HELPERS = (
    "injection_config_mims",
    "lepton_prop_config_mims",
    "photon_prop_config_mims",
    "check_consistency",
)


class _Indexable(SimpleNamespace):
    """SimpleNamespace that also supports ``obj[key]`` subscription.

    ``config_mims`` reads e.g. ``config.injection[config.injection.name]`` and
    ``config.lepton_propagator[config.lepton_propagator.name]``.
    """

    def __getitem__(self, key):
        return getattr(self, key)


def _make_config(pp_name, storage_prefix):
    """Minimal stand-in config exposing exactly what ``config_mims`` reads."""
    return SimpleNamespace(
        photon_propagator=SimpleNamespace(name=pp_name),
        run=SimpleNamespace(
            random_state_seed=1,
            run_number=1,
            storage_prefix=storage_prefix,
            outfile="out.parquet",
            nevents=1,
        ),
        # geo_file kept in EARTH_MODEL_DICT so the earth-model lookup succeeds.
        detector=SimpleNamespace(geo_file="icecube.geo", offset=None),
        injection=_Indexable(name="ranged", ranged=SimpleNamespace()),
        lepton_propagator=_Indexable(name="new", new=SimpleNamespace()),
    )


def _make_detector(medium):
    """Minimal stand-in detector: real ``Medium`` enum + a 3-vector offset."""
    return SimpleNamespace(medium=medium, _offset=[0.0, 0.0, 0.0])


def _resolve_name(pp_name, medium, storage_prefix, setattr_fn):
    """No-op the downstream helpers, call ``config_mims``, return the name set."""
    for helper in _DOWNSTREAM_HELPERS:
        setattr_fn(config_mims_module, helper, lambda *a, **k: None)
    config = _make_config(pp_name, storage_prefix)
    detector = _make_detector(medium)
    config_mims(config, detector)
    return config.photon_propagator.name


# --------------------------------------------------------------------------- #
# pytest entry points
# --------------------------------------------------------------------------- #
def test_water_explicit_ppc_cuda_is_kept(tmp_path, monkeypatch):
    """WATER + explicit PPC_CUDA must be preserved (no olympus override)."""
    name = _resolve_name("PPC_CUDA", Medium.WATER, str(tmp_path), monkeypatch.setattr)
    assert name == "PPC_CUDA"


def test_water_unset_defaults_to_olympus(tmp_path, monkeypatch):
    """WATER + unset (None) must still default to olympus (back-compat)."""
    name = _resolve_name(None, Medium.WATER, str(tmp_path), monkeypatch.setattr)
    assert name == "olympus"


def test_ice_unset_defaults_to_ppc(tmp_path, monkeypatch):
    """ICE + unset (None) must still default to PPC (unchanged)."""
    name = _resolve_name(None, Medium.ICE, str(tmp_path), monkeypatch.setattr)
    assert name == "PPC"


# --------------------------------------------------------------------------- #
# Fallback runner: `python3 tests/test_config_mims_water_ppc.py` (no pytest)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":

    def _plain_setattr(obj, name, value):
        setattr(obj, name, value)

    cases = (
        ("PPC_CUDA", Medium.WATER, "PPC_CUDA"),
        (None, Medium.WATER, "olympus"),
        (None, Medium.ICE, "PPC"),
    )
    for pp, med, expected in cases:
        with tempfile.TemporaryDirectory() as td:
            got = _resolve_name(pp, med, td, _plain_setattr)
        assert got == expected, f"{med.name} + {pp!r}: expected {expected!r}, got {got!r}"
    print("OK: all 3 config_mims water/PPC routing checks passed")
