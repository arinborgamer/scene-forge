"""Prompt -> unchanged Qwen -> validated body controls -> trained mesh -> editable Blender file."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from scene_forge.planner import request_json, models
from modeling_lab.shape_model import CONTROL_NAMES, validate_controls

SYSTEM = """Translate an adult humanoid modeling request into the supported JSON controls.
This is a bounded body-shape interpolation experiment, not unrestricted sculpting.
masculine: 0 feminine source template, 1 masculine source template; default 0.5.
adult_age: 0 younger adult, 1 older adult source template; default 0.3. Never create children.
muscle: 0 low muscularity, 0.5 average, 1 very muscular; athletic about 0.75.
mass: 0 low body mass, 0.5 average, 1 high body mass; moderately lean about 0.35.
height_m: 1.45 to 2.1; default 1.8. Use a requested height exactly.
Output all fields plus unsupported_requests ([] if none).
The output is a bald, adult human anatomy study with a procedural skin shader and a
graphite fitted study suit that is a material region on the body, NOT separate clothing.
A 163-bone skeleton with inherited skin weights includes fingers, toes and face bones.
Supported: variations of adult human build, height, editable quad mesh, that skeleton,
the fixed study suit, front/side/three-quarter/face renders. No animation is generated.
Unsupported: creatures, nonhuman anatomy, specific likeness/identity, arbitrary sculpt
details, hair, garments other than the fixed material study suit, photographs, scars,
tattoos, realistic texture maps, props, motion, speech, guaranteed photorealism.
Report only unsupported features ACTUALLY requested, not generic limitations or negated
features. Do not silently replace a requested unsupported feature with something else.
Never output code, paths or additional keys."""
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": [*CONTROL_NAMES, "height_m", "unsupported_requests"],
          "properties": {**{k: {"type": "number", "minimum": 0, "maximum": 1} for k in CONTROL_NAMES},
                         "height_m": {"type": "number", "minimum": 1.45, "maximum": 2.1},
                         "unsupported_requests": {"type": "array", "items": {"type": "string"}, "maxItems": 12}}}


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != set(SCHEMA['required']):
        raise ValueError('Expected exactly the supported modeling fields')
    if any(isinstance(spec[k], bool) or not isinstance(spec[k], (float, int)) for k in (*CONTROL_NAMES, 'height_m')):
        raise ValueError('Shape controls must be numbers, not booleans or strings')
    validate_controls([spec[k] for k in CONTROL_NAMES])
    if not 1.45 <= spec['height_m'] <= 2.1:
        raise ValueError('Height out of range')
    unsupported = spec['unsupported_requests']
    if not isinstance(unsupported, list) or len(unsupported) > 12 or not all(isinstance(x, str) for x in unsupported):
        raise ValueError('Unsupported requests must be an array of strings')
    if unsupported:
        raise ValueError('Unsupported modeling request: ' + ', '.join(unsupported))
    return spec


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--prompt')
    source.add_argument('--spec')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11434')
    parser.add_argument('--model', default='qwen3:4b')
    parser.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    request = {"prompt": args.prompt, "spec_source": args.spec, "model": args.model if args.prompt else None,
               "checkpoint": str(Path(args.checkpoint).resolve())}
    (output / 'request.json').write_text(json.dumps(request, indent=2))
    try:
        if args.prompt:
            if not 1 <= len(args.prompt.strip()) <= 6000:
                raise ValueError('Prompt length must be 1 to 6000 characters')
            if args.model not in models(args.ollama_url):
                raise ValueError('Requested Ollama model is not installed')
            messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': args.prompt}]
            (output / 'planner_context.json').write_text(json.dumps({'messages': messages, 'schema': SCHEMA}, indent=2))
            response = request_json(args.ollama_url, '/api/chat', {
                'model': args.model, 'messages': messages, 'format': SCHEMA, 'stream': False,
                'think': False, 'keep_alive': 0, 'options': {'temperature': 0, 'num_ctx': 4096, 'num_predict': 500}}, timeout=600)
            (output / 'planner_response.json').write_text(json.dumps(response, indent=2))
            if response.get('done_reason') == 'length':
                raise ValueError('Planner output truncated')
            spec = validate_spec(json.loads(response['message']['content']))
        else:
            spec = validate_spec(json.loads(Path(args.spec).read_text()))
        spec_path = output / 'spec.json'
        spec_path.write_text(json.dumps(spec, indent=2))
        command = [args.blender, '--background', '--factory-startup', '--threads', '4',
                   '--python-exit-code', '1', '--python', str(Path(__file__).with_name('build_blender.py')),
                   '--', '--spec', str(spec_path), '--checkpoint', str(Path(args.checkpoint).resolve()),
                   '--output', str(output / 'scene')]
        if args.no_render:
            command.append('--no-render')
        with (output / 'blender.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            raise RuntimeError('Blender failed; inspect blender.log')
        status = {'status': 'completed', 'elapsed_seconds': time.perf_counter() - start,
                  'blend': str(output / 'scene' / 'humanoid.blend')}
    except Exception as exc:
        status = {'status': 'failed', 'error': str(exc), 'elapsed_seconds': time.perf_counter() - start}
        (output / 'status.json').write_text(json.dumps(status, indent=2))
        raise
    (output / 'status.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main()
