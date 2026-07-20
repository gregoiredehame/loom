"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: display
Execute: from loom import display

Viewport physics draw for loomCloth and loomCollider nodes: the draw mode, the wireframe and
face colours, and the face transparency. loomCloth/loomCollider draw themselves - there is no separate viz
node - so this just sets the draw attributes on the shape.
"""

import logging
log = logging.getLogger("loom.display")

import maya.cmds as cmds


# physics-draw enum values. loomCloth has all five, loomCollider has the first three.
CLOTH_DRAW    = {"none": 0, "surface": 1, "mesh": 2, "soft primitives": 3, "soft": 3, "paint map": 4, "map": 4}
COLLIDER_DRAW = {"none": 0, "surface": 1, "mesh": 2}


def display(node:str, mode=None, wire=None, face=None, alpha:float=None):
    """Set the viewport physics draw of a loomCloth or loomCollider (pass only what you want to change).

    Args:
        node:  (str):        - the loomCloth/loomCollider node (transform or shape).
        mode:  (int | str):  - the physics draw mode, by index or name. loomCloth: None/Surface/Mesh/
                              Soft Primitives/Paint Map (0..4). loomCollider: None/Surface/Mesh (0..2).
        wire:  (tuple):      - wireframe colour (r, g, b).
        face:  (tuple):      - face colour (r, g, b).
        alpha: (float):      - face transparency 0..1.
    """
    shape = node
    kind = cmds.nodeType(shape)
    if kind not in ("loomCloth", "loomCollider"):
        for t in ("loomCloth", "loomCollider"):
            found = cmds.listRelatives(node, shapes=True, type=t, fullPath=True) or []
            if found:
                shape, kind = found[0], t
                break
    if mode is not None:
        if isinstance(mode, str):
            table = CLOTH_DRAW if kind == "loomCloth" else COLLIDER_DRAW
            mode = table.get(mode.strip().lower(), 1)
        cmds.setAttr(shape + ".displayMode", mode)
    if wire is not None:  cmds.setAttr(shape + ".loomWireColor", wire[0], wire[1], wire[2], type="double3")
    if face is not None:  cmds.setAttr(shape + ".loomFaceColor", face[0], face[1], face[2], type="double3")
    if alpha is not None: cmds.setAttr(shape + ".faceAlpha", alpha)
