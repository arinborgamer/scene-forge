"""Isolated job folders and subprocess execution; never overwrite a user's .blend."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from .planner import plan
from .schema import SceneError, demo_scene, organic_scene, validate_scene
from .capabilities import UnsupportedRequest, preflight


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def discover_blender(explicit=None):
    candidates = [explicit, os.environ.get("BLENDER_PATH"), shutil.which("blender")]
    if os.name == "nt":
        base = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Blender Foundation"
        candidates += [str(p) for p in sorted(base.glob("Blender */blender.exe"), reverse=True)]
    else:
        candidates += ["/Applications/Blender.app/Contents/MacOS/Blender", "/usr/bin/blender"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise SceneError("Blender was not found. Pass --blender with the path to its executable.")


def new_job(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    folder = root / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    folder.mkdir()
    return folder


def changes(before, after, path="scene"):
    """Reviewable structural changes; never apply a revision to the source project."""
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            result.extend(changes(before.get(key), after.get(key), f"{path}.{key}"))
        return result
    if before == after:
        return []
    return [{"path": path, "before": before, "after": after}]


def run_process(command, folder, timeout=900):
    log_path = folder / "blender.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        began = time.monotonic()
        try:
            while process.poll() is None:
                if (folder / "cancel.request").exists():
                    raise InterruptedError("Job cancelled")
                if time.monotonic() - began > timeout:
                    raise SceneError(f"Blender exceeded its {timeout / 60:g}-minute job limit; see blender.log")
                time.sleep(0.25)
            if process.returncode != 0:
                raise SceneError(f"Blender exited with code {process.returncode}; see {log_path}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def execute_job(output_root="output", *, prompt=None, provider="ollama", model="qwen3:4b",
                base_url="http://127.0.0.1:11434", previous=None, scene=None,
                blender=None, preview="stills", job_dir=None, source_plan=None):
    folder = Path(job_dir).resolve() if job_dir else new_job(output_root)
    if job_dir:
        folder.mkdir(parents=True, exist_ok=False)
    status = {"id": folder.name, "created_at": datetime.now(timezone.utc).isoformat(),
              "state": "created", "message": "Preparing scene", "output": str(folder)}
    def update(state, message):
        status.update(state=state, message=message, updated_at=datetime.now(timezone.utc).isoformat())
        write_json(folder / "status.json", status)
        print(json.dumps({"state": state, "message": message, "output": str(folder)}), flush=True)
    write_json(folder / "request.json", {"prompt": prompt, "provider": 'scene_file' if scene is not None else provider,
                                         "model": model, "preview": preview,
                                         "source_plan": str(Path(source_plan).resolve()) if source_plan else None,
                                         "previous_scene": previous})
    try:
        if scene is None and provider == 'ollama':
            capability = preflight(prompt or '')
            write_json(folder / 'capability_check.json', capability)
            if capability['unsupported']:
                raise UnsupportedRequest(capability['unsupported'])
        executable = discover_blender(blender)
        if scene is not None:
            scene = validate_scene(scene)
            provenance = {"provider": "scene_file", "model": None,
                          "source_plan": str(Path(source_plan).resolve()) if source_plan else None}
        elif provider == "demo":
            scene, provenance = demo_scene(), {"provider": "demo", "model": None}
        elif provider == 'organic_demo':
            scene, provenance = organic_scene(), {'provider': 'demo', 'style': 'organic', 'model': None}
        elif provider == "ollama":
            update("planning", "Local AI is preparing the scene; the first request may take several minutes")
            scene, provenance = plan(prompt or "", model=model, base_url=base_url, previous=previous,
                on_response=lambda event: write_json(folder / f"planner_attempt_{event['attempt']}.json", event))
        else:
            raise SceneError("Unknown planning provider")
        if (folder / "cancel.request").exists():
            raise InterruptedError("Job cancelled")
        write_json(folder / "scene.json", scene)
        write_json(folder / "provenance.json", provenance)
        if scene.get('unsupported_requests'):
            raise UnsupportedRequest([entry['feature'] for entry in scene['unsupported_requests']])
        if previous is not None:
            write_json(folder / "revision_diff.json", changes(previous, scene))
        update("building", "Blender is building the project and rendering requested previews")
        script = Path(__file__).with_name("blender_scene.py")
        command = [executable, "--background", "--factory-startup", "--disable-autoexec",
                   "--threads", "4", "--python-exit-code", "1", "--python", str(script), "--",
                   "--plan", str(folder / "scene.json"), "--output", str(folder), "--preview", preview]
        # Shaded organic previews are much slower than Workbench on small GPUs.
        budget = max(900, int(scene['duration_seconds'] * 12 * 20 + 180)) if scene['style'] == 'organic' and preview == 'video' else 900
        run_process(command, folder, timeout=budget)
        if not (folder / "scene.blend").is_file() or not (folder / "validation.json").is_file():
            raise SceneError("Blender did not produce the required project and validation report")
        report = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
        if not report.get("passed"):
            raise SceneError("Generated scene failed validation; see validation.json")
        if preview != "none" and len(list(folder.glob("preview_*.png"))) != 3:
            raise SceneError("Expected three rendered previews but some are missing")
        warnings = []
        if preview == "video":
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                rate = 12 if scene['style'] == 'organic' else 6
                update("encoding", f"Encoding a {rate} FPS motion preview")
                with (folder / "encoder.log").open("w", encoding="utf-8") as log:
                    result = subprocess.run([ffmpeg, "-y", "-framerate", str(rate), "-i",
                        str(folder / "draft_frames" / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(folder / "motion_preview.mp4")],
                        stdout=log, stderr=subprocess.STDOUT, timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                if result.returncode:
                    raise SceneError("Preview encoding failed; see encoder.log")
            else:
                warnings.append("FFmpeg was not found. Motion preview frames are saved in draft_frames/.")
        status["warnings"] = warnings
        status["artifacts"] = {"blend": str(folder / "scene.blend"), "plan": str(folder / "scene.json"),
                               "validation": str(folder / "validation.json")}
        update("complete", "Editable Blender scene is ready" + (". " + " ".join(warnings) if warnings else ""))
        return folder
    except UnsupportedRequest as exc:
        status['unsupported_requests'] = exc.features
        update('unsupported', str(exc))
        raise
    except InterruptedError as exc:
        update("cancelled", str(exc))
        raise
    except Exception as exc:
        update("failed", str(exc))
        raise
