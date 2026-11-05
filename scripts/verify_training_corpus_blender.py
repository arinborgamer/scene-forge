"""Execute every curriculum target in Blender; does not generate training targets."""
import itertools
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from modeling_lab.operation_blender import execute, mesh_state, make_mesh
from modeling_training.corpus import wrapped, validate_example
from modeling_training.vfx_ops import SCHEMAS,apply_vfx,validate_operation
from modeling_training.vfx_fixture import fixture,observe

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
manifest = json.loads((root/'manifest.json').read_text())
intent_profile = manifest.get('profile') == 'intent'
refusal_count = 0
records = []
for path in sorted(root.glob('*.jsonl')):
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if intent_profile:
            from modeling_training.intent_ops import compile_intent, validate_intent, UnsupportedIntent
            from modeling_training.transfer_review import equivalent
            frame = row['operation']
            existing = [frame['target']] if 'target' in frame else []
            validate_intent(frame, existing)
            if frame['intent'] == 'unsupported':
                try:
                    compile_intent(frame, existing)
                except UnsupportedIntent:
                    records.append({'id':row['id'],'passed':True,'execution':'refused before Blender'})
                    refusal_count += 1
                    continue
                raise ValueError('Unsupported request reached execution')
            compiled = compile_intent(frame, existing)
            assert equivalent(compiled, row['expected_operation']), row['id']
            row = {**row, 'operation': compiled}
        if row['operation']['op'] in SCHEMAS:
            op=row['operation']
            validate_operation(op,[op['target']])
            fixture(op)
            apply_vfx(op)
            observed=observe(op)
            assert all(math.isclose(observed[k],v,abs_tol=1e-5) for k,v in row['facts'].items()), row['id']
            records.append({'id':row['id'],'passed':True,'observed':observed})
            continue
        validate_example(row)
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        op, facts = row['operation'], row['facts']
        editable = []
        if 'target' in op:
            c = facts.get('center', [0, 0, 0])
            r = facts.get('radius', [1, 1, 1])
            points = [[c[i] + signs[i]*r[i]*.25 + (3*r[i] if outside and i == 0 else 0)
                       for i in range(3)] for outside in (False, True)
                      for signs in itertools.product((-1, 1), repeat=3)]
            faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
            faces += [[i+8 for i in f] for f in faces.copy()]
            target = make_mesh(op['target'], points, faces)
            group = target.vertex_groups.new(name='preserved_weight')
            group.add(list(range(16)), .75, 'REPLACE')
            editable = [target.name]
            before = mesh_state(target, True)
        trace = execute(wrapped(op), editable)
        if 'target' in op:
            after = mesh_state(target, True)
            assert before['topology_sha256'] == after['topology_sha256']
            assert before['weights_sha256'] == after['weights_sha256']
            axis = 'XYZ'.index(facts['axis'])
            if op['op'] == 'deform':
                for p, q in zip(before['points'], after['points']):
                    d2 = sum(((p[i]-c[i])/r[i])**2 for i in range(3))
                    weight = max(0, 1-d2)**2 if d2 < 1 else 0
                    expected = p.copy()
                    expected[axis] += weight * ((p[axis]-c[axis])*facts['percent']/100 if facts['mode'] == 'scale' else facts['distance'])
                    assert all(math.isclose(a, b, abs_tol=3e-7) for a, b in zip(q, expected)), row['id']
            else:
                assert before['mesh_sha256'] == after['mesh_sha256']
                assert math.isclose(target.location[axis], facts['distance'], abs_tol=1e-7)
        else:
            target = bpy.data.objects[op['id']]
            assert all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(target.location, facts['location']))
            assert all(math.isclose(a, b, rel_tol=.02, abs_tol=.002) for a, b in zip(target.dimensions, facts['dimensions']))
        records.append({'id': row['id'], 'passed': True})
report = {'passed': True, 'count': len(records), 'cases': records,
          'executed_count':len(records)-refusal_count,'refusal_count':refusal_count,
          'scope': 'Supported targets executed on small geometric fixtures; refusals stopped before Blender. Not artist approval or proof on all rigs'}
if intent_profile:
    from modeling_training import intent_ops
    report['compiler_sha256'] = hashlib.sha256(Path(intent_ops.__file__).read_bytes()).hexdigest()
    assert report['compiler_sha256'] == manifest['compiler_sha256']
with (root/'blender-verification.json').open('x') as file:
    json.dump(report, file, indent=2)
print('CORPUS_BLENDER_PASS', len(records), flush=True)
