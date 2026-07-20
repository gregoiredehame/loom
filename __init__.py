"""
LOOM. (c)

Author: Gregoire Dehame
Created: Jul 20, 2026
Modified: Jul 20, 2026
Module: __init__
Execute: import loom

Loom : an in-house Maya cloth / soft-body toolset (an XPBD solver). This is the
Python API. The nodes (loom solver, loomCloth, loomCollider) currently ship inside the kata plug-in (kata.mll);
loom.load() loads it. A standalone loom.mll is a later extraction (the C++ lives in kata/plugins for now).

    import loom
    body  = loom.build_collider(joints, mesh="body_geo")   # a drawn capsule collider
    cloth = loom.setup_after_skin("shirt_geo")             # sim the skinned shirt
    loom.attach(body)                                       # the shirt collides with the body
    loom.pin_border(cloth, "shirt_geo", axis=1, side="max") # pin its top edge
    loom.apply_preset(cloth, "cotton")
    loom.display(cloth, mode="soft primitives")             # physics draw
"""

from __future__ import annotations
from __future__ import absolute_import

__versiontuple__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __versiontuple__)

__author__ = "Gregoire Dehame"

import os
import sys
import logging
log = logging.getLogger("loom")          # base logger; all loom.* module loggers propagate here
log.setLevel(logging.INFO)

# the folder on disk is "loom_dynamics" (the git-submodule path), but the package is meant to be used as
# "loom" : alias this module so `import loom` and `from loom import ...` resolve to this exact package. The
# sub-modules already do `from . import ...`, so relative imports keep working; only the top-level name
# gets the short alias. Registering it on the package itself means the alias exists however loom is first
# imported (via kata boot, or a direct `from kata.ui import loom_dynamics`).
sys.modules.setdefault("loom", sys.modules[__name__])

__loom__ = os.path.dirname(os.path.abspath(__file__))

# the standalone Maya plug-in that registers the loom / loomCloth / loomCollider nodes (loom.mll, built
# per Maya version into loom_dynamics/plugins/<version>/). load() tries "loom" first, then falls back to
# "kata" only for legacy scenes whose nodes were authored while loom still shipped inside kata.mll.
PLUGIN = "loom"
PLUGIN_FALLBACK = "kata"


# --- public API : re-exported from the sub-modules so `import loom; loom.<fn>()` just works ---------
from .solver    import get_solver, reset, partial_reset, world
from .cloth     import setup, setup_after_skin, setup_wrapped, remove_cloth
from .collider  import (build_collider, build_sphere_collider, build_mesh_collider,
                        add_sphere, add_capsule, add_limb, auto_capsules, attach, detach)
from .weights   import pin, pin_border, paint, set_map
from .material  import apply_preset, save_material, load_material, presets
from .display   import display
from .cache     import bake, preflight

from . import util


def load():
    """Load the Maya plug-in that provides the loom nodes (loom, or kata as a fallback)."""
    return util.load()


def reload_api():
    """Reload every loom sub-module (dev helper). Does not touch the C++ plug-in."""
    import importlib
    from . import util, solver, cloth, collider, weights, material, display, cache
    for module in (util, solver, cloth, collider, weights, material, display, cache):
        importlib.reload(module)
    importlib.reload(importlib.import_module(__name__))
