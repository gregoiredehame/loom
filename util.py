"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: util
Execute: from loom import util

Shared low-level helpers: the plug-in loader and the small mesh/name utilities every module uses.
"""

import logging
log = logging.getLogger("loom.util")

import maya.cmds as cmds


def load():
    """Load the Maya plug-in that registers the loom nodes.

    The nodes (loom / lCloth / lCollider) currently ship inside the kata plug-in; a standalone loom
    plug-in is a later extraction. Tries "loom" first, then falls back to "kata", so the API keeps
    working through the migration. Safe to call repeatedly.

    Returns:
        str: the name of the loaded plug-in ("loom" or "kata"), or None when neither could load.
    """
    from . import PLUGIN, PLUGIN_FALLBACK
    for name in (PLUGIN, PLUGIN_FALLBACK):
        try:
            if cmds.pluginInfo(name, query=True, loaded=True):
                return name
        except Exception:
            pass
        try:
            cmds.loadPlugin(name, quiet=True)
            return name
        except Exception:
            continue
    log.error("could not load a loom plug-in ('%s' or '%s')." % (PLUGIN, PLUGIN_FALLBACK))
    return None


def shape(mesh:str) -> str:
    """Return the non-intermediate mesh shape under a transform (or the shape itself).

    Args:
        mesh: (str): - a transform or a mesh shape.

    Returns:
        str: the deformable mesh shape.
    """
    if cmds.nodeType(mesh) == "mesh":
        return mesh
    shapes = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True, type="mesh") or []
    return shapes[0] if shapes else mesh


def next_name(base:str) -> str:
    """First free 'base1', 'base2', ... not already used by a node (auto-increment like Maya's own).

    Args:
        base: (str): - the name stem.

    Returns:
        str: an unused "<base><n>" name.
    """
    i = 1
    while cmds.objExists("%s%d" % (base, i)):
        i += 1
    return "%s%d" % (base, i)


def vert_count(cloth:str) -> int:
    """Vertex count of the mesh feeding an lCloth (its inMesh source).

    polyEvaluate can return an int OR a one-element list depending on the node passed, so normalise it
    (an un-normalised list count silently breaks setAttr on the doubleArray maps).

    Args:
        cloth: (str): - the lCloth shape.

    Returns:
        int: the vertex count, or 0 when it cannot be resolved.
    """
    src = cmds.listConnections(cloth + ".inMesh", source=True, destination=False)
    if src:
        try:
            v = cmds.polyEvaluate(src[0], vertex=True)
            return v[0] if isinstance(v, (list, tuple)) else int(v)
        except Exception:
            pass
    return 0


def has_attr(node:str, attr:str) -> bool:
    """True when `node` carries `attr` (so old scenes without a v2 attr still work cleanly).

    Args:
        node: (str): - the node.
        attr: (str): - the attribute long name.

    Returns:
        bool: whether the attribute exists on the node.
    """
    return cmds.attributeQuery(attr, node=node, exists=True)


def cloth_shape(node:str) -> str:
    """Resolve the lCloth shape from a transform or shape (returns node unchanged if already a shape)."""
    if cmds.nodeType(node) == "lCloth":
        return node
    shapes = cmds.listRelatives(node, shapes=True, type="lCloth", fullPath=True) or []
    return shapes[0] if shapes else node


def collider_shape(node:str) -> str:
    """Resolve the lCollider shape from a transform or shape (returns node unchanged if already a shape)."""
    if cmds.nodeType(node) == "lCollider":
        return node
    shapes = cmds.listRelatives(node, shapes=True, type="lCollider", fullPath=True) or []
    return shapes[0] if shapes else node
