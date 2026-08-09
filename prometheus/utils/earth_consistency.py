"""Consistency check between a detector geometry and an earth model file.

Geometry, medium, and earth model are sourced independently and nothing else
cross-checks them; PROPOSAL and LeptonInjector place z=0 at the outer radius
of the outermost non-AIR shell, so a mismatched pair silently embeds the
detector in the wrong medium (e.g. rock).
"""

from pathlib import Path
from typing import List, NamedTuple, Union


class EarthLayer(NamedTuple):
    """Spherical shell of an earth model density file."""

    inner_radius: float
    outer_radius: float
    label: str
    media_type: str


# Media type (third earth-file column) that must surround the modules.
_REQUIRED_MEDIA_TYPE = {
    "WATER": "WATER",
    "ICE": "ICE",
}

_HINT = (
    "The configured paths.earth_model_location (or the geo-file name it is "
    "resolved from by default) likely does not describe this detector site. "
    "Set config.detector.check_earth_consistency = False to bypass this check."
)


def parse_earth_layers(earth_model_file: Union[str, Path]) -> List[EarthLayer]:
    """Read the spherical shells of an earth model density file.

    Data lines are ``outer_radius_m label MEDIUMTYPE ...``; '#' starts a
    comment. Each shell's inner radius is the previous shell's outer radius.
    """
    layers = []
    inner_radius = 0.0
    with open(earth_model_file) as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip() or line[0] in "# \t":
                continue
            data = line.split("#", 1)[0].split()
            if len(data) < 3:
                raise ValueError(
                    f"{earth_model_file}:{lineno}: expected "
                    f"'outer_radius label MEDIUMTYPE ...', got {line!r}"
                )
            try:
                outer_radius = float(data[0])
            except ValueError:
                raise ValueError(
                    f"{earth_model_file}:{lineno}: invalid outer radius {data[0]!r}"
                ) from None
            if outer_radius <= inner_radius:
                raise ValueError(
                    f"{earth_model_file}:{lineno}: layer radii must be strictly "
                    f"ascending, got {outer_radius} m after {inner_radius} m"
                )
            layers.append(EarthLayer(inner_radius, outer_radius, data[1], data[2].upper()))
            inner_radius = outer_radius
    if not layers:
        raise ValueError(f"{earth_model_file}: no layer definitions found")
    return layers


def _containing_layer(layers: List[EarthLayer], radius: float) -> Union[EarthLayer, None]:
    """Return the shell containing ``radius``, or None if outside all shells."""
    for layer in layers:
        if layer.inner_radius < radius <= layer.outer_radius:
            return layer
    return None


def check_detector_earth_consistency(detector, earth_model_file: Union[str, Path]) -> None:
    """Validate that every detector module sits in a medium-matching shell.

    A module at depth z sits at radius ``surface_radius + z`` (z=0 at the
    outer radius of the outermost non-AIR shell) and must lie within the
    contiguous stack of shells ending at the surface whose media type matches
    the detector medium. Boundaries count as inside, so modules anchored
    exactly on the seabed or at the surface pass.
    """
    medium_name = None if detector.medium is None else detector.medium.name
    if medium_name not in _REQUIRED_MEDIA_TYPE:
        raise ValueError(
            f"Cannot check earth model consistency: detector medium is "
            f"{medium_name}, expected one of {sorted(_REQUIRED_MEDIA_TYPE)}"
        )
    required_media = _REQUIRED_MEDIA_TYPE[medium_name]

    layers = parse_earth_layers(earth_model_file)
    non_air_indices = [i for i, layer in enumerate(layers) if layer.media_type != "AIR"]
    if not non_air_indices:
        raise ValueError(f"{earth_model_file}: every layer is AIR")
    top_index = non_air_indices[-1]
    top = layers[top_index]
    surface_radius = top.outer_radius

    if top.media_type != required_media:
        raise ValueError(
            f"Detector medium {medium_name} is inconsistent with earth model "
            f"'{earth_model_file}': its outermost non-AIR layer "
            f"'{top.label}' has media type {top.media_type}, but medium "
            f"{medium_name} requires {required_media} at the surface. {_HINT}"
        )

    stack_inner = surface_radius
    for layer in layers[top_index::-1]:
        if layer.media_type != required_media:
            break
        stack_inner = layer.inner_radius

    z = detector.module_coords[:, 2]
    z_min, z_max = float(z.min()), float(z.max())
    r_min, r_max = surface_radius + z_min, surface_radius + z_max
    if stack_inner <= r_min and r_max <= surface_radius:
        return

    problems = []
    if r_min < stack_inner:
        layer = _containing_layer(layers, r_min)
        where = (
            f"the {layer.media_type} layer '{layer.label}' "
            f"(r in ({layer.inner_radius:.1f}, {layer.outer_radius:.1f}] m)"
            if layer is not None
            else "below all layers of the earth model"
        )
        problems.append(
            f"the deepest module (z = {z_min:.1f} m, r = {r_min:.1f} m) lies in {where}"
        )
    if r_max > surface_radius:
        layer = _containing_layer(layers, r_max)
        where = (
            f"the {layer.media_type} layer '{layer.label}' "
            f"(r in ({layer.inner_radius:.1f}, {layer.outer_radius:.1f}] m)"
            if layer is not None
            else "above the outermost layer of the earth model"
        )
        problems.append(
            f"the highest module (z = {z_max:.1f} m, r = {r_max:.1f} m) lies in {where}"
        )

    raise ValueError(
        f"Detector modules lie outside the {required_media} shells of earth "
        f"model '{earth_model_file}': modules span z in [{z_min:.1f}, {z_max:.1f}] m "
        f"relative to the surface (z=0 at r = {surface_radius:.1f} m), but the "
        f"matching {required_media} shells only cover depths 0.0 to "
        f"{surface_radius - stack_inner:.1f} m below the surface "
        f"(r in [{stack_inner:.1f}, {surface_radius:.1f}] m); " + "; ".join(problems) + f". {_HINT}"
    )
