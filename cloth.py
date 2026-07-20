"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: cloth
Execute: from loom import cloth

Garments: add a mesh (plain or skinned) to the solver as an lCloth shape, wire its material forward to
the solver, and manage the garment's lifecycle. lCloth is a locator that computes its output mesh AND
draws itself (nCloth style); it blends the skinned input toward the solved mesh by pinWeights.
"""

import logging
log = logging.getLogger("loom.cloth")

import maya.cmds as cmds

from . import util
from .solver import get_solver


# every per-garment attribute forwarded from lCloth to loom.inCloth[idx]. The solver reads ONLY these;
# lCloth is the artist-facing source of truth. Long names match on both nodes.
MATERIAL = (
    # v1 base material
    "mass", "stretchStiffness", "compressionStiffness", "bendStiffness", "maxStretch",
    "maxSpeed", "thickness", "friction", "airDrag", "airLift", "damping",
    # v2 material : friction split, self-collision, damping, aero, pins
    "staticFriction", "dynamicFriction", "selfCollide", "selfThickness",
    "viscousDamping", "reducer", "skinDrag", "pinWeights",
    # v2 goal posing (sim follows anim while keeping collision consistency)
    "goalStrength", "goalTrailStiffness", "goalTrailViscosity", "goalViscosity",
    "goalVelocityLimit", "goalLowerThreshold", "goalUpperThreshold",
    # v2 painted maps (Base is the scalar above ; Range x Map is the paint)
    "massRange", "massMap", "stretchStiffnessRange", "stretchStiffnessMap",
    "compressionStiffnessRange", "compressionStiffnessMap", "bendStiffnessRange", "bendStiffnessMap",
    "thicknessRange", "thicknessMap", "goalStrengthRange", "goalStrengthMap",
    "reducerRange", "reducerMap",
)


def _wire_material(cloth:str, solver:str, idx:int):
    """Connect each per-garment material attr on lCloth to loom.inCloth[idx].

    Skips (with a warning) any attr that fails to connect, so a single missing/renamed attr can never
    abort the whole setup. pinWeights is forwarded too, so the solver can pin/kinematic-drive vertices
    itself (in addition to lCloth's client-side blend).
    """
    for attr in MATERIAL:
        try:
            cmds.connectAttr("%s.%s" % (cloth, attr), "%s.inCloth[%d].%s" % (solver, idx, attr), force=True)
        except Exception as error:
            log.warning("lCloth material '%s' not wired to the solver (%s)." % (attr, error))


def setup(mesh:str, solver:str=None, start:float=None, fps:float=24.0, name:str=None) -> str:
    """Add a plain (un-skinned) mesh to the loom solver as an lCloth SHAPE.

    Same wiring as setup_after_skin, but the rest input is the mesh's own geometry (frozen into a hidden
    intermediate copy) instead of a skinCluster, so lCloth drives the visible shape without feeding it
    from itself. Use setup_after_skin for skinned garments.

    Args:
        mesh:   (str):   - the mesh (transform or shape) to simulate.
        solver: (str):   - the loom solver to join (None = the shared one).
        start:  (float): - solver start frame (None = leave the solver's current value).
        fps:    (float): - frames per second used for the timestep.
        name:   (str):   - lCloth node name.

    Returns:
        str: the lCloth shape node.
    """
    util.load()
    solver = solver or get_solver()
    if start is not None:
        cmds.setAttr(solver + ".startFrame", start)
    cmds.setAttr(solver + ".frameRate", fps)

    shp   = util.shape(mesh)
    xform = cmds.listRelatives(shp, parent=True, fullPath=True)[0]
    idx   = len(cmds.getAttr(solver + ".inCloth", multiIndices=True) or [])

    nm = name or util.next_name("lCloth")
    # a hidden intermediate copy of the shape holds the rest pose (the sim input)
    dup  = cmds.duplicate(xform, name=nm + "Rest")[0]
    rest = util.shape(dup)
    rest = cmds.parent(rest, xform, shape=True, relative=True)[0]
    cmds.setAttr(rest + ".intermediateObject", 1)
    cmds.delete(dup)

    xf = cmds.createNode("transform", name=nm)
    lc = cmds.createNode("lCloth", name=xf + "Shape", parent=xf)

    rest_out = rest + ".outMesh"
    cmds.connectAttr(rest_out, "%s.inCloth[%d].inMesh" % (solver, idx), force=True)
    cmds.connectAttr(rest_out, lc + ".inMesh", force=True)
    cmds.connectAttr("%s.outCloth[%d]" % (solver, idx), lc + ".solvedMesh", force=True)
    _wire_material(lc, solver, idx)
    cmds.connectAttr(lc + ".outMesh", shp + ".inMesh", force=True)
    return lc


def setup_after_skin(mesh:str, skin:str=None, solver:str=None, name:str=None) -> str:
    """Add a skinned garment to the loom solver as an lCloth SHAPE (nCloth style).

    Wiring:
        skinCluster.outputGeometry -> loom.inCloth[i].inMesh   (the skinned pose)
        skinCluster.outputGeometry -> lCloth.inMesh            (same skinned pose)
        loom.outCloth[i]           -> lCloth.solvedMesh        (the solved garment)
        lCloth.<material>          -> loom.inCloth[i].<material>
        lCloth.outMesh             -> <render mesh>.inMesh     (drives the visible garment)
    lCloth blends inMesh toward solvedMesh per vertex by pinWeights (0 = stays skinned = pin).

    Args:
        mesh:   (str): - the skinned garment mesh.
        skin:   (str): - its skinCluster (None = found on the mesh).
        solver: (str): - the loom solver to join (None = the shared one).
        name:   (str): - lCloth node name.

    Returns:
        str: the lCloth shape node.
    """
    util.load()
    if skin is None:
        skins = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
        if not skins:
            log.error("no skinCluster found on '%s'." % mesh)
            return None
        skin = skins[0]

    solver = solver or get_solver()
    shp    = util.shape(mesh)
    idx    = len(cmds.getAttr(solver + ".inCloth", multiIndices=True) or [])

    xform = cmds.createNode("transform", name=name or util.next_name("lCloth"))
    lc    = cmds.createNode("lCloth", name=xform + "Shape", parent=xform)

    skin_out = skin + ".outputGeometry[0]"
    cmds.connectAttr(skin_out, "%s.inCloth[%d].inMesh" % (solver, idx), force=True)
    cmds.connectAttr(skin_out, lc + ".inMesh", force=True)
    cmds.connectAttr("%s.outCloth[%d]" % (solver, idx), lc + ".solvedMesh", force=True)
    _wire_material(lc, solver, idx)
    cmds.connectAttr(lc + ".outMesh", shp + ".inMesh", force=True)
    return lc


def setup_wrapped(render_mesh:str, reduce_percent:float=80.0, start:float=None, fps:float=24.0):
    """Performance path: simulate a low-res proxy, wrap the render mesh onto it (Chaos style).

    The single biggest performance lever: a garment of tens of thousands of polys never needs to be
    simulated directly. A reduced proxy carries the sim, a proximityWrap drives the heavy render mesh.
    Paint the blend map / add colliders on the PROXY, not the render mesh.

    NOTE: needs the proximityWrap deformer (Maya 2020+). Verify the wrap.

    Args:
        render_mesh:    (str):   - the high-resolution mesh to keep at render quality.
        reduce_percent: (float): - how much to reduce for the proxy (80 = keep ~20% of the polys).
        start:          (float): - reset frame (None = playback start).
        fps:            (float): - timestep fps.

    Returns:
        tuple: (proxy_transform, cloth_node, proximityWrap_node).
    """
    util.load()

    proxy = cmds.duplicate(render_mesh, name=str(render_mesh).split("|")[-1] + "_clothProxy")[0]
    cmds.select(proxy, replace=True)
    cmds.polyReduce(version=1, percentage=reduce_percent, keepQuadsWeight=1.0,
                    triangulate=False, replaceOriginal=True)
    cmds.delete(proxy, constructionHistory=True)

    node = setup(proxy, start=start, fps=fps)

    try:
        wrap = cmds.deformer(render_mesh, type="proximityWrap")[0]
        cmds.setAttr(wrap + ".wrapMode", 1)              # offset (follows the driver's deformation)
        cmds.setAttr(wrap + ".maxDrivers", 1)
        cmds.setAttr(wrap + ".falloffScale", 1.0)
        cmds.proximityWrap(wrap, edit=True, addDrivers=[util.shape(proxy)])
    except Exception as error:
        log.error("proximityWrap setup failed (%s). Proxy + lCloth are ready; wrap the render mesh "
                  "to '%s' by hand." % (error, proxy))
        wrap = None

    return proxy, node, wrap


def remove_cloth(cloth:str, solver:str=None):
    """Remove a garment from the solver: disconnect and delete its inCloth/outCloth elements.

    Safe now the solver keys its state by logical index, so removing one garment does not disturb the
    others. Leaves the lCloth node itself in place unless you delete it yourself.

    Args:
        cloth:  (str): - the lCloth shape (transform or shape).
        solver: (str): - the loom solver (None = found from the cloth's solvedMesh source).
    """
    shape = util.cloth_shape(cloth)
    if solver is None:
        src = cmds.listConnections(shape + ".solvedMesh", source=True, destination=False) or []
        solver = src[0] if src else get_solver()
    for j in (cmds.getAttr(solver + ".inCloth", multiIndices=True) or []):
        out = cmds.listConnections("%s.outCloth[%d]" % (solver, j), source=False, destination=True) or []
        if shape in out:
            for attr in ("inCloth", "outCloth", "outContact"):
                try:
                    cmds.removeMultiInstance("%s.%s[%d]" % (solver, attr, j), b=True)
                except Exception:
                    pass
