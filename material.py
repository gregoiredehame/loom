"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: material
Execute: from loom import material

Fabric material: apply a named preset of material scalars to an lCloth, list the presets, or save/load
the full scalar material of a garment to/from a JSON file on disk. Presets and save/load cover only the
scalar material attributes; the per-vertex maps are handled by loom.weights.
"""

import json
import logging
log = logging.getLogger("loom.material")

import maya.cmds as cmds

from . import util
from .cloth import MATERIAL


PRESETS = {
    "cotton":  {"stretchStiffness": 0.9, "compressionStiffness": 0.6, "bendStiffness": 0.15, "mass": 1.0,  "damping": 0.03, "airDrag": 0.1, "thickness": 1.0},
    "denim":   {"stretchStiffness": 1.0, "compressionStiffness": 0.9, "bendStiffness": 0.5,  "mass": 2.0,  "damping": 0.05, "airDrag": 0.15, "thickness": 1.5},
    "silk":    {"stretchStiffness": 0.7, "compressionStiffness": 0.3, "bendStiffness": 0.03, "mass": 0.4,  "damping": 0.02, "airDrag": 0.25, "thickness": 0.5},
    "leather": {"stretchStiffness": 1.0, "compressionStiffness": 1.0, "bendStiffness": 0.7,  "mass": 2.5,  "damping": 0.08, "airDrag": 0.1, "thickness": 2.0},
    "jersey":  {"stretchStiffness": 0.5, "compressionStiffness": 0.4, "bendStiffness": 0.05, "mass": 0.8,  "damping": 0.04, "airDrag": 0.15, "thickness": 0.8},
    "rubber":  {"stretchStiffness": 1.0, "compressionStiffness": 1.0, "bendStiffness": 0.9,  "mass": 1.5,  "damping": 0.10, "airDrag": 0.05, "thickness": 1.0},
}


def presets() -> list:
    """List the available fabric preset names.

    Returns:
        list: the preset names, sorted.
    """
    return sorted(PRESETS)


def apply_preset(cloth:str, preset:str="cotton"):
    """Apply a fabric preset (a dict of material scalars) to an lCloth.

    Args:
        cloth:  (str): - the lCloth shape (transform or shape).
        preset: (str): - one of: cotton, denim, silk, leather, jersey, rubber.
    """
    shape = util.cloth_shape(cloth)
    values = PRESETS.get(preset)
    if not values:
        log.error("unknown preset '%s' (have: %s)." % (preset, ", ".join(sorted(PRESETS))))
        return
    for attr, val in values.items():
        try:
            cmds.setAttr(shape + "." + attr, val)
        except Exception as error:
            log.warning("preset attr '%s' not applied (%s)." % (attr, error))


def save_material(cloth:str, path:str) -> str:
    """Write every scalar material attribute of an lCloth to a JSON file (maps excluded).

    Only the non-map scalar material attributes are saved; the per-vertex maps (names ending in "Map")
    are skipped - they belong to the mesh and are handled by loom.weights.

    Args:
        cloth: (str): - the lCloth shape (transform or shape).
        path:  (str): - the .json output path.

    Returns:
        str: the written path.
    """
    shape = util.cloth_shape(cloth)
    data = {}
    for attr in MATERIAL:
        if attr.endswith("Map"):
            continue
        try:
            data[attr] = cmds.getAttr(shape + "." + attr)
        except Exception as error:
            log.warning("material attr '%s' not read (%s)." % (attr, error))
    path = path.replace("\\", "/")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    log.info("saved material: %s" % path)
    return path


def load_material(cloth:str, path:str):
    """Read a JSON material file and set each scalar attribute onto an lCloth.

    Args:
        cloth: (str): - the lCloth shape (transform or shape).
        path:  (str): - the .json file to read.
    """
    shape = util.cloth_shape(cloth)
    path = path.replace("\\", "/")
    with open(path, "r") as f:
        data = json.load(f)
    for attr, val in data.items():
        try:
            cmds.setAttr(shape + "." + attr, val)
        except Exception as error:
            log.warning("material attr '%s' not applied (%s)." % (attr, error))
