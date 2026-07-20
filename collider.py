"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: collider
Execute: from loom import collider

Colliders: primitive (sphere / capsule) and mesh collision geometry for the loom solver. Author the
body's collision once as a drawn lCollider node (it draws itself and its radii in the viewport), then
attach() it to the solver so every garment collides. add_* write straight onto the solver (no drawn
node); build_* create a reusable, drawn lCollider.
"""

import logging
log = logging.getLogger("loom.collider")

import maya.cmds as cmds

from . import util
from .solver import get_solver


def add_sphere(solver:str, driver:str, radius:float) -> int:
    """Attach a sphere collider to the solver, driven by a transform's world matrix.

    A collider straight on the solver (no drawn lCollider). See build_collider() + attach() for the
    reusable, drawn path.

    Args:
        solver: (str):   - the loom solver.
        driver: (str):   - transform whose world matrix positions the sphere.
        radius: (float): - sphere radius.

    Returns:
        int: the collider array index used.
    """
    idx = len(cmds.getAttr(solver + ".sphere", multiIndices=True) or [])
    cmds.connectAttr(driver + ".worldMatrix[0]", "%s.sphere[%d].sphMatrix" % (solver, idx), force=True)
    cmds.setAttr("%s.sphere[%d].sphRadius" % (solver, idx), radius)
    return idx


def add_capsule(solver:str, driver_a:str, driver_b:str, radius_a:float, radius_b:float=None) -> int:
    """Attach a capsule collider to the solver, between two transforms (e.g. an arm or leg segment).

    A collider straight on the solver (no drawn lCollider). See build_collider() + attach() for the
    reusable, drawn path.

    Args:
        solver:   (str):   - the loom solver.
        driver_a: (str):   - transform at end A.
        driver_b: (str):   - transform at end B.
        radius_a: (float): - radius at end A.
        radius_b: (float): - radius at end B (None = same as A).

    Returns:
        int: the collider array index used.
    """
    if radius_b is None:
        radius_b = radius_a
    idx = len(cmds.getAttr(solver + ".capsule", multiIndices=True) or [])
    cmds.connectAttr(driver_a + ".worldMatrix[0]", "%s.capsule[%d].capMatrixA" % (solver, idx), force=True)
    cmds.connectAttr(driver_b + ".worldMatrix[0]", "%s.capsule[%d].capMatrixB" % (solver, idx), force=True)
    cmds.setAttr("%s.capsule[%d].capRadiusA" % (solver, idx), radius_a)
    cmds.setAttr("%s.capsule[%d].capRadiusB" % (solver, idx), radius_b)
    return idx


def add_limb(solver:str, joints:list, radius:float, radius_tip:float=None) -> list:
    """Approximate a limb with a chain of capsule colliders on the solver, following its joints.

    A straight capsule per bone that bends with the joints - the way a physics asset approximates a
    body. Prefer this for arms, legs, fingers.

    Args:
        solver:     (str):   - the loom solver.
        joints:     (list):  - ordered joints along the limb (a capsule spans each consecutive pair).
        radius:     (float): - capsule radius at the root.
        radius_tip: (float): - radius at the last joint (None = constant, else linearly tapered).

    Returns:
        list: the collider indices added.
    """
    if radius_tip is None:
        radius_tip = radius
    span = max(1, len(joints) - 1)
    return [add_capsule(solver, joints[k], joints[k + 1],
                        radius + (radius_tip - radius) * (float(k)     / span),
                        radius + (radius_tip - radius) * (float(k + 1) / span))
            for k in range(len(joints) - 1)]


def _fit_radii(mesh:str, joints:list, percentile:float=0.9, scale:float=1.0) -> list:
    """Per-bone radius fitted to a body mesh: the radial percentile of the verts projecting onto each
    bone. Purely rest geometry + joint positions, no skin weights. Returns one radius per bone (or
    None where a bone caught no vertices)."""
    flat = cmds.xform(mesh + ".vtx[*]", query=True, worldSpace=True, translation=True)
    pts = [(flat[i * 3], flat[i * 3 + 1], flat[i * 3 + 2]) for i in range(len(flat) // 3)]
    positions = [cmds.xform(j, query=True, worldSpace=True, translation=True) for j in joints]

    radii = []
    for k in range(len(joints) - 1):
        a, b = positions[k], positions[k + 1]
        abx, aby, abz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        l2 = abx * abx + aby * aby + abz * abz
        dists = []
        for p in pts:
            t = ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby + (p[2] - a[2]) * abz) / l2 if l2 > 1e-9 else 0.0
            if t < -0.1 or t > 1.1:
                continue                                    # not alongside this bone
            t = max(0.0, min(1.0, t))
            qx, qy, qz = a[0] + abx * t, a[1] + aby * t, a[2] + abz * t
            dists.append(((p[0] - qx) ** 2 + (p[1] - qy) ** 2 + (p[2] - qz) ** 2) ** 0.5)
        if dists:
            dists.sort()
            radii.append(dists[int(percentile * (len(dists) - 1))] * scale)
        else:
            radii.append(None)
    return radii


def auto_capsules(solver:str, collider_mesh:str, joints:list, percentile:float=0.9, scale:float=1.0) -> list:
    """Fit a capsule collider to each bone by measuring the body mesh, straight onto the solver.

    See build_collider() for the same fit as a separate, reusable, drawn lCollider node.

    Args:
        solver:        (str):   - the loom solver.
        collider_mesh: (str):   - the BODY mesh to approximate (the leg, the torso...).
        joints:        (list):  - ordered joints along the body part.
        percentile:    (float): - 0..1 radial percentile per bone (0.9 = encloses most of the surface).
        scale:         (float): - multiply every fitted radius.

    Returns:
        list: the collider indices added.
    """
    radii = _fit_radii(collider_mesh, joints, percentile, scale)
    idx = []
    for k in range(len(joints) - 1):
        r = radii[k] if radii[k] else (radii[k - 1] if k and radii[k - 1] else 1.0)
        idx.append(add_capsule(solver, joints[k], joints[k + 1], r, r))
    return idx


def build_collider(joints:list, mesh:str=None, radius:float=1.0, percentile:float=0.9,
                   scale:float=1.0, name:str=None) -> str:
    """Create a separate, drawn lCollider node: capsules along the joints, shared across cloths.

    Author the body's collision once here - it draws itself in the viewport (see the capsules and
    their radii) - then attach() it to any number of lCloth nodes. This is how nRigid / a physics
    asset works: one collider object, many cloths.

    Args:
        joints:     (list):  - ordered joints; a capsule spans each consecutive pair.
        mesh:       (str):   - body mesh to fit the radii to (None = use `radius` everywhere).
        radius:     (float): - fallback radius when no mesh is given.
        percentile: (float): - 0..1 radial percentile per bone when fitting.
        scale:      (float): - multiply every fitted radius.
        name:       (str):   - node name.

    Returns:
        str: the lCollider transform node.
    """
    util.load()
    # a clean transform + shape, so the outliner shows "lCollider1" (not an auto "transform1")
    xform = cmds.createNode("transform", name=name or util.next_name("lCollider"))
    shape = cmds.createNode("lCollider", name=xform + "Shape", parent=xform)
    radii = _fit_radii(mesh, joints, percentile, scale) if mesh is not None else [radius] * (len(joints) - 1)
    for k in range(len(joints) - 1):
        cmds.connectAttr(joints[k]     + ".worldMatrix[0]", "%s.capsule[%d].capMatrixA" % (shape, k), force=True)
        cmds.connectAttr(joints[k + 1] + ".worldMatrix[0]", "%s.capsule[%d].capMatrixB" % (shape, k), force=True)
        r = radii[k] if radii[k] else radius
        cmds.setAttr("%s.capsule[%d].capRadiusA" % (shape, k), r)
        cmds.setAttr("%s.capsule[%d].capRadiusB" % (shape, k), r)
    return xform


def build_sphere_collider(driver:str, radius:float, solver:str=None, name:str=None) -> str:
    """Create a drawn lCollider with a single sphere (driven by `driver`) and attach it to the solver.

    The node is VISIBLE in the viewport (it draws the sphere at its radius) and selectable - unlike
    add_sphere(), which writes the sphere straight onto the solver with no node to see.

    Args:
        driver: (str):   - transform whose world matrix positions the sphere.
        radius: (float): - sphere radius.
        solver: (str):   - the loom solver to attach to (None = the shared one).
        name:   (str):   - node name.

    Returns:
        str: the lCollider transform.
    """
    util.load()
    xform = cmds.createNode("transform", name=name or util.next_name("lCollider"))
    shape = cmds.createNode("lCollider", name=xform + "Shape", parent=xform)
    cmds.connectAttr(driver + ".worldMatrix[0]", shape + ".sphere[0].sphMatrix", force=True)
    cmds.setAttr(shape + ".sphere[0].sphRadius", radius)
    attach(shape, solver or get_solver())
    return xform


def build_mesh_collider(mesh:str, name:str=None) -> str:
    """Create a drawn lCollider that shows a body mesh as the collider geometry (nRigid look).

    Mesh collision IS now supported (v2): enable the collider's meshCollide attribute and attach() the
    node, and the solver's mesh-collision path takes the collider mesh into account. The node also draws
    the collider mesh in the viewport (wire + face colours, display modes). Use build_collider() capsules
    for the cheaper primitive approximation.

    Args:
        mesh: (str): - the body mesh to show as a collider.
        name: (str): - node name.

    Returns:
        str: the lCollider transform.
    """
    util.load()
    xform = cmds.createNode("transform", name=name or util.next_name("lCollider"))
    shape = cmds.createNode("lCollider", name=xform + "Shape", parent=xform)
    cmds.connectAttr(util.shape(mesh) + ".worldMesh[0]", shape + ".inMesh", force=True)
    return xform


def attach(collider_node:str, solver:str=None):
    """Feed an lCollider's primitives into the loom solver, so every garment on that solver collides.

    Matrices come from the collider's own drivers (the joints), radii live-linked from the lCollider -
    tweak a radius on the collider and the solver follows. When meshCollide is on, the collider mesh and
    its scalar attributes are wired into the solver's mesh-collision path too.

    Args:
        collider_node: (str): - the lCollider node (transform or shape).
        solver:        (str): - the loom solver (None = the shared one).
    """
    collider_node = util.collider_shape(collider_node)
    solver = solver or get_solver()

    for i in (cmds.getAttr(collider_node + ".capsule", multiIndices=True) or []):
        src_a = cmds.listConnections("%s.capsule[%d].capMatrixA" % (collider_node, i), source=True, destination=False, plugs=True)
        src_b = cmds.listConnections("%s.capsule[%d].capMatrixB" % (collider_node, i), source=True, destination=False, plugs=True)
        j = len(cmds.getAttr(solver + ".capsule", multiIndices=True) or [])
        if src_a:
            cmds.connectAttr(src_a[0], "%s.capsule[%d].capMatrixA" % (solver, j), force=True)
        if src_b:
            cmds.connectAttr(src_b[0], "%s.capsule[%d].capMatrixB" % (solver, j), force=True)
        cmds.connectAttr("%s.capsule[%d].capRadiusA" % (collider_node, i), "%s.capsule[%d].capRadiusA" % (solver, j), force=True)
        cmds.connectAttr("%s.capsule[%d].capRadiusB" % (collider_node, i), "%s.capsule[%d].capRadiusB" % (solver, j), force=True)

    for i in (cmds.getAttr(collider_node + ".sphere", multiIndices=True) or []):
        src = cmds.listConnections("%s.sphere[%d].sphMatrix" % (collider_node, i), source=True, destination=False, plugs=True)
        j = len(cmds.getAttr(solver + ".sphere", multiIndices=True) or [])
        if src:
            cmds.connectAttr(src[0], "%s.sphere[%d].sphMatrix" % (solver, j), force=True)
        cmds.connectAttr("%s.sphere[%d].sphRadius" % (collider_node, i), "%s.sphere[%d].sphRadius" % (solver, j), force=True)

    # v2 : a collider mesh feeds the solver's mesh-collision path when meshCollide is on
    if util.has_attr(collider_node, "meshCollide") and cmds.getAttr(collider_node + ".meshCollide"):
        mesh_src = cmds.listConnections(collider_node + ".inMesh", source=True, destination=False, plugs=True)
        if mesh_src:
            j = len(cmds.getAttr(solver + ".collider", multiIndices=True) or [])
            cmds.connectAttr(mesh_src[0], "%s.collider[%d].colMesh" % (solver, j), force=True)
            for src_attr, dst_attr in (("doubleSided", "colDoubleSided"), ("thickness", "colThickness"),
                                       ("innerFatness", "colInnerFatness"), ("outerFatness", "colOuterFatness"),
                                       ("staticFriction", "colStaticFriction"), ("dynamicFriction", "colDynamicFriction"),
                                       ("geometryAnimated", "colAnimated")):
                try:
                    cmds.connectAttr("%s.%s" % (collider_node, src_attr), "%s.collider[%d].%s" % (solver, j, dst_attr), force=True)
                except Exception as error:
                    log.warning("collider mesh attr '%s' not wired (%s)." % (src_attr, error))


def detach(collider_node:str, solver:str=None):
    """Undo attach(): disconnect the collider's primitives / mesh from the solver.

    Removes only the solver-side capsule/sphere/collider elements fed from THIS collider (matched by the
    source connection), leaving other colliders on the solver untouched.

    Args:
        collider_node: (str): - the lCollider node (transform or shape).
        solver:        (str): - the loom solver (None = the shared one).
    """
    collider_node = util.collider_shape(collider_node)
    solver = solver or get_solver()

    # the plugs this collider drives on the solver, matched by shared source. Capsules/spheres are driven
    # by the same matrix sources the collider uses; the mesh element by the collider's inMesh source.
    def _sources(plugs):
        out = set()
        for p in plugs:
            src = cmds.listConnections(p, source=True, destination=False, plugs=True) or []
            if src:
                out.add(src[0])
        return out

    cap_srcs  = _sources(["%s.capsule[%d].capMatrixA" % (collider_node, i) for i in (cmds.getAttr(collider_node + ".capsule", multiIndices=True) or [])])
    sph_srcs  = _sources(["%s.sphere[%d].sphMatrix" % (collider_node, i) for i in (cmds.getAttr(collider_node + ".sphere", multiIndices=True) or [])])
    mesh_srcs = _sources([collider_node + ".inMesh"])

    for array, child, srcs in (("capsule", "capMatrixA", cap_srcs), ("sphere", "sphMatrix", sph_srcs), ("collider", "colMesh", mesh_srcs)):
        for j in (cmds.getAttr(solver + "." + array, multiIndices=True) or [])[::-1]:
            src = cmds.listConnections("%s.%s[%d].%s" % (solver, array, j, child), source=True, destination=False, plugs=True) or []
            if src and src[0] in srcs:
                cmds.removeMultiInstance("%s.%s[%d]" % (solver, array, j), b=True)
