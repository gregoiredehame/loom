"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: solver
Execute: from loom import solver

The shared loom solver: find/create it, reset it, and set its world settings. One solver owns the
timestep, the forces and the particle state of every garment and collider connected to it, so separate
cloths interact in a single solve (mutual collision).
"""

import logging
log = logging.getLogger("loom.solver")

import maya.cmds as cmds

from . import util


def get_solver(name:str="loom1") -> str:
    """Find the shared loom solver, or create one. All garments/colliders share it.

    loom is a locator (drawn): a transform `name` + a shape `nameShape`, so it is
    visible/selectable in the outliner and viewport. The solver ignores its own transform (the sim is
    world-space, driven by connected inputs). Returns the SHAPE (every attr the setup wires lives on it).
    Always ensures `time` is connected (a dangling time input never advances the sim), and sets startFrame
    on a fresh solver.

    Args:
        name: (str): - the solver transform name to create when none exists yet.

    Returns:
        str: the loom solver shape node.
    """
    util.load()
    existing = cmds.ls(type="loom")
    if existing:
        node = existing[0]
    else:
        xform = cmds.createNode("transform", name=name)
        node  = cmds.createNode("loom", name=xform + "Shape", parent=xform)
        cmds.setAttr(node + ".startFrame", cmds.playbackOptions(query=True, min=True))
    if not cmds.listConnections(node + ".time", source=True, destination=False):
        cmds.connectAttr("time1.outTime", node + ".time", force=True)
    return node


def reset(solver:str=None):
    """Reset the solver: rebuild every cloth's rest state and drop the RAM cache.

    Bumps the solver's resetTrigger so the next evaluation rebuilds from the rest pose, then snaps to the
    start frame. A forward sim is only valid played in order from the start.

    Args:
        solver: (str): - the loom solver (None = the shared one).
    """
    solver = solver or get_solver()
    try:
        cmds.setAttr(solver + ".resetTrigger", cmds.getAttr(solver + ".resetTrigger") + 1)
    except Exception:
        pass
    cmds.currentTime(cmds.getAttr(solver + ".startFrame"))


def partial_reset(solver:str=None, frame:float=None):
    """Keep the cached sim up to `frame` and resimulate only from there (iterate a shot's end).

    Sets the solver's resetFrame so cached frames beyond it are dropped, then plays forward from that
    frame. Nothing before `frame` is recomputed.

    Args:
        solver: (str):   - the loom solver (None = the shared one).
        frame:  (float): - keep every cached frame up to and including this one.
    """
    solver = solver or get_solver()
    if frame is None:
        frame = cmds.currentTime(query=True)
    cmds.setAttr(solver + ".resetFrame", int(frame))
    cmds.currentTime(int(frame))


def world(solver:str=None, gravity=None, wind_speed:float=None, wind_dir=None, wind_noise:float=None,
          air_density:float=None, substeps:int=None, iterations:int=None, fps:float=None,
          self_collisions:bool=None, ground:bool=None, ground_height:float=None):
    """Set the solver's world / environment settings (pass only what you want to change).

    Args:
        solver:          (str):   - the loom solver (None = the shared one).
        gravity:         (tuple): - world gravity vector (x, y, z), cm/s^2 (default (0, -980, 0)).
        wind_speed:      (float): - wind speed.
        wind_dir:        (tuple): - wind direction vector (x, y, z).
        wind_noise:      (float): - gusty wind amount, 0..1.
        air_density:     (float): - air density (scales aero forces).
        substeps:        (int):   - sub-steps per frame (raise for fast motion / collision quality).
        iterations:      (int):   - constraint iterations per sub-step.
        fps:             (float): - frame rate used for the timestep.
        self_collisions: (bool):  - global self-collision gate.
        ground:          (bool):  - enable the infinite ground plane.
        ground_height:   (float): - the ground Y height.
    """
    solver = solver or get_solver()
    if gravity is not None:         cmds.setAttr(solver + ".gravity", gravity[0], gravity[1], gravity[2], type="double3")
    if wind_speed is not None:      cmds.setAttr(solver + ".windSpeed", wind_speed)
    if wind_dir is not None:        cmds.setAttr(solver + ".windDirection", wind_dir[0], wind_dir[1], wind_dir[2], type="double3")
    if wind_noise is not None:      cmds.setAttr(solver + ".windNoise", wind_noise)
    if air_density is not None:     cmds.setAttr(solver + ".airDensity", air_density)
    if substeps is not None:        cmds.setAttr(solver + ".substeps", substeps)
    if iterations is not None:      cmds.setAttr(solver + ".iterations", iterations)
    if fps is not None:             cmds.setAttr(solver + ".frameRate", fps)
    if self_collisions is not None: cmds.setAttr(solver + ".selfCollisions", self_collisions)
    if ground is not None:          cmds.setAttr(solver + ".groundCollide", ground)
    if ground_height is not None:   cmds.setAttr(solver + ".groundHeight", ground_height)
