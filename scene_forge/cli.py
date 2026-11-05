import argparse
import json
from pathlib import Path
import shutil
import sys

from .jobs import discover_blender, execute_job
from .planner import models
from .schema import SceneError, validate_scene


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scene Forge: local AI planning and editable Blender scenes")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Check Blender, FFmpeg, and installed local models")
    doctor.add_argument("--blender")
    doctor.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    generate = sub.add_parser("generate", help="Generate a scene from text with local Ollama")
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--model", default="qwen3:4b")
    generate.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    generate.add_argument("--revise", help="Previous scene.json to revise into a NEW job")
    demo = sub.add_parser("demo", help="Run a deterministic scene without AI (integration check)")
    demo.add_argument('--style', choices=('blocky', 'organic'), default='blocky')
    build = sub.add_parser("build", help="Build a saved scene.json without an AI request")
    build.add_argument("--plan", required=True)
    for command in (generate, demo, build):
        command.add_argument("--output", default="output", help="Parent folder for unique job folders")
        command.add_argument("--job-dir", help=argparse.SUPPRESS)
        command.add_argument("--blender")
        command.add_argument("--preview", choices=("none", "stills", "video"), default="stills")
    validate_cmd = sub.add_parser("validate", help="Validate a scene.json without Blender")
    validate_cmd.add_argument("plan")
    dataset = sub.add_parser('export-dataset', help='Export explicitly reviewed AI planning examples; no training or uploads')
    dataset.add_argument('--jobs', default='output')
    dataset.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg")}
            try:
                result["blender"] = discover_blender(args.blender)
            except SceneError as exc:
                result["blender_error"] = str(exc)
            try:
                result["local_models"] = models(args.ollama_url)
            except SceneError as exc:
                result["ollama_error"] = str(exc)
            print(json.dumps(result, indent=2))
            return int("blender_error" in result or "ollama_error" in result)
        if args.command == "validate":
            validate_scene(json.loads(Path(args.plan).read_text(encoding="utf-8")))
            print("Valid scene")
            return 0
        if args.command == 'export-dataset':
            from .dataset import export_dataset
            print(json.dumps(export_dataset(args.jobs, args.output), indent=2))
            return 0
        kwargs = dict(output_root=args.output, blender=args.blender, preview=args.preview, job_dir=args.job_dir)
        if args.command == "generate":
            kwargs.update(prompt=args.prompt, model=args.model, base_url=args.ollama_url,
                          previous=json.loads(Path(args.revise).read_text(encoding="utf-8")) if args.revise else None)
        elif args.command == "demo":
            if args.style == 'organic':
                kwargs['provider'] = 'organic_demo'
            else:
                kwargs["provider"] = "demo"
        else:
            kwargs["scene"] = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            kwargs['source_plan'] = args.plan
        execute_job(**kwargs)
        return 0
    except (SceneError, OSError, ValueError, InterruptedError) as exc:
        print(f"Scene Forge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
