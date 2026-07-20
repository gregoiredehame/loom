"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: weights
Execute: from loom import weights

Per-vertex maps: pin vertices to the skinned pose, pin a border row, open the Artisan paint tool on an
lCloth map, or set a map directly from a list of floats. pinWeights is the pin/blend map (0 = pinned to
the skinned pose, 1 = fully simulated); the other maps modulate the material scalars per vertex.
"""

import logging
log = logging.getLogger("loom.weights")

import maya.cmds as cmds

from . import util


# per-vertex maps that live on lCloth and are the ones a user paints. pinWeights is the pin/blend map.
PAINTABLE = ("pinWeights", "massMap", "stretchStiffnessMap", "compressionStiffnessMap",
             "bendStiffnessMap", "thicknessMap", "goalStrengthMap", "reducerMap")


def _register_paintable():
    """Register every lCloth per-vertex map as a paintable double-array (idempotent, safe to re-call)."""
    for attr in PAINTABLE:
        try:
            cmds.makePaintable("lCloth", attr, attrType="doubleArray")
        except Exception:
            pass


def pin(cloth:str, vertices, count:int=None):
    """Pin vertices to the skinned pose by setting their pinWeight to 0 (1 = fully simulated).

    Args:
        cloth:    (str):  - the lCloth shape.
        vertices: (list): - vertex indices to pin.
        count:    (int):  - total vertex count (None = read it from the mesh feeding lCloth).
    """
    n = count if count else util.vert_count(cloth)
    if isinstance(n, (list, tuple)):        # polyEvaluate/caller may hand back [N]; want a scalar int
        n = n[0]
    n = int(n)
    if not n:
        log.error("cannot pin '%s': unknown vertex count (pass count=)." % cloth)
        return
    w = [1.0] * n
    for i in vertices:
        if 0 <= i < n:
            w[i] = 0.0
    cmds.setAttr(cloth + ".pinWeights", w, type="doubleArray")


def pin_border(cloth:str, mesh:str, axis:int=1, side:str="max", tolerance:float=0.05):
    """Pin the extreme row of vertices along a world axis (e.g. the top edge of a curtain).

    Args:
        cloth:     (str):   - the lCloth shape.
        mesh:      (str):   - the simulated mesh.
        axis:      (int):   - 0=X, 1=Y, 2=Z.
        side:      (str):   - "max" or "min" end of that axis.
        tolerance: (float): - how close to the extreme a vertex must be to get pinned.
    """
    flat = cmds.xform(mesh + ".vtx[*]", query=True, worldSpace=True, translation=True)
    coords = [flat[i * 3 + axis] for i in range(len(flat) // 3)]
    edge = max(coords) if side == "max" else min(coords)
    verts = [i for i, c in enumerate(coords) if abs(c - edge) <= tolerance]
    pin(cloth, verts, count=len(coords))


def paint(cloth:str, param:str="pinWeights"):
    """Open the Maya paint tool on one of an lCloth's per-vertex maps (one-click paint flow).

    Ensures the map array exists at the mesh's vertex count, registers it paintable, then activates the
    Artisan attribute paint context targeting it.

    Args:
        cloth: (str): - the lCloth shape (transform or shape).
        param: (str): - the map to paint: pinWeights, massMap, stretchStiffnessMap, bendStiffnessMap,
                        compressionStiffnessMap, thicknessMap, goalStrengthMap or reducerMap.
    """
    shape = util.cloth_shape(cloth)
    if param not in PAINTABLE:
        log.error("'%s' is not a paintable lCloth map (%s)." % (param, ", ".join(PAINTABLE)))
        return
    _register_paintable()
    n = util.vert_count(shape)
    if n:
        default = 1.0 if param == "pinWeights" else 0.0
        current = cmds.getAttr(shape + "." + param) or []
        if len(current) != n:
            cmds.setAttr(shape + "." + param, [default] * n, type="doubleArray")
    try:
        cmds.select(cmds.listConnections(shape + ".inMesh", source=True, destination=False) or shape)
        # artAttrCtx wants the attribute as "<nodeType>.<node>.<attr>" via the -at flag on the ctx.
        ctx = "artAttrLoomCtx"
        if not cmds.artAttrCtx(ctx, exists=True):
            cmds.artAttrCtx(ctx)
        cmds.setToolTo(ctx)
        cmds.artAttrCtx(ctx, edit=True, attrSelected="lCloth.%s.%s" % (shape, param))
    except Exception as error:
        log.warning("could not open the paint tool for %s.%s (%s)." % (shape, param, error))


def set_map(cloth:str, param:str, values:list):
    """Set an lCloth per-vertex map directly from a list of floats (0..1).

    Args:
        cloth:  (str):  - the lCloth shape (transform or shape).
        param:  (str):  - the map attribute (see paint()).
        values: (list): - one value per vertex.
    """
    shape = util.cloth_shape(cloth)
    cmds.setAttr(shape + "." + param, list(values), type="doubleArray")
