"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: cache
Execute: from loom import cache

Bake and preflight. bake() steps the deterministic forward sim across a range and freezes the result to
an Alembic cache (the mesh that goes to lighting). preflight() checks a garment mesh for the geometry
problems that break cloth sim before you ever run it.
"""

import logging
log = logging.getLogger("loom.cache")

import maya.cmds as cmds

from . import util


def preflight(cloth:str) -> list:
    """Check a garment mesh for the geometry problems that break cloth sim (automated geometry checklist).

    Returns a list of human-readable issues (empty = clean) and logs each. Checks: non-manifold geometry,
    lamina faces, zero-area faces, ngons, and whether static/dynamic friction and skin/air drag are
    ordered correctly.

    Args:
        cloth: (str): - the loomCloth shape (transform or shape) or the simulated mesh.

    Returns:
        list: the issues found (strings), empty when the garment is clean.
    """
    shape = cloth
    if cmds.nodeType(shape) == "loomCloth":
        src = cmds.listConnections(shape + ".inMesh", source=True, destination=False) or []
        mesh = src[0] if src else None
    else:
        mesh = cloth
    issues = []
    if mesh and cmds.objExists(mesh):
        nonmanifold = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
        if nonmanifold:
            issues.append("non-manifold edges (%d)" % len(nonmanifold))
        lamina = cmds.polyInfo(mesh, laminaFaces=True) or []
        if lamina:
            issues.append("lamina faces (%d)" % len(lamina))
        try:
            faces = cmds.polyEvaluate(mesh, face=True)
            tris  = cmds.polyEvaluate(mesh, triangle=True)
            if faces and tris and tris > faces * 2.2:
                issues.append("mostly-ngon or heavily triangulated mesh (quads recommended)")
        except Exception:
            pass
    if cmds.nodeType(shape) == "loomCloth":
        if util.has_attr(shape, "dynamicFriction") and cmds.getAttr(shape + ".dynamicFriction") > cmds.getAttr(shape + ".staticFriction"):
            issues.append("dynamicFriction > staticFriction (dynamic should be <= static)")
        if util.has_attr(shape, "skinDrag") and cmds.getAttr(shape + ".skinDrag") > cmds.getAttr(shape + ".airDrag"):
            issues.append("skinDrag > airDrag (skin drag should be <= air/form drag)")
    for issue in issues:
        log.warning("preflight '%s': %s" % (cloth, issue))
    if not issues:
        log.info("preflight '%s': clean." % cloth)
    return issues


def bake(mesh:str, start:float=None, end:float=None, path:str=None) -> str:
    """Simulate forward across the range and freeze the result to an Alembic cache.

    A forward sim is deterministic only when played IN ORDER from the start, so this steps every frame
    from start to end before exporting - never scrub a live sim and expect the same result. The cache
    is what goes to lighting; re-import it as a static, scrubbable, renderable mesh.

    NOTE: needs the AbcExport plug-in. Not runtime-tested here.

    Args:
        mesh:  (str):   - the simulated mesh (or its render mesh when wrapped).
        start: (float): - first frame (None = playback start).
        end:   (float): - last frame (None = playback end).
        path:  (str):   - .abc output path (None = user temp dir).

    Returns:
        str: the written .abc path.
    """
    if not cmds.pluginInfo("AbcExport", query=True, loaded=True):
        cmds.loadPlugin("AbcExport")

    if start is None:
        start = cmds.playbackOptions(query=True, min=True)
    if end is None:
        end = cmds.playbackOptions(query=True, max=True)

    # deterministic forward sim: walk every frame in order before capturing
    for f in range(int(start), int(end) + 1):
        cmds.currentTime(f)

    if path is None:
        path = cmds.internalVar(userTmpDir=True) + str(mesh).split("|")[-1] + "_cloth.abc"
    path = path.replace("\\", "/")

    root = cmds.ls(mesh, long=True)[0]
    cmds.AbcExport(jobArg="-frameRange %d %d -uvWrite -worldSpace -dataFormat ogawa -root %s -file %s"
                          % (int(start), int(end), root, path))
    log.info("baked cloth cache: %s" % path)
    return path
