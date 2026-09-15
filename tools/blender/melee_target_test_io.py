# ##############################################################################
# Melee Break-the-Targets (.tt) I/O — Blender add-on
#
# Authors Super Smash Bros. Melee "Break the Targets" levels in Blender and
# round-trips them to/from the native PC port's `mods/targettest/<name>.tt`
# line-based text format, so Blender is the level editor.
#
# The module is split into two layers:
#
#   1. A PURE format layer (no `bpy` import anywhere): `parse_tt`, `serialize_tt`,
#      the character-name table, and the coordinate mapping. This layer is
#      importable and testable OUTSIDE Blender (see `test_roundtrip.py`).
#
#   2. A `bpy` layer (operators + panel) that is only defined when `bpy` is
#      importable. It registers File > Import/Export operators and a View3D
#      sidebar panel.
#
# Coordinate convention (single mapping, applied symmetrically on import AND
# export so a round trip is the identity):
#
#       melee_x =  blender_x
#       melee_y =  blender_z     # Blender "up"  -> Melee "up"
#       melee_z = -blender_y     # Blender "back" -> Melee "depth", negated
#
# Inverse (import):
#
#       blender_x =  melee_x
#       blender_y = -melee_z
#       blender_z =  melee_y
#
# Melee stage units: X right, Y up, Z depth (into the screen). The port stores
# target coordinates as bare world floats (see `gw_TTMod_Target` in
# `pc/platform/gw_runtime.c`), so the mapping is a pure permutation + sign flip.
# ##############################################################################

bl_info = {
    "name": "Melee Break-the-Targets (.tt) I/O",
    "author": "GD's Melee",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "File > Import/Export, View3D > Sidebar > Melee TT",
    "description": (
        "Author Super Smash Bros. Melee Break-the-Targets levels in Blender "
        "and round-trip the port's .tt level format"
    ),
    "category": "Import-Export",
}

# =============================================================================
# PURE FORMAT LAYER — no bpy dependency. Safe to import with plain python3.
# =============================================================================

# Maximum targets per level, matching TT_MAX_TARGETS in the port loader.
MAX_TARGETS = 21

# Default platform thickness (Melee "up"/Blender "up" extent) used when a
# platform is imported: the .tt format stores no vertical thickness (collision
# is 2D XY), so a cube gets this default height. Units are Melee stage units.
DEFAULT_PLATFORM_THICKNESS = 2.0

# Character names -> ckind, matching `tt_parse_ckind` in the port loader
# (`pc/platform/gw_runtime.c`) exactly, so names resolve identically in both.
# Values are the decomp's CharacterKind enum (ft/forward.h).
CHARACTER_NAMES = {
    "captain": 0, "falcon": 0,
    "donkey": 1, "dk": 1,
    "fox": 2,
    "gamewatch": 3, "gw": 3,
    "kirby": 4,
    "koopa": 5, "bowser": 5,
    "link": 6,
    "luigi": 7,
    "mario": 8,
    "marth": 9, "mars": 9,
    "mewtwo": 10,
    "ness": 11,
    "peach": 12,
    "pikachu": 13,
    "iceclimbers": 14, "popo": 14, "nana": 14,
    "jigglypuff": 15, "purin": 15,
    "samus": 16,
    "yoshi": 17,
    "zelda": 18,
    "sheik": 19, "seak": 19,
    "falco": 20,
    "clink": 21, "younglink": 21,
    "drmario": 22,
    "emblem": 23, "roy": 23,
    "pichu": 24,
    "ganon": 25, "ganondorf": 25,
}

# Canonical (primary) name for each ckind, used for human-friendly display.
CHARACTER_PRIMARY = {
    0: "captain", 1: "donkey", 2: "fox", 3: "gamewatch", 4: "kirby",
    5: "koopa", 6: "link", 7: "luigi", 8: "mario", 9: "marth", 10: "mewtwo",
    11: "ness", 12: "peach", 13: "pikachu", 14: "iceclimbers", 15: "jigglypuff",
    16: "samus", 17: "yoshi", 18: "zelda", 19: "sheik", 20: "falco",
    21: "younglink", 22: "drmario", 23: "roy", 24: "pichu", 25: "ganon",
}


def blender_to_melee(x, y, z):
    """Map a Blender point (X right, Y forward, Z up) to Melee (X right, Y up, Z depth)."""
    return (x, z, -y)


def melee_to_blender(x, y, z):
    """Map a Melee point (X right, Y up, Z depth) to Blender (X right, Y forward, Z up)."""
    return (x, -z, y)


def normalize_character(value):
    """Canonicalize a `character` value to the string written to a .tt file.

    Integer strings are normalised to a plain decimal integer ("+8"/"08" -> "8");
    recognised names are lower-cased to their canonical spelling ("MARIO" ->
    "mario"); anything else is returned verbatim so it round-trips (the port
    loader rejects it, but Blender keeps it lossless).
    """
    v = str(value).strip()
    try:
        int(v, 10)
        return str(int(v, 10))
    except ValueError:
        pass
    key = v.lower()
    if key in CHARACTER_NAMES:
        return key
    return v


def resolve_ckind(value):
    """Resolve a `character` value to its CharacterKind integer, or None.

    Accepts either a bare integer (decimal) or a case-insensitive name. None
    means the value is not a known character (the port loader would skip it).
    """
    v = str(value).strip()
    try:
        return int(v, 10)
    except ValueError:
        pass
    return CHARACTER_NAMES.get(v.lower())


def _fmt(v):
    """Shortest round-trip decimal for a float, normalising -0.0 -> 0.0."""
    r = repr(float(v))
    if r == "-0.0":
        r = "0.0"
    return r


def parse_tt(text):
    """Parse .tt text into a level dict. Pure; no bpy.

    Returns::
        {
            "name": str,                 # may be ""
            "character": str,            # canonical string form (see normalize_character)
            "targets": [(x, y, z), ...],
            "platforms": [(cx, cy, cz, w, d), ...],
        }

    Blank lines and `#` comments are ignored; unknown keys are ignored (matching
    the port loader). Malformed target/platform lines are skipped.
    """
    level = {"name": "", "character": "mario", "targets": [], "platforms": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        key = parts[0].lower()
        val = parts[1].strip() if len(parts) > 1 else ""
        if key == "name":
            level["name"] = val
        elif key == "character":
            level["character"] = normalize_character(val)
        elif key == "target":
            nums = val.split()
            if len(nums) >= 3:
                try:
                    x, y, z = float(nums[0]), float(nums[1]), float(nums[2])
                except ValueError:
                    continue
                level["targets"].append((x, y, z))
        elif key == "platform":
            nums = val.split()
            if len(nums) >= 5:
                try:
                    cx, cy, cz = float(nums[0]), float(nums[1]), float(nums[2])
                    w, d = float(nums[3]), float(nums[4])
                except ValueError:
                    continue
                level["platforms"].append((cx, cy, cz, w, d))
        # every other key (e.g. "basestage") is accepted and ignored
    return level


def serialize_tt(level):
    """Serialize a level dict to .tt text. Pure; no bpy. Ends with a single LF."""
    name = level.get("name") or ""
    character = level.get("character") or "mario"
    lines = []
    lines.append(("name " + name) if name else "name")
    lines.append("character " + str(character))
    for x, y, z in level.get("targets", []):
        lines.append("target %s %s %s" % (_fmt(x), _fmt(y), _fmt(z)))
    for cx, cy, cz, w, d in level.get("platforms", []):
        lines.append(
            "platform %s %s %s %s %s" % (_fmt(cx), _fmt(cy), _fmt(cz), _fmt(w), _fmt(d))
        )
    return "\n".join(lines) + "\n"


# =============================================================================
# BPY LAYER — operators + panel. Only defined when bpy is importable, so the
# pure layer above remains importable without bpy.
# =============================================================================

try:
    import bpy
    from bpy.props import StringProperty
    from bpy_extras.io_utils import ImportHelper, ExportHelper

    _HAS_BPY = True
except ImportError:  # pragma: no cover - exercised by the standalone test
    bpy = None
    _HAS_BPY = False


if _HAS_BPY:

    def classify_object(obj):
        """Return the Melee role of an object: "target", "platform", or None.

        Precedence:
          1. custom property `melee_role` (or `role`), value "target"/"platform";
          2. object name prefix "target*" / "platform*" (case-insensitive);
          3. an EMPTY living in a collection named "targets".
        """
        role = obj.get("melee_role")
        if role is None:
            role = obj.get("role")
        if isinstance(role, str):
            r = role.strip().lower()
            if r in ("target", "platform"):
                return r
        name = obj.name.lower()
        if name.startswith("target"):
            return "target"
        if name.startswith("platform"):
            return "platform"
        if obj.type == "EMPTY":
            for coll in obj.users_collection:
                if coll.name.lower() == "targets":
                    return "target"
        return None

    def _world_extents(obj):
        """World-space extents (x, y, z) of an object.

        For MESH objects this is the axis-aligned bounding box (`obj.dimensions`,
        which accounts for scale and rotation). Non-mesh objects fall back to
        their scale, so an empty can still stand in for a platform placeholder.
        """
        if obj.type == "MESH":
            d = obj.dimensions
            return (d.x, d.y, d.z)
        s = obj.scale
        return (s.x, s.y, s.z)

    def gather_level(scene):
        """Gather (targets, platforms) in Melee coordinates from the scene."""
        targets = []
        platforms = []
        for obj in scene.objects:
            role = classify_object(obj)
            if role is None:
                continue
            loc = obj.matrix_world.translation
            mx, my, mz = blender_to_melee(loc.x, loc.y, loc.z)
            if role == "target":
                targets.append((mx, my, mz))
            else:  # platform
                dx, dy, dz = _world_extents(obj)
                cx = mx
                # The format documents `cy` as the *top* surface (the walkable
                # line in the 2D XY collision). Recover it from the object's
                # center plus half its vertical (Blender Z / Melee up) extent.
                cy = my + dz / 2.0
                cz = mz
                w = dx            # Melee X extent  <- Blender X extent
                d = dy            # Melee Z depth   <- Blender Y extent
                platforms.append((cx, cy, cz, w, d))
        return targets, platforms

    def count_level_objects(scene):
        """Return (num_targets, num_platforms) for the sidebar panel."""
        nt = np = 0
        for obj in scene.objects:
            role = classify_object(obj)
            if role == "target":
                nt += 1
            elif role == "platform":
                np += 1
        return nt, np

    def _make_empty(name, location):
        obj = bpy.data.objects.new(name, None)
        obj.location = location
        obj.empty_display_type = "SPHERE"
        obj.empty_display_size = 1.0
        obj["melee_role"] = "target"
        bpy.context.collection.objects.link(obj)
        return obj

    def _make_platform(name, center, dims):
        # Default cube primitive is 2x2x2; scale it to the target dimensions.
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=center)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (dims[0] / 2.0, dims[1] / 2.0, dims[2] / 2.0)
        obj["melee_role"] = "platform"
        return obj

    class IMPORT_OT_melee_tt(bpy.types.Operator, ImportHelper):
        """Import a Melee Break-the-Targets .tt level into the scene."""

        bl_idname = "import_scene.melee_tt"
        bl_label = "Import Melee Break-the-Targets (.tt)"
        bl_options = {"REGISTER", "UNDO"}
        filename_ext = ".tt"

        def execute(self, context):
            try:
                with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                self.report({"ERROR"}, "Could not read %s: %s" % (self.filepath, e))
                return {"CANCELLED"}

            level = parse_tt(text)
            scene = context.scene

            # Persist the level identity so a re-export reproduces the file.
            scene.melee_name = level["name"]
            scene.melee_character = level["character"]

            t = DEFAULT_PLATFORM_THICKNESS
            for i, (x, y, z) in enumerate(level["targets"]):
                bx, by, bz = melee_to_blender(x, y, z)
                _make_empty("target.%d" % i, (bx, by, bz))
            for i, (cx, cy, cz, w, d) in enumerate(level["platforms"]):
                bx, by, bz = melee_to_blender(cx, cy, cz)
                # Rebuild the cube centered half a thickness below the top
                # surface so exporting it yields the same `cy` back.
                center = (bx, by, bz - t / 2.0)
                _make_platform("platform.%d" % i, center, (w, d, t))

            self.report(
                {"INFO"},
                "Imported %d targets, %d platforms" % (len(level["targets"]), len(level["platforms"])),
            )
            return {"FINISHED"}

    class EXPORT_OT_melee_tt(bpy.types.Operator, ExportHelper):
        """Export the current scene as a Melee Break-the-Targets .tt level."""

        bl_idname = "export_scene.melee_tt"
        bl_label = "Export Melee Break-the-Targets (.tt)"
        bl_options = {"REGISTER", "UNDO"}
        filename_ext = ".tt"

        def execute(self, context):
            scene = context.scene
            targets, platforms = gather_level(scene)
            if not targets and not platforms:
                self.report(
                    {"ERROR"},
                    "Nothing to export: no 'target*' objects or platform cubes "
                    "found (set a 'melee_role' custom property, or name objects "
                    "'target*'/'platform*').",
                )
                return {"CANCELLED"}

            character = normalize_character(scene.melee_character or "mario")
            if resolve_ckind(character) is None:
                self.report(
                    {"WARNING"},
                    "Character '%s' is not a known ckind/name; the port loader "
                    "will skip this level." % character,
                )

            level = {
                "name": scene.melee_name or scene.name,
                "character": character,
                "targets": targets,
                "platforms": platforms,
            }
            text = serialize_tt(level)

            try:
                with open(self.filepath, "w", newline="\n", encoding="utf-8") as f:
                    f.write(text)
            except OSError as e:
                self.report({"ERROR"}, "Could not write %s: %s" % (self.filepath, e))
                return {"CANCELLED"}

            self.report(
                {"INFO"},
                "Exported %d targets, %d platforms to %s" % (len(targets), len(platforms), self.filepath),
            )
            return {"FINISHED"}

    class MELEE_PT_tt_panel(bpy.types.Panel):
        """View3D sidebar panel showing level identity and object counts."""

        bl_label = "Melee TT"
        bl_idname = "MELEE_PT_melee_tt"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Melee TT"

        def draw(self, context):
            layout = self.layout
            scene = context.scene
            layout.prop(scene, "melee_character")
            layout.prop(scene, "melee_name")
            nt, np = count_level_objects(scene)
            layout.label(text="Targets: %d" % nt)
            layout.label(text="Platforms: %d" % np)
            layout.separator()
            layout.operator(EXPORT_OT_melee_tt.bl_idname, text="Export .tt")
            layout.operator(IMPORT_OT_melee_tt.bl_idname, text="Import .tt")

    def menu_func_import(self, context):
        self.layout.operator(IMPORT_OT_melee_tt.bl_idname, text="Melee Break-the-Targets (.tt)")

    def menu_func_export(self, context):
        self.layout.operator(EXPORT_OT_melee_tt.bl_idname, text="Melee Break-the-Targets (.tt)")

    def register():
        bpy.utils.register_class(IMPORT_OT_melee_tt)
        bpy.utils.register_class(EXPORT_OT_melee_tt)
        bpy.utils.register_class(MELEE_PT_tt_panel)
        bpy.types.Scene.melee_character = StringProperty(
            name="Character", description="Character (ckind or name, e.g. 'mario')", default="mario"
        )
        bpy.types.Scene.melee_name = StringProperty(
            name="Level Name", description="Level name (falls back to the scene name)", default=""
        )
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    def unregister():
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        del bpy.types.Scene.melee_character
        del bpy.types.Scene.melee_name
        bpy.utils.unregister_class(MELEE_PT_tt_panel)
        bpy.utils.unregister_class(EXPORT_OT_melee_tt)
        bpy.utils.unregister_class(IMPORT_OT_melee_tt)

else:  # pragma: no cover - Blender-only entry points stubbed for the pure import

    def register():
        pass

    def unregister():
        pass


if __name__ == "__main__":
    # Blender runs this module as a script to install it in the text editor.
    if _HAS_BPY:
        register()
