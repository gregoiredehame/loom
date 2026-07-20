# loom : in-house Maya cloth API

XPBD cloth and soft-body toolset for Maya. This folder holds both the **Python API** and the standalone
**`loom.mll`** plug-in that registers the nodes (`loom` solver, `loomCloth`, `loomCollider`). `loom.load()`
puts the per-version plug-in folder on the plug-in path and loads it, so the API is self-contained.

## Install

`loom` lives inside kata at `kata/ui/loom_dynamics`, so it comes along with kata. From Maya:

```python
from kata.ui import loom_dynamics as loom
loom.load()   # loads loom.mll for the running Maya version
```

kata already calls this on boot (`main.run(plugins=True)`), so the nodes are ready as soon as Maya starts.

For the styled Attribute Editor templates, put `loom_dynamics/scripts` on the MEL path. Add to your
`userSetup.py`:

```python
import os, maya.mel as mel
loom_scripts = os.path.expanduser("~/Documents/maya/scripts/kata/ui/loom_dynamics/scripts")
mel.eval('putenv "MAYA_SCRIPT_PATH" (`getenv "MAYA_SCRIPT_PATH"` + ";%s")' % loom_scripts.replace("\\", "/"))
```

or copy the three `AE*Template.mel` files into a folder already on `MAYA_SCRIPT_PATH`.

## Quick start

```python
from kata.ui import loom_dynamics as loom

# a body collider from a joint chain, fitted to the body mesh, drawn in the viewport
body = loom.build_collider(spine_joints, mesh="body_geo")

# simulate a skinned shirt; it collides with the body
shirt = loom.setup_after_skin("shirt_geo")
loom.attach(body)

# pin the collar, paint the rest, give it a fabric
loom.pin_border(shirt, "shirt_geo", axis=1, side="max")
loom.apply_preset(shirt, "cotton")
loom.paint(shirt, "pinWeights")            # opens the Maya paint tool on the pin map

# physics draw and play
loom.display(shirt, mode="soft primitives")
loom.reset()
```

## Modules

| module | what it holds |
|--------|---------------|
| `solver`   | `get_solver`, `reset`, `partial_reset`, `world` (gravity/wind/substeps…) |
| `cloth`    | `setup`, `setup_after_skin`, `setup_wrapped`, `remove_cloth`, the `MATERIAL` wiring |
| `collider` | `build_collider`, `build_sphere_collider`, `build_mesh_collider`, `attach`, `detach`, `add_*`, `auto_capsules` |
| `weights`  | `pin`, `pin_border`, `paint`, `set_map`, `PAINTABLE` |
| `material` | `apply_preset`, `save_material`, `load_material`, `presets` |
| `display`  | `display` (physics draw modes) |
| `cache`    | `bake` (Alembic), `preflight` (geometry checklist) |
| `util`     | `load` (plug-in), `shape`, `next_name`, `vert_count`, … |

## Physics draw modes

- **loomCloth** `display(mode=...)` : `None` / `Surface` (faces) / `Mesh` (wire) / `Soft Primitives`
  (particles plus constraint links) / `Paint Map` (per-vertex weight colours).
- **loomCollider** : `None` / `Surface` (capsules plus spheres) / `Mesh` (the collider geometry).

## Build

The C++ is a standalone plug-in built per Maya version into `plugins/<version>/loom.mll`. Open
`plugins/loom.sln` in Visual Studio (batch-build the `release|x64` configs), or run
`scripts/build_all.bat 2026 loom` from the repo root.

## Status

- Python API : complete.
- Nodes : provided by the standalone `loom.mll` (own VS solution in `plugins/`).
- Smoke test : `kata/rig/loom_test.py` (10/10). A loom-native test suite is a follow-up.
