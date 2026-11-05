"""Bounded general modeling language. No character recipes, Python evaluation or paths."""
import math
from scene_forge.schema import obj, enum, number, vector, validate, SceneError

NAME = {'type': 'string', 'pattern': r'[A-Za-z][A-Za-z0-9_.-]{0,63}', 'maxLength': 64}
POS = vector(-10, 10)
ROT = vector(-360, 360)
SCALE = vector(.05, 4)
FACE = {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 1023}, 'minItems': 3, 'maxItems': 32}
VARIANTS = [
    obj({'op': enum('mesh'), 'id': NAME,
         'vertices': {'type': 'array', 'items': POS, 'minItems': 3, 'maxItems': 1024},
         'faces': {'type': 'array', 'items': FACE, 'minItems': 1, 'maxItems': 1024}}),
    obj({'op': enum('primitive'), 'id': NAME, 'kind': enum('box', 'sphere', 'cylinder'),
         'location': POS, 'dimensions': vector(.001, 10), 'rotation_degrees': ROT}),
    obj({'op': enum('loft'), 'id': NAME, 'location': POS,
         'rings': {'type': 'array', 'minItems': 2, 'maxItems': 24,
                   'items': obj({'z': number(-5, 5), 'radius_x': number(.001, 3),
                                 'radius_y': number(.001, 3), 'center_y': number(-3, 3)})}}),
    obj({'op': enum('modifier'), 'target': NAME, 'kind': enum('bevel', 'subdivide', 'solidify'), 'value': number(.001, 2)}),
    obj({'op': enum('material'), 'target': NAME, 'color': {'type': 'string', 'pattern': '#[0-9a-fA-F]{6}'},
         'metallic': number(0, 1), 'roughness': number(.05, 1)}),
    obj({'op': enum('transform'), 'target': NAME, 'translation': POS, 'scale': SCALE, 'rotation_degrees': ROT}),
    obj({'op': enum('duplicate'), 'source': NAME, 'id': NAME, 'translation': POS}),
    obj({'op': enum('deform'), 'target': NAME, 'center': POS, 'radius': vector(.005, 3),
         'translation': vector(-.2, .2), 'scale': vector(.5, 1.5)}),
]
SCHEMA = obj({'title': {'type': 'string', 'minLength': 1, 'maxLength': 100},
              'operations': {'type': 'array', 'items': {'anyOf': VARIANTS}, 'maxItems': 48},
              'unsupported_requests': {'type': 'array', 'items': {'type': 'string', 'maxLength': 200}, 'maxItems': 12}})


def validate_plan(plan, existing=()):
    validate(plan, SCHEMA, 'modeling_plan')
    if plan['unsupported_requests']:
        raise SceneError('Unsupported modeling request: ' + '; '.join(plan['unsupported_requests']))
    if not plan['operations']:
        raise SceneError('Supported plan must contain operations')
    known, modified, new_count = set(existing), {}, 0
    for operation in plan['operations']:
        kind = operation['op']
        if 'target' in operation and operation['target'] not in known:
            raise SceneError('Unknown target: ' + operation['target'])
        if kind == 'duplicate' and operation['source'] not in known:
            raise SceneError('Unknown source: ' + operation['source'])
        if 'id' in operation:
            name = operation['id']
            if name in known:
                raise SceneError('Object ID already exists: ' + name)
            known.add(name)
            new_count += 1
            if new_count > 24:
                raise SceneError('At most 24 new objects per plan')
        if kind == 'mesh':
            vertices = operation['vertices']
            for face in operation['faces']:
                if max(face) >= len(vertices) or len(set(face)) != len(face):
                    raise SceneError('Invalid mesh face indices')
                # Nonzero fan-triangle area; Blender cannot repair a degenerate design silently.
                a = vertices[face[0]]
                area = 0.
                for i in range(1, len(face) - 1):
                    u = [vertices[face[i]][j] - a[j] for j in range(3)]
                    v = [vertices[face[i + 1]][j] - a[j] for j in range(3)]
                    cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                    area += math.sqrt(sum(n*n for n in cross))
                if area < 1e-10:
                    raise SceneError('Degenerate mesh face')
        elif kind in ('deform', 'transform'):
            identity = operation['translation'] == [0, 0, 0] and operation['scale'] == [1, 1, 1]
            if identity and (kind == 'deform' or operation['rotation_degrees'] == [0, 0, 0]):
                raise SceneError('No-op edit: zero translation and identity scale/rotation change nothing. Choose a nonidentity operation that satisfies the request.')
        elif kind == 'loft':
            heights = [r['z'] for r in operation['rings']]
            if any(b <= a for a, b in zip(heights, heights[1:])):
                raise SceneError('Loft ring z values must strictly increase')
        elif kind == 'modifier':
            key = operation['target'], operation['kind']
            if key in modified:
                raise SceneError('Only one modifier of each kind per target per plan')
            modified[key] = True
            if operation['kind'] == 'subdivide' and operation['value'] not in (1, 2):
                raise SceneError('Subdivision must be 1 or 2')
            if operation['kind'] in ('bevel', 'solidify') and operation['value'] > .1:
                raise SceneError('Bevel/solidify limit is 0.1 m')
    return plan


def deform_points(points, operation):
    """Ellipsoidal smooth proportional edit in object-local coordinates."""
    result, changed = [], 0
    center, radius = operation['center'], operation['radius']
    for p in points:
        distance = math.sqrt(sum(((p[i] - center[i]) / radius[i]) ** 2 for i in range(3)))
        weight = (1 - distance * distance) ** 2 if distance < 1 else 0
        q = [p[i] + weight * ((p[i] - center[i]) * (operation['scale'][i] - 1) + operation['translation'][i]) for i in range(3)]
        changed += math.dist(p, q) > 1e-9
        result.append(q)
    return result, changed


def loft_geometry(rings, segments=32):
    vertices = [(r['radius_x'] * math.cos(2 * math.pi * i / segments),
                 r['center_y'] + r['radius_y'] * math.sin(2 * math.pi * i / segments), r['z'])
                for r in rings for i in range(segments)]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(segments):
            a, b = j * segments + i, j * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    faces += [tuple(range(segments - 1, -1, -1)), tuple(range((len(rings)-1)*segments, len(rings)*segments))]
    return vertices, faces
