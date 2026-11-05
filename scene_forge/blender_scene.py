"""Run only in Blender: deterministic scene construction from validated JSON."""
import argparse
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Quaternion, Vector
from bpy_extras.object_utils import world_to_camera_view

# Blender --python supplies a different import root than python -m.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.schema import validate_scene

MATERIALS = {}


def rgba(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values) + (1,)


def material(name, color, finish="matte"):
    key = (color, finish)
    if key in MATERIALS:
        return MATERIALS[key]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba(color)
    bsdf.inputs["Roughness"].default_value = 0.72
    if finish == "metal":
        bsdf.inputs["Metallic"].default_value = 0.85
        bsdf.inputs["Roughness"].default_value = 0.26
    elif finish == "glass":
        bsdf.inputs["Transmission Weight"].default_value = 1
        bsdf.inputs["Roughness"].default_value = 0.12
        bsdf.inputs["IOR"].default_value = 1.45
    elif finish == "emissive":
        bsdf.inputs["Emission Color"].default_value = rgba(color)
        bsdf.inputs["Emission Strength"].default_value = 3.5
    MATERIALS[key] = mat
    return mat


def tag(obj, identifier, role):
    obj["forge_id"] = identifier
    obj["forge_role"] = role
    return obj


def finish_object(obj, name, mat=None, parent=None):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


def box(name, pos, size, mat, parent=None, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = finish_object(bpy.context.object, name, mat, parent)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def cylinder(name, pos, radius, depth, mat, vertices=12, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=pos)
    return finish_object(bpy.context.object, name, mat, parent)


def mesh(name, vertices, faces, mat, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish_object(obj, name, mat, parent)


def empty(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    return obj


def prop(item, scene):
    identifier = item["id"]
    root = tag(empty(identifier), identifier, "prop")
    root.location = item["position"]
    root.scale = (item["scale"],) * 3
    root["kind"] = item["kind"]
    mat = material(identifier + " material", item["color"], item["material"])
    stone = material("Basalt", "#384a50")
    wood = material("Dark timber", "#45352e")
    glow = material("Warm windows", "#ffc674", "emissive")
    kind = item["kind"]
    if kind == "house":
        box(identifier + " walls", (0, 0, 1.15), (2.4, 1.85, 2.3), mat, root)
        box(identifier + " foundation", (0, 0, 0.12), (2.65, 2.1, 0.24), stone, root)
        roof = material("Terracotta roof", "#783e38")
        mesh(identifier + " roof", [(-1.45, -1.15, 2.3), (1.45, -1.15, 2.3),
             (0, -1.15, 3.4), (-1.45, 1.15, 2.3), (1.45, 1.15, 2.3), (0, 1.15, 3.4)],
             [(0, 2, 1), (3, 4, 5), (0, 3, 5, 2), (1, 2, 5, 4), (0, 1, 4, 3)], roof, root)
        box(identifier + " door", (0, -0.95, 0.65), (0.52, 0.08, 1.3), wood, root)
        for x in (-0.78, 0.78):
            box(identifier + " window frame", (x, -0.96, 1.45), (0.62, 0.13, 0.76), wood, root)
            box(identifier + " window", (x, -1.04, 1.45), (0.47, 0.04, 0.59), glow, root)
            box(identifier + " window bar", (x, -1.07, 1.45), (0.04, 0.04, 0.65), wood, root, 0)
        box(identifier + " beam", (0, -0.96, 2.1), (2.4, 0.12, 0.14), wood, root)
    elif kind == "tree":
        cylinder(identifier + " trunk", (0, 0, 0.8), 0.17, 1.6, wood, parent=root)
        for radius, depth, z in ((1.0, 1.7, 1.8), (0.76, 1.5, 2.5), (0.49, 1.3, 3.1)):
            bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=radius, radius2=0, depth=depth, location=(0, 0, z))
            finish_object(bpy.context.object, identifier + " canopy", mat, root)
    elif kind == "crystal":
        cylinder(identifier + " plinth", (0, 0, 0.17), 0.65, 0.34, stone, parent=root)
        cylinder(identifier + " ring", (0, 0, 0.37), 0.48, 0.12, mat, parent=root)
        vertices = [(0.34 * math.cos(i * math.tau / 6), 0.34 * math.sin(i * math.tau / 6), 0.8) for i in range(6)]
        vertices += [(0, 0, 0.5), (0, 0, 1.8)]
        faces = [(i, (i + 1) % 6, 7) for i in range(6)] + [(i, 6, (i + 1) % 6) for i in range(6)]
        crystal = mesh(identifier + " crystal", vertices, faces, mat, root)
        for f, angle in ((1, 0), (scene.frame_end, math.tau)):
            crystal.rotation_euler.z = angle
            crystal.keyframe_insert("rotation_euler", frame=f)
        if item["material"] == "emissive":
            light = bpy.data.lights.new(identifier + " glow", "POINT")
            light.energy = 65
            light.color = rgba(item["color"])[:3]
            light.shadow_soft_size = 1
            lamp = bpy.data.objects.new(identifier + " glow", light)
            bpy.context.collection.objects.link(lamp)
            lamp.parent = root
            lamp.location = (0, 0, 1.1)
    elif kind == "rock":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.65, location=(0, 0, 0.35))
        rock = finish_object(bpy.context.object, identifier + " rock", mat, root)
        rock.scale = (1.1, 0.8, 0.65)
    elif kind == "pillar":
        cylinder(identifier + " column", (0, 0, 1.1), 0.36, 2.2, mat, parent=root)
        for z in (0.1, 2.2):
            box(identifier + " cap", (0, 0, z), (0.92, 0.92, 0.2), mat, root)
    elif kind == "cube":
        box(identifier + " cube", (0, 0, 0.5), (1, 1, 1), mat, root)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.5, location=(0, 0, 0.5))
        finish_object(bpy.context.object, identifier + " sphere", mat, root)
    return root


def actor(item, scene, style):
    """Actual armature with rigid-weighted mesh parts; motion remains procedural."""
    identifier = item["id"]
    data = bpy.data.armatures.new(identifier + " skeleton")
    rig = tag(bpy.data.objects.new(identifier, data), identifier, "actor")
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    definitions = {
        "root": ((0, 0, 0), (0, 0, 0.3), None),
        "torso": ((0, 0, 1.03), (0, 0, 1.83), "root"),
        "head": ((0, 0, 1.83), (0, 0, 2.43), "torso"),
        "arm_l": ((0, 0.52, 1.75), (0, 0.52, 0.95), "torso"),
        "arm_r": ((0, -0.52, 1.75), (0, -0.52, 0.95), "torso"),
        "leg_l": ((0, 0.2, 1.03), (0, 0.2, 0.18), "root"),
        "leg_r": ((0, -0.2, 1.03), (0, -0.2, 0.18), "root"),
    }
    for name, (head, tail, parent) in definitions.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    cloth = material(identifier + " coat", item["color"])
    dark = material("Charcoal fabric", "#23333e")
    skin = material("Warm porcelain", "#e6b995")
    boots = material("Leather", "#353038")
    pack = material("Explorer backpack", "#79583d")
    bevel = 0.025 if style == "blocky" else 0.085
    pieces = [
        ("torso", "coat", (0, 0, 1.46), (0.46, 0.76, 0.81), cloth),
        ("torso", "belt", (0, 0, 1.12), (0.49, 0.78, 0.1), dark),
        ("head", "face", (0, 0, 2.13), (0.59, 0.6, 0.59), skin),
        ("head", "cap", (-0.02, 0, 2.43), (0.68, 0.71, 0.15), dark),
        ("torso", "backpack", (-0.33, 0, 1.5), (0.26, 0.62, 0.63), pack),
    ]
    for side, y in (("l", 0.52), ("r", -0.52)):
        pieces += [("arm_" + side, "sleeve", (0, y, 1.4), (0.3, 0.28, 0.65), cloth),
                   ("arm_" + side, "hand", (0, y, 1.0), (0.28, 0.26, 0.2), skin)]
    for side, y in (("l", 0.2), ("r", -0.2)):
        pieces += [("leg_" + side, "trousers", (0, y, 0.62), (0.32, 0.32, 0.78), dark),
                   ("leg_" + side, "boot", (0.10, y, 0.13), (0.52, 0.35, 0.25), boots)]
    for y in (-0.15, 0.15):
        pieces += [("head", "eye", (0.303, y, 2.18), (0.025, 0.075, 0.085), dark)]
    for bone, name, pos, size, mat in pieces:
        part = box(identifier + " " + name, pos, size, mat, bevel=bevel)
        part.parent = rig
        group = part.vertex_groups.new(name=bone)
        group.add(list(range(len(part.data.vertices))), 1, "REPLACE")
        modifier = part.modifiers.new("Character skeleton", "ARMATURE")
        modifier.object = rig
    if item['action'] == 'sequence':
        return rig  # Animated after the scene camera exists.
    start, end = Vector(item["start"]), Vector(item["end"])
    delta = end - start
    heading = math.atan2(delta.y, delta.x) if delta.length else 0
    rig.rotation_euler.z = heading
    walk_end = max(2, round(scene.frame_end * item["walk_until"]))
    moving = item["action"] in ("walk", "walk_and_wave") and delta.length > 0.001
    stride_count = max(1, round(delta.length / 0.9))
    for frame in range(1, scene.frame_end + 1):
        t = (frame - 1) / max(1, walk_end - 1)
        u = min(1, t) if moving else 0
        # Smooth short acceleration and deceleration, preserving a mostly steady walk.
        travel = u * u * (3 - 2 * u)
        rig.location = start.lerp(end, travel)
        phase = travel * stride_count * math.tau
        amplitude = math.sin(min(1, u * 8) * math.pi / 2) * math.sin(min(1, (1 - u) * 8) * math.pi / 2) if moving else 0
        rig.location.z = 0.045 * abs(math.sin(phase)) * amplitude
        rig.keyframe_insert("location", frame=frame)
        angles = {"leg_l": 0.38 * math.sin(phase) * amplitude,
                  "leg_r": -0.38 * math.sin(phase) * amplitude,
                  "arm_l": -0.3 * math.sin(phase) * amplitude,
                  "arm_r": 0.3 * math.sin(phase) * amplitude}
        waving = item["action"] == "wave" or (item["action"] == "walk_and_wave" and frame > walk_end)
        for name, angle in angles.items():
            bone = rig.pose.bones[name]
            rest = bone.bone.matrix_local.to_quaternion()
            rotation = Quaternion((0, 1, 0), angle)
            if name == "arm_r" and waving:
                elapsed = (frame - (walk_end if moving else 1)) / scene.render.fps
                blend = min(1, max(0, elapsed / 0.7))
                rotation = Quaternion((1, 0, 0), (-2.3 + 0.22 * math.sin(elapsed * 8)) * blend)
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = rest.inverted() @ rotation @ rest
            bone.keyframe_insert("rotation_quaternion", frame=frame)
    return rig


def light(name, kind, location, energy, color, size=5):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.shape, data.size = "DISK", size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def setup_lighting(mode):
    world = bpy.data.worlds.new("Atmosphere")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.16, 0.23, 0.32, 1)
    background.inputs["Strength"].default_value = 0.25 if mode != "moonlight" else 0.09
    if mode == "golden_hour":
        sun = light("Late afternoon sun", "SUN", (-6, -4, 9), 2.2, (1, 0.72, 0.47))
        sun.data.angle = math.radians(12)
        light("Sky fill", "AREA", (2, -5, 7), 850, (0.58, 0.8, 1), 8)
        light("Warm rim", "AREA", (1, 5, 8), 1200, (1, 0.65, 0.34), 6)
    elif mode == "moonlight":
        light("Moon", "SUN", (-4, 2, 8), 0.8, (0.38, 0.55, 1))
        light("Blue fill", "AREA", (2, -5, 7), 600, (0.36, 0.64, 1), 8)
        light("Moon rim", "AREA", (1, 5, 8), 1000, (0.5, 0.75, 1), 6)
    else:
        light("Softbox key", "AREA", (2, -4, 8), 1800, (1, 0.91, 0.8), 7)
        light("Softbox fill", "AREA", (-5, -2, 5), 1200, (0.72, 0.85, 1), 7)
        light("Softbox rim", "AREA", (1, 6, 7), 2000, (1, 0.8, 0.6), 6)


def camera(spec, scene):
    centers = [(Vector(a["start"]) + Vector(a["end"])) / 2 for a in spec["actors"]]
    center = sum(centers, Vector()) / len(centers)
    center.z = 1.25
    bounds = [Vector(a[point]) for a in spec["actors"] for point in ("start", "end")]
    extent = max((v - Vector((center.x, center.y, 0))).length for v in bounds)
    distance = max(12, 10 + extent * 1.3)
    data = bpy.data.cameras.new("Director camera")
    cam = bpy.data.objects.new("Director camera", data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    data.lens = 42
    data.clip_end = 250
    target = tag(empty("Camera focus"), "camera_focus", "camera_target")
    target.location = center
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    for frame in range(1, scene.frame_end + 1, 3):
        t = (frame - 1) / max(1, scene.frame_end - 1)
        angle = math.radians(-62 + (26 * t if spec["camera"] == "orbit" else 0))
        radius = distance * (1.1 - 0.22 * t if spec["camera"] == "dolly" else 1)
        cam.location = center + Vector((math.cos(angle) * radius, math.sin(angle) * radius, radius * 0.57))
        cam.keyframe_insert("location", frame=frame)
    data.dof.use_dof = False
    return cam


def linear_animation():
    # Blender 5.x stores curves in action slots/layers rather than action.fcurves.
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type != "KEYFRAME":
                    continue
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation = "LINEAR"


def build(spec):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    MATERIALS.clear()
    scene = bpy.context.scene
    scene.timeline_markers.clear()
    scene.name = spec["title"]
    scene.render.fps = spec["fps"]
    scene.frame_start = 1
    scene.frame_end = round(spec["duration_seconds"] * spec["fps"])
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_persistent_data = True
    scene.view_settings.view_transform = "AgX"
    random.seed(spec["seed"])
    ground = material("Moss ground", spec["ground_color"])
    cylinder("Landscape", (0, 0, -0.28), 23, 0.55, ground, vertices=96)
    box("Backdrop floor", (0, 0, -0.65), (200, 200, 0.2), material("Backdrop", "#18262c"), bevel=0)
    # A path of individual editable stones anchors the walking corridor.
    stone = material("Path sandstone", "#8e9685")
    for a in spec["actors"]:
        start, end = Vector(a["start"]), Vector(a["end"])
        if (end - start).length < 0.01:
            continue
        for i in range(17):
            p = start.lerp(end, i / 16)
            for offset in (-0.32, 0.32):
                tile = box("Path stone", (p.x, p.y + offset, 0.018), (0.34, 0.5, 0.035), stone, bevel=0.035)
                tile.rotation_euler.z = random.uniform(-0.08, 0.08)
    for item in spec["props"]:
        prop(item, scene)
    setup_lighting(spec["lighting"])
    if spec["style"] == "organic":
        from scene_forge.organic import create_character, create_set, select_render_device
        rigs = [create_character(item, scene) for item in spec["actors"]]
        create_set(spec, scene, rigs[0])
        select_render_device(scene)
        scene.cycles.samples = 48
    else:
        rigs = [actor(item, scene, spec["style"]) for item in spec["actors"]]
        camera(spec, scene)
        from scene_forge.sequence_motion import animate_sequence
        for rig, item in zip(rigs, spec['actors']):
            if item['action'] == 'sequence':
                animate_sequence(rig, item, spec, scene)
    linear_animation()
    scene["forge_schema_version"] = spec['schema_version']
    scene["forge_motion_provider"] = "procedural"
    text = bpy.data.texts.new("Scene Forge - scene.json")
    text.write(json.dumps(spec, indent=2))
    notes = bpy.data.texts.new("Scene Forge - README")
    notes.write("Generated by Scene Forge 0.4.0. Local AI plans the scene; procedural Blender code builds it.\n"
                "Select an actor armature and use Pose Mode to edit its animation.\n"
                "This is a prototype, not general text-to-movie AI.\n\n"
                "Plan notes below are unverified descriptions, not capability checks.\n"
                + "\n".join(spec["limitations"]))
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    rigs[0].select_set(True)
    bpy.context.view_layer.objects.active = rigs[0]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.shading.type = "MATERIAL"
    return scene, rigs


def inspect_scene(spec, scene, rigs):
    checks = []
    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    check("camera", scene.camera is not None, "A render camera is assigned")
    check("duration", scene.frame_end == round(spec["duration_seconds"] * spec["fps"]), "Timeline matches specification")
    for item in spec["actors"] + spec["props"]:
        check("object:" + item["id"], bpy.data.objects.get(item["id"]) is not None, "Requested object exists")
    for rig, item in zip(rigs, spec["actors"]):
        if item['action'] == 'sequence':
            from scene_forge.sequence_motion import inspect_sequence
            checks.extend(inspect_sequence(rig, item, spec, scene))
        expected = rig.get('expected_bones', 7)
        check("rig:" + rig.name, len(rig.data.bones) == expected, f"{expected} editable skeleton bones")
        for frame, expected in ((1, item["start"]), (scene.frame_end, item["end"])):
            scene.frame_set(frame)
            check(f"position:{rig.name}:{frame}", (rig.location - Vector(expected)).length < 0.01,
                  f"Actual {list(rig.location)}; expected {expected}")
        for frame in (1, scene.frame_end // 2, scene.frame_end):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            depsgraph.update()
            evaluated_camera = scene.camera.evaluated_get(depsgraph)
            heights = (2.05, 2.8, 3.6) if spec['style'] == 'organic' else (0.05, 1.2, 2.5)
            if spec['camera'] == 'full_body':
                heights = (0.05, 1.8, 3.6)
            sample_points = [rig.matrix_world @ Vector((0, 0, z)) for z in heights]
            points = [world_to_camera_view(scene, evaluated_camera, p) for p in sample_points]
            check(f"framing:{rig.name}:{frame}", all(0.02 < p.x < 0.98 and 0.02 < p.y < 0.98 and p.z > 0 for p in points),
                  "Actor centerline fits within the frame; occlusion is not evaluated")
    if spec['style'] == 'organic':
        import bmesh
        bodies = [o for o in scene.objects if o.get('forge_role') == 'organic_body']
        check('organic_body', len(bodies) == 1, 'One editable skin object')
        for body in bodies:
            bm=bmesh.new()
            bm.from_mesh(body.data)
            check('skin_manifold', all(e.is_manifold for e in bm.edges), 'Base skin has no boundary or non-manifold edges')
            remaining=set(bm.verts)
            components=0
            while remaining:
                components+=1
                queue=[remaining.pop()]
                while queue:
                    vertex=queue.pop()
                    for edge in vertex.link_edges:
                        other=edge.other_vert(vertex)
                        if other in remaining:
                            remaining.remove(other)
                            queue.append(other)
            check('skin_connected', components==1, f'Base skin has {components} connected component(s)')
            bm.free()
            check('skin_weights', all(abs(sum(g.weight for g in v.groups)-1)<0.001 for v in body.data.vertices), 'Every skin vertex has normalized weights')
            check('skin_detail', len(body.data.vertices)>5000, 'Base mesh has more than 5,000 editable vertices')
        lids=[o for o in scene.objects if o.type=='MESH' and o.data.shape_keys and o.data.shape_keys.key_blocks.get('Blink')]
        check('blink_controls', len(lids)==4, 'Four eyelid meshes have animated Blink shape keys')
    scene.frame_set(1)
    return {"schema_version": 1, "blender_version": bpy.app.version_string,
            "passed": all(c["passed"] for c in checks), "checks": checks,
            "object_count": len(scene.objects), "frame_count": scene.frame_end,
            "limitations": ["No automatic visual critic is implemented.",
                            "Procedural walking has no contact-aware IK; foot sliding may remain.",
                            "Framing checks do not detect occlusion, collisions, or artistic quality."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", choices=("none", "stills", "video"), default="stills")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    spec = validate_scene(json.loads(Path(args.plan).read_text(encoding="utf-8")))
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene, rigs = build(spec)
    report = inspect_scene(spec, scene, rigs)
    (out / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("Scene checks failed; see validation.json")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
    if args.preview != "none":
        # Drafts favor CPU portability on small GPUs; final .blend retains 960x540 settings.
        organic = spec['style'] == 'organic'
        scene.render.resolution_x, scene.render.resolution_y = (960, 540) if organic else (640, 360)
        scene.cycles.samples = 32 if organic else 8
        for frame in (1, scene.frame_end // 2, scene.frame_end):
            scene.frame_set(frame)
            scene.render.filepath = str(out / f"preview_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
    if args.preview == "video":
        organic = spec['style'] == 'organic'
        scene.render.engine = "BLENDER_EEVEE" if organic else "BLENDER_WORKBENCH"
        if organic:
            scene.eevee.taa_render_samples = 16
        scene.render.resolution_x, scene.render.resolution_y = 640, 360
        scene.cycles.samples = 12
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
        scene.display.shading.background_type = "WORLD"
        frames = out / "draft_frames"
        frames.mkdir(exist_ok=True)
        rate = 12 if organic else 6
        for index in range(round(spec['duration_seconds'] * rate)):
            frame = 1 + index * scene.render.fps / rate
            scene.frame_set(int(frame), subframe=frame-int(frame))
            scene.render.filepath = str(frames / f"{index+1:04d}.png")
            bpy.ops.render.render(write_still=True)
    print("SCENE_FORGE_SUCCESS", flush=True)


if __name__ == "__main__":
    main()
