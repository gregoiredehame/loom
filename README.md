# loom — in-house Maya cloth API

XPBD cloth / soft-body toolset for Maya. This folder is the **Python API**. The nodes
(`loom` solver, `lCloth`, `lCollider`) currently ship inside the **kata** plug-in (`kata.mll`); a
standalone `loom.mll` is a later extraction. `loom.load()` loads whichever is available.

## Install

`C:\Users\USER\Documents\maya\scripts` is already on Maya's Python path (that is where kata lives), so
`import loom` works out of the box. For the styled Attribute Editor templates, put `loom/scripts` on the
MEL path — add to your `userSetup.py` (or `userSetup.mel`):

```python
# userSetup.py
import os, maya.mel as mel
loom_scripts = os.path.expanduser("~/Documents/maya/scripts/loom/scripts")
mel.eval('putenv "MAYA_SCRIPT_PATH" (`getenv "MAYA_SCRIPT_PATH"` + ";%s")' % loom_scripts.replace("\\", "/"))
```

or simply copy the three `AE*Template.mel` files into a folder already on `MAYA_SCRIPT_PATH`.

## Quick start

```python
import loom

# a body collider from a joint chain, fitted to the body mesh, drawn in the viewport
body = loom.build_collider(spine_joints, mesh="body_geo")

# simulate a skinned shirt; it collides with the body
shirt = loom.setup_after_skin("shirt_geo")
loom.attach(body)

# pin the collar, paint the rest, give it a fabric
loom.pin_border(shirt, "shirt_geo", axis=1, side="max")
loom.apply_preset(shirt, "cotton")
loom.paint(shirt, "pinWeights")            # opens the Maya paint tool on the pin map

# physics draw + play
loom.display(shirt, mode="soft primitives")
loom.reset()
```

## Modules

| module | what it holds |
|--------|---------------|
| `loom.solver`   | `get_solver`, `reset`, `partial_reset`, `world` (gravity/wind/substeps…) |
| `loom.cloth`    | `setup`, `setup_after_skin`, `setup_wrapped`, `remove_cloth`, the `MATERIAL` wiring |
| `loom.collider` | `build_collider`, `build_sphere_collider`, `build_mesh_collider`, `attach`, `detach`, `add_*`, `auto_capsules` |
| `loom.weights`  | `pin`, `pin_border`, `paint`, `set_map`, `PAINTABLE` |
| `loom.material` | `apply_preset`, `save_material`, `load_material`, `presets` |
| `loom.display`  | `display` (physics draw modes) |
| `loom.cache`    | `bake` (Alembic), `preflight` (geometry checklist) |
| `loom.util`     | `load` (plug-in), `shape`, `next_name`, `vert_count`, … |

## Physics draw modes

- **lCloth** `display(mode=...)` : `None` / `Surface` (faces) / `Mesh` (wire) / `Soft Primitives`
  (particles + constraint links) / `Paint Map` (per-vertex weight colours).
- **lCollider** : `None` / `Surface` (capsules + spheres) / `Mesh` (the collider geometry).

## Status

- Python API : complete, `import loom` works.
- Nodes : provided by `kata.mll` for now (the C++ lives in `kata/plugins`). Standalone `loom.mll` is a
  planned extraction (see `kata/plugins/LOOM_V2_PLAN.md`).
- Smoke test : `kata/rig/loom_test.py` (10/10). A loom-native test suite is a follow-up.
