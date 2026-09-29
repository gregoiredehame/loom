"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: util
Execute: from loom import util

Shared low-level helpers: the plug-in loader and the small mesh/name utilities every module uses.
"""

import os
import logging
log = logging.getLogger("loom.util")

import maya.cmds as cmds


def _plugin_dir():
    """The loom plug-in folder for the running Maya version: <loom>/plugins/<version>/.

    loom.mll is built per Maya version into loom_dynamics/plugins/<version>/ (same layout as kata). This
    returns that folder so load() can put it on MAYA_PLUG_IN_PATH before loading, making loom load itself
    without depending on kata's startup.
    """
    from . import __loom__
    return os.path.join(__loom__, "plugins", cmds.about(version=True))


def _register_icons():
    """Put loom's icons folder on XBMLANGPATH so the outliner finds out_<nodeType>.png for our nodes.

    Maya resolves a custom node's outliner icon from `out_<nodeType>.png` on XBMLANGPATH. loom's icons live
    in <loom>/icons/ (out_loom.png, out_loomCloth.png, out_loomCollider.png). Doing this from Python (before
    any loom node is created) is more reliable than doing it in C++ at plug-in load, because the path is
    already resolved and the outliner has not cached a default icon yet. Idempotent.
    """
    from . import __loom__
    icon_dir = os.path.join(__loom__, "icons").replace("\\", "/")   # Maya path lists want forward slashes
    if not os.path.isdir(icon_dir):
        return
    current = os.environ.get("XBMLANGPATH", "")
    if icon_dir not in current.split(os.pathsep):
        os.environ["XBMLANGPATH"] = (current + os.pathsep + icon_dir) if current else icon_dir


def load():
    """Load the standalone loom plug-in (loom.mll) that registers the loom / loomCloth / loomCollider nodes.

    Adds loom's own per-version plug-in folder to MAYA_PLUG_IN_PATH, then loads "loom". Falls back to
    "kata" only for older scenes where the nodes might still live there. Safe to call repeatedly.

    Returns:
        str: the name of the loaded plug-in ("loom" or "kata"), or None when neither could load.
    """
    from . import PLUGIN, PLUGIN_FALLBACK

    # make sure the outliner can find our node icons before any loom node exists
    _register_icons()

    # make sure Maya can find loom.mll : add <loom>/plugins/<version> to the plug-in path once
    plugin_dir = _plugin_dir()
    if os.path.isdir(plugin_dir):
        current = os.environ.get("MAYA_PLUG_IN_PATH", "")
        if plugin_dir not in current.split(os.pathsep):
            os.environ["MAYA_PLUG_IN_PATH"] = (current + os.pathsep + plugin_dir) if current else plugin_dir

    # Maya pops a "a new plug-in has been detected, load it?" dialog the first time it loads an unknown
    # .mll. Silence it around our load (and restore the user's setting after) so loom loads without a prompt.
    try:
        ask = cmds.optionVar(query="loadDialogWhenNewPluginDetected")
    except Exception:
        ask = None
    try:
        cmds.optionVar(intValue=("loadDialogWhenNewPluginDetected", 0))
    except Exception:
        pass

    try:
        # - a plug-in only counts when it really registered the loom node: loadPlugin raises nothing when
        #   initializePlugin fails (a node type id taken by another plug-in, say), and kata no longer holds loom
        for name in (PLUGIN, PLUGIN_FALLBACK):
            try:
                if not cmds.pluginInfo(name, query=True, loaded=True):
                    cmds.loadPlugin(name, quiet=True)
                if "loom" in (cmds.pluginInfo(name, query=True, dependNode=True) or []):
                    return name
            except Exception:
                continue
        log.error("could not load the loom plug-in ('%s', fallback '%s'): either loom.mll is not built into %s, or "
                  "its nodes could not register (see the error above)." % (PLUGIN, PLUGIN_FALLBACK, plugin_dir))
        return None
    finally:
        # restore the user's original "ask when new plug-in detected" preference
        if ask is not None:
            try:
                cmds.optionVar(intValue=("loadDialogWhenNewPluginDetected", int(ask)))
            except Exception:
                pass


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
    """Vertex count of the mesh feeding a loomCloth (its inMesh source).

    polyEvaluate can return an int OR a one-element list depending on the node passed, so normalise it
    (an un-normalised list count silently breaks setAttr on the doubleArray maps).

    Args:
        cloth: (str): - the loomCloth shape.

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
    """Resolve the loomCloth shape from a transform or shape (returns node unchanged if already a shape)."""
    if cmds.nodeType(node) == "loomCloth":
        return node
    shapes = cmds.listRelatives(node, shapes=True, type="loomCloth", fullPath=True) or []
    return shapes[0] if shapes else node


def collider_shape(node:str) -> str:
    """Resolve the loomCollider shape from a transform or shape (returns node unchanged if already a shape)."""
    if cmds.nodeType(node) == "loomCollider":
        return node
    shapes = cmds.listRelatives(node, shapes=True, type="loomCollider", fullPath=True) or []
    return shapes[0] if shapes else node
