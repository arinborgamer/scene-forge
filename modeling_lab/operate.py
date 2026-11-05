"""Run local Qwen's modeling operations, recording exact inputs, outputs and provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from scene_forge.planner import request_json
from modeling_lab.operations import SCHEMA, validate_plan

SYSTEM = """You are a Blender modeling operator. Return only JSON matching the supplied schema.
Design geometry by choosing an ordered sequence of generic mesh operations. There are
NO character, head, clothing or object presets. There is no automatic anatomical generator.
World: metres, Z up, front is NEGATIVE Y, character's left is POSITIVE X.
Available operations:
mesh: id, explicit vertices [[x,y,z],...], faces [[indices...],...]. Coordinates local at world origin.
primitive: id, kind box/sphere/cylinder, location, dimensions (FULL sizes along XYZ), rotation_degrees.
cylinder's length is Z before rotation. sphere dimensions define an ellipsoid.
loft: id, location, rings of z/radius_x/radius_y/center_y. Produces capped elliptical cross
sections joined with quad faces. Rings are LOCAL coordinates, strictly increasing z.
Loft radius is half width/depth. Choose a detailed profile when the shape calls for it.
modifier: target, kind bevel/subdivide/solidify, value. bevel width or solidify thickness in
metres <=0.1; subdivide integer 1 or 2. Only one of each modifier per target per plan.
material: target, color #RRGGBB, metallic 0..1, roughness .05..1.
transform: target, translation (relative in metres), scale (multipliers, 1 unchanged),
rotation_degrees (relative). Whole-object edit, NOT a localized sculpt.
duplicate: source, new id, translation (relative). Copies the mesh and modifiers.
deform: target, center, radius [rx,ry,rz], translation, scale [sx,sy,sz]. This moves actual
control vertices inside an ellipsoid in OBJECT-LOCAL space using smooth falloff to zero
at the boundary. Points outside the ellipsoid are EXACTLY unchanged. Scale is around
center and blended by falloff: it is not a uniform region scale. Use a tightly bounded
radius to avoid affecting unwanted regions. Preserves faces and weights, but does not
refit bones or provide anatomical corrections. It cannot edit meshes with shape keys.
Objects must be created before using them. Existing input IDs may be targeted directly.
mesh, primitive, loft and duplicate each CREATE a complete object: choose exactly ONE
creation operation per ID. Never create placeholder mesh objects before loft/primitive.
For curved forms prefer loft or sphere; boxes/cylinders are already complete meshes.
Use explicit mesh only for custom polygons: vertices must span a surface, not a line;
face indices are zero-based and must refer to vertices that actually exist.
For widening/narrowing about a center, use scale and ZERO translation. Translation
moves both sides in the same direction; it does not symmetrically widen a region.
Use material operations when colors or metal are requested. Dimensions alone do not
assign a material. Check all requested parts and colors before returning.
Use exact IDs requested by the user. For a revision emit ONLY the needed operations.
Never rebuild an existing asset to make a local change. Preserve unmentioned geometry,
materials, positions and rigs. Cannot change bones, animate, download, write scripts,
run code, access files, generate realistic textures, invent learned anatomy or guarantee
photorealism. Report requested unsupported features in unsupported_requests; otherwise [].
No hair generation, sculpt-detail synthesis, remeshing or automatic rig creation exists.
Generic mechanical/stylized mesh construction, assembly, materials and local edits ARE
supported. Existing detailed meshes can be edited. Do not report negated or unrequested
features as unsupported. Up to 24 new objects, 48 operations. Prefer concise plans.
Default camera and review lighting are added by the host, not by your plan.
Never claim artistic quality from valid geometry alone."""


def planner_messages(prompt, inventory):
    # The format field constrains sampling; it does not replace model-visible instructions.
    return [{'role': 'system', 'content': SYSTEM + '\nRequired JSON schema:\n' + json.dumps(SCHEMA, separators=(',', ':'))},
            {'role': 'user', 'content': json.dumps({'request': prompt, 'existing_scene': inventory})}]


def run_blender(executable, script_args, log):
    command = [executable, '--background', '--factory-startup', '--disable-autoexec', '--threads', '4',
               '--python-exit-code', '1', '--python', str(Path(__file__).with_name('operation_blender.py')),
               '--', *script_args]
    with Path(log).open('w') as file:
        result = subprocess.run(command, stdout=file, stderr=subprocess.STDOUT, check=False, timeout=900)
    if result.returncode:
        raise RuntimeError('Blender operation failed; inspect ' + str(log))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--input')
    parser.add_argument('--editable', nargs='*', default=[])
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default='qwen3:4b')
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11434')
    parser.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--model-timeout', type=int, default=1200)
    args = parser.parse_args()
    if not args.prompt.strip() or len(args.prompt) > 6000:
        parser.error('Prompt length must be 1 to 6000 characters')
    if args.model_timeout < 1 or args.model_timeout > 3600:
        parser.error('Model timeout must be between 1 and 3600 seconds')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    source = Path(args.input).resolve() if args.input else None
    source_args = ['--input', str(source)] if source else []
    if args.editable:
        source_args += ['--editable', *args.editable]
    request = {'prompt': args.prompt, 'input': str(source) if source else None, 'editable_objects': args.editable,
               'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest() if source else None,
               'weights_updated': False, 'requested_model': args.model}
    (output / 'request.json').write_text(json.dumps(request, indent=2))
    try:
        if source:
            run_blender(args.blender, [*source_args, '--inventory', str(output / 'inventory.json')], output / 'inventory.log')
            inventory = json.loads((output / 'inventory.json').read_text())
        else:
            inventory = {'objects': [], 'rigs': {}}
        installed = request_json(args.ollama_url, '/api/tags', timeout=10).get('models', [])
        model = next((m for m in installed if m['name'] == args.model), None)
        if model is None:
            raise ValueError('Requested model is not installed; no model downloads were started')
        messages = planner_messages(args.prompt, inventory)
        options = {'temperature': 0, 'num_ctx': 8192, 'num_predict': 4096}
        context = {'messages': messages.copy(), 'schema': SCHEMA, 'model_metadata': model,
                   'inference_options': options, 'timeout_seconds': args.model_timeout,
                   'source_hashes': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in ('operations.py', 'operation_blender.py', 'operate.py')}}
        (output / 'planner_context.json').write_text(json.dumps(context, indent=2))
        errors = []
        for attempt in range(1, 3):
            response = request_json(args.ollama_url, '/api/chat', {
                'model': args.model, 'messages': messages, 'format': SCHEMA, 'stream': False,
                'think': False, 'keep_alive': 0,
                'options': options}, timeout=args.model_timeout)
            (output / f'planner_attempt_{attempt}.json').write_text(json.dumps(response, indent=2))
            raw = response.get('message', {}).get('content', '')
            try:
                if response.get('done_reason') == 'length':
                    raise ValueError('Planner output truncated')
                plan = validate_plan(json.loads(raw), [o['id'] for o in inventory['objects']])
                break
            except ValueError as exc:
                errors.append(str(exc))
                if 'Unsupported modeling request:' in str(exc) or attempt == 2:
                    raise
                messages += [{'role': 'assistant', 'content': raw},
                             {'role': 'user', 'content': 'Fix this validation error only; preserve the request: ' + str(exc)}]
        (output / 'plan.json').write_text(json.dumps(plan, indent=2))
        flags = [*source_args, '--plan', str(output / 'plan.json'), '--output', str(output / 'scene')]
        if args.render:
            flags.append('--render')
        run_blender(args.blender, flags, output / 'blender.log')
        run_blender(args.blender, ['--input', str(output / 'scene/model.blend'), '--verify', str(output / 'reopen.json')], output / 'reopen.log')
        if source and hashlib.sha256(source.read_bytes()).hexdigest() != request['input_sha256']:
            raise RuntimeError('Original source changed')
        candidate = {'review_status': 'pending', 'approved_for_training': False,
                     'messages': context['messages'] + [{'role': 'assistant', 'content': json.dumps(plan)}],
                     'plan_sha256': hashlib.sha256((output / 'plan.json').read_bytes()).hexdigest(),
                     'model': model, 'structural_checks_passed': True, 'semantic_checks_passed': None,
                     'rights_review': 'pending', 'artistic_review': 'pending'}
        (output / 'training_candidate.json').write_text(json.dumps(candidate, indent=2))
        status = {'status': 'completed', 'meaning': 'Execution and reload passed; request satisfaction requires separate evaluation',
                  'attempts': attempt, 'validation_errors': errors, 'elapsed_seconds': time.perf_counter() - start,
                  'blend': str(output / 'scene/model.blend')}
    except Exception as exc:
        (output / 'status.json').write_text(json.dumps({'status': 'failed', 'error': str(exc), 'elapsed_seconds': time.perf_counter() - start}, indent=2))
        raise
    (output / 'status.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main()
