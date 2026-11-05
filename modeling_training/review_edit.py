"""Review saved adapter output against the declared numerical edit and actual geometry."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from modeling_lab.evaluate_operations import evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--job', required=True)
    p.add_argument('--case', default='examples/trained-modeling-review.json')
    args = p.parse_args()
    job = Path(args.job)
    case = json.loads(Path(args.case).read_text())
    result = json.loads((job/'scene/execution.json').read_text())
    checks = evaluate('humanoid_edit', result)
    actual = result['plan']['operations']
    expected = case['expected_operation']
    def same(a, b):
        if isinstance(b, list):
            return isinstance(a, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
        if isinstance(b, (float, int)):
            return isinstance(a, (float, int)) and abs(a-b) < 1e-6
        return a == b
    checks['checks']['declared_operation_exact'] = len(actual) == 1 and actual[0].keys() == expected.keys() and all(same(actual[0][k], v) for k, v in expected.items())
    checks['checks']['fresh_reload_passed'] = json.loads((job/'reopen.json').read_text())['passed']
    request = json.loads((job/'request.json').read_text())
    checks['checks']['input_file_unchanged'] = hashlib.sha256(Path(request['input']).read_bytes()).hexdigest() == request['input_sha256']
    checks['passed'] = all(checks['checks'].values())
    name = case['editable']
    before = result['before'][name]['points']
    after = next(s for s in result['states'] if s['id'] == name)['points']
    distances = [math.dist(p, q) for p, q in zip(before, after)]
    checks['moved_vertices'] = sum(d > 1e-7 for d in distances)
    checks['maximum_displacement_mm'] = max(distances)*1000
    checks['note'] = 'Existing detailed humanoid edited by the trained adapter. Anatomy, topology and skeleton are inherited.'
    with (job/'acceptance.json').open('x') as file:
        json.dump(checks, file, indent=2)
    # A measured geometry plot, not a retouched render: original front projection and
    # actual changed vertices. Orange highlights movement, not a quality score.
    lowx, highx = min(p[0] for p in before), max(p[0] for p in before)
    lowz, highz = min(p[2] for p in before), max(p[2] for p in before)
    scale = min(500/(highx-lowx), 650/(highz-lowz))
    def xy(point):
        return 300 + (point[0]-(lowx+highx)/2)*scale, 710 - (point[2]-lowz)*scale
    marks = []
    for index, (point, distance) in enumerate(zip(after, distances)):
        if distance > 1e-7 or index % 5 == 0:
            x, y = xy(point)
            color = '#ff954f' if distance > 1e-7 else '#64748b'
            marks.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{1.5 if distance > 1e-7 else .7}" fill="{color}"/>')
    text = f'{checks["moved_vertices"]} moved vertices; maximum {checks["maximum_displacement_mm"]:.2f} mm'
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800"><rect width="600" height="800" fill="#111827"/><g font-family="sans-serif" fill="#e2e8f0"><text x="24" y="30" font-size="20">Actual adapter edit: front vertex projection</text><text x="24" y="54" font-size="14">Orange = changed; gray = unchanged sample</text></g>' + ''.join(marks) + f'<text x="24" y="760" font-family="sans-serif" font-size="15" fill="#e2e8f0">{text}</text></svg>'
    (job/'edit-map.svg').write_text(svg)
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
