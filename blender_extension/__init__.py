"""Scene Forge's Blender panel. Blender API access stays on the main thread."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty

_process = None
_job_dir = None


def python_binary():
    root = Path(bpy.app.binary_path).parent
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    candidates = [root / version / "python" / "bin" / "python.exe",
                  root / version / "python" / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}",
                  root.parent / "Resources" / version / "python" / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}"]
    for path in candidates:
        if path.is_file():
            return str(path)
    raise RuntimeError("Bundled Python executable was not found for this Blender installation")


def poll_job():
    global _process
    if _process is None:
        return None
    props = bpy.context.window_manager.scene_forge
    try:
        path = _job_dir / "status.json"
        if path.is_file():
            status = json.loads(path.read_text(encoding="utf-8"))
            props.status = status["message"]
            props.job_state = status["state"]
    except (OSError, ValueError, KeyError):
        pass
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    if _process.poll() is not None:
        if props.job_state not in ("complete", "failed", "cancelled", "unsupported"):
            props.status = f"Worker exited ({_process.returncode}); inspect the job folder."
            props.job_state = "failed"
        _process = None
        return None
    return 0.75


class FORGE_Properties(bpy.types.PropertyGroup):
    prompt: StringProperty(name="Scene instruction", default="A six-second organic creature portrait with jade skin, long ears, amber eyes, subtle breathing and blinking. Moonlit forest lighting.", maxlen=6000)
    model: StringProperty(name="Local model", default="qwen3:4b")
    output_dir: StringProperty(name="Output folder", subtype="DIR_PATH")
    previous_plan: StringProperty(name="Previous scene JSON", subtype="FILE_PATH", description="Optional: preserve this scene while applying the instruction as a revision")
    preview: EnumProperty(name="Preview", items=[("none", "Project only", "Fastest; save an editable .blend"),
        ("stills", "Three rendered stills", "Three draft Cycles images"),
        ("video", "Stills + motion preview", "Organic: 12 FPS Eevee; blocky: 6 FPS workbench. FFmpeg encodes MP4")], default="stills")
    status: StringProperty(default="Ready. Start Ollama before generating with AI.")
    job_state: StringProperty(default="idle")
    last_job: StringProperty(subtype="DIR_PATH")


class FORGE_OT_generate(bpy.types.Operator):
    bl_idname = "scene_forge.generate"
    bl_label = "Generate with local AI"
    bl_description = "Plan a supported scene with Ollama and build it in a separate Blender process"
    mode: EnumProperty(items=[("ai", "AI", ""), ("demo", "Blocky demo", ""), ("organic_demo", "Organic demo", "")], default="ai")

    @classmethod
    def poll(cls, context):
        return _process is None

    def execute(self, context):
        global _process, _job_dir
        props = context.window_manager.scene_forge
        if self.mode == "ai" and not props.prompt.strip():
            self.report({"ERROR"}, "Enter a scene instruction")
            return {"CANCELLED"}
        try:
            root = Path(bpy.path.abspath(props.output_dir)) if props.output_dir else Path.home() / "Documents" / "Scene Forge"
            root.mkdir(parents=True, exist_ok=True)
            _job_dir = root / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
            command = [python_binary(), "-m", "scene_forge", "generate" if self.mode == "ai" else "demo",
                       "--job-dir", str(_job_dir), "--blender", bpy.app.binary_path, "--preview", props.preview]
            if self.mode == 'organic_demo':
                command += ['--style', 'organic']
            if self.mode == "ai":
                command += ["--prompt", props.prompt, "--model", props.model]
                if props.previous_plan:
                    previous = Path(bpy.path.abspath(props.previous_plan))
                    if not previous.is_file():
                        raise RuntimeError("The previous scene JSON file does not exist")
                    command += ["--revise", str(previous)]
            _process = subprocess.Popen(command, cwd=str(Path(__file__).resolve().parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            props.last_job = str(_job_dir)
            props.job_state = "starting"
            props.status = "Starting a separate worker. Your current scene stays open."
            bpy.app.timers.register(poll_job, first_interval=0.75)
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class FORGE_OT_cancel(bpy.types.Operator):
    bl_idname = "scene_forge.cancel"
    bl_label = "Cancel job"
    bl_description = "Stop during Blender execution, or after the current AI request finishes"

    @classmethod
    def poll(cls, context):
        return _process is not None and _job_dir is not None and _job_dir.is_dir()

    def execute(self, context):
        (_job_dir / "cancel.request").touch()
        context.window_manager.scene_forge.status = "Cancellation requested; an active AI request may finish first."
        return {"FINISHED"}


class FORGE_OT_folder(bpy.types.Operator):
    bl_idname = "scene_forge.folder"
    bl_label = "Show output folder"

    @classmethod
    def poll(cls, context):
        return bool(context.window_manager.scene_forge.last_job)

    def execute(self, context):
        path = context.window_manager.scene_forge.last_job
        if Path(path).is_dir():
            bpy.ops.wm.path_open(filepath=path)
        return {"FINISHED"}


class FORGE_OT_open(bpy.types.Operator):
    bl_idname = "scene_forge.open"
    bl_label = "Open generated project in new window"

    @classmethod
    def poll(cls, context):
        props = context.window_manager.scene_forge
        return props.job_state == "complete" and bool(props.last_job)

    def execute(self, context):
        path = Path(context.window_manager.scene_forge.last_job) / "scene.blend"
        if path.is_file():
            # A new visible Blender window is explicitly requested by this button.
            subprocess.Popen([bpy.app.binary_path, "--disable-autoexec", str(path)])
        return {"FINISHED"}


class FORGE_PT_panel(bpy.types.Panel):
    bl_label = "Scene Forge"
    bl_idname = "FORGE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scene Forge"

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.scene_forge
        layout.label(text="Local AI scene builder", icon="SCENE_DATA")
        layout.label(text="Timed blocky actions / organic greetings")
        column = layout.column()
        column.enabled = _process is None
        column.prop(props, "prompt", text="Instruction")
        column.prop(props, "model")
        column.prop(props, "output_dir")
        column.prop(props, "preview")
        column.prop(props, "previous_plan")
        column.operator("scene_forge.generate", icon="PLAY")
        column.operator("scene_forge.generate", text="Build demo (no AI)", icon="FILE_3D").mode = "demo"
        column.operator("scene_forge.generate", text="Organic demo (no AI)", icon="OUTLINER_OB_ARMATURE").mode = "organic_demo"
        if _process is not None:
            layout.operator("scene_forge.cancel", icon="CANCEL")
        box = layout.box()
        box.label(text=props.job_state.upper())
        # Wrap the status without hiding actionable errors.
        import textwrap
        width = max(24, int(context.region.width / 7))
        for line in textwrap.wrap(props.status, width=width):
            box.label(text=line)
        if props.last_job:
            layout.operator("scene_forge.folder", icon="FILE_FOLDER")
            layout.operator("scene_forge.open", icon="BLENDER")
        layout.separator()
        layout.label(text="AI plans; procedural tools animate.")
        layout.label(text="No model downloads or paid APIs.")


CLASSES = (FORGE_Properties, FORGE_OT_generate, FORGE_OT_cancel, FORGE_OT_folder, FORGE_OT_open, FORGE_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.scene_forge = PointerProperty(type=FORGE_Properties)


def unregister():
    if bpy.app.timers.is_registered(poll_job):
        bpy.app.timers.unregister(poll_job)
    del bpy.types.WindowManager.scene_forge
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
