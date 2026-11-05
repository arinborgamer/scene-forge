"""Run using blender --background --python this_file."""
import importlib.util
from pathlib import Path
import bpy

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("scene_forge_extension_test", root / "blender_extension" / "__init__.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.register()
assert bpy.context.window_manager.scene_forge.model == "qwen3:4b"
assert Path(module.python_binary()).is_file()
assert bpy.ops.scene_forge.generate.poll()
module.unregister()
assert not hasattr(bpy.types.WindowManager, "scene_forge")
print("EXTENSION_REGISTER_UNREGISTER_PASS")
