"""Typed model intent -> bounded Blender operation. No prompt heuristics or repairs."""
from decimal import Decimal

from scene_forge.schema import obj, enum, number, vector, validate
from modeling_lab.operations import NAME
from modeling_training.vfx_ops import validate_operation

REGION = {'center': vector(-10, 10), 'radius': vector(.005, 3)}
SCHEMAS = {
    'local_translate': obj(dict(intent=enum('local_translate'), target=NAME, axis=enum('X', 'Y', 'Z'),
                                amount=number(-10000, 10000), unit=enum('m', 'cm', 'mm'), **REGION)),
    'object_translate': obj(dict(intent=enum('object_translate'), target=NAME, axis=enum('X', 'Y', 'Z'),
                                 amount=number(-10000, 10000), unit=enum('m', 'cm', 'mm'))),
    'local_scale': obj(dict(intent=enum('local_scale'), target=NAME, axis=enum('X', 'Y', 'Z'),
                            percent=number(-50, 50), **REGION)),
    'light_power': obj(dict(intent=enum('light_power'), target=NAME, amount=number(.001, 5000), unit=enum('W', 'kW'))),
    'camera_lens': obj(dict(intent=enum('camera_lens'), target=NAME, amount=number(.1, 200), unit=enum('mm', 'cm'))),
    'surface': obj(dict(intent=enum('surface'), target=NAME, roughness=number(0, 100), metallic=number(0, 100), unit=enum('percent', 'fraction'))),
    'glow': obj(dict(intent=enum('glow'), target=NAME, threshold=number(0, 10), strength=number(0, 100), unit=enum('percent', 'fraction'))),
    'unsupported': obj(dict(intent=enum('unsupported'), feature=enum('new_geometry', 'animation', 'simulation', 'multi_step', 'ambiguous'))),
}

SYSTEM = '''Return exactly ONE flat JSON object, no outer wrapper, prose or code. Examples of the exact formats:
{"intent":"local_translate","target":"Mesh","axis":"X","amount":2,"unit":"cm","center":[0,0,1.2],"radius":[0.3,0.2,0.1]}
{"intent":"object_translate","target":"Mesh","axis":"X","amount":2,"unit":"cm"}
{"intent":"local_scale","target":"Mesh","axis":"X","percent":8,"center":[0,0,1.2],"radius":[0.3,0.2,0.1]}
{"intent":"light_power","target":"Key","amount":500,"unit":"W"}
{"intent":"camera_lens","target":"Cam","amount":55,"unit":"mm"}
{"intent":"surface","target":"Mesh","roughness":25,"metallic":80,"unit":"percent"}
{"intent":"glow","target":"Glow","threshold":1.2,"strength":45,"unit":"percent"}
{"intent":"unsupported","feature":"simulation"}
All numbers and arrays are JSON values, never quoted strings. Choose ONE format only.
Copy the target name exactly. axis is X,Y,Z. center/radius are [X,Y,Z] in metres.
Copy the signed amount AND its original unit; do not convert units.
Movement units: m,cm,mm. Light: W,kW. Lens: mm,cm. Surface/glow: percent or fraction. Copy values without arithmetic.
local_translate moves vertices inside the specified ellipsoid with smooth falloff; the object stays fixed.
object_translate moves the entire object; its local vertices stay fixed. Do not confuse what is preserved with what moves.
local_scale changes only the named axis inside the ellipsoid: positive percent increases, negative reduces.
All other axes/properties stay unchanged; never emit scale or rotation fields for translation.
Only existing-element single edits are supported. Otherwise unsupported feature is new_geometry,animation,simulation,multi_step,ambiguous.
No other fields, prose or Python.'''


class UnsupportedIntent(ValueError):
    pass


def decimal_value(value, multiplier):
    return float(Decimal(str(value))*Decimal(multiplier))


def validate_intent(frame, existing):
    if not isinstance(frame, dict) or frame.get('intent') not in SCHEMAS:
        raise ValueError('Unknown intent kind')
    validate(frame, SCHEMAS[frame['intent']], 'intent')
    if frame['intent'] != 'unsupported' and frame['target'] not in existing:
        raise ValueError('Unknown intent target: '+frame['target'])
    return frame


def compile_intent(frame, existing):
    """Copy declared intent literally. Wrong scope stays wrong and must fail evaluation."""
    validate_intent(frame, existing)
    kind = frame['intent']
    if kind == 'unsupported':
        raise UnsupportedIntent('Unsupported existing-element edit: '+frame['feature'])
    target = frame['target']
    if kind in ('local_translate', 'object_translate', 'local_scale'):
        axis = 'XYZ'.index(frame['axis'])
        translation, scale = [0, 0, 0], [1, 1, 1]
        if kind == 'local_scale':
            scale[axis] = float(Decimal(1)+Decimal(str(frame['percent']))/100)
        else:
            translation[axis] = decimal_value(frame['amount'], {'m': '1', 'cm': '.01', 'mm': '.001'}[frame['unit']])
        if kind == 'object_translate':
            result = dict(op='transform', target=target, translation=translation, scale=scale, rotation_degrees=[0, 0, 0])
        else:
            result = dict(op='deform', target=target, center=frame['center'].copy(), radius=frame['radius'].copy(), translation=translation, scale=scale)
    elif kind == 'light_power':
        result = dict(op=kind, target=target, watts=decimal_value(frame['amount'], '1000' if frame['unit'] == 'kW' else '1'))
    elif kind == 'camera_lens':
        result = dict(op=kind, target=target, millimeters=decimal_value(frame['amount'], '10' if frame['unit'] == 'cm' else '1'))
    elif kind == 'surface':
        multiplier = '.01' if frame['unit'] == 'percent' else '1'
        result = dict(op=kind, target=target, roughness=decimal_value(frame['roughness'], multiplier), metallic=decimal_value(frame['metallic'], multiplier))
    else:
        result = dict(op='glow', target=target, threshold=frame['threshold'], strength=decimal_value(frame['strength'], '.01' if frame['unit'] == 'percent' else '1'))
    validate_operation(result, existing)
    return result


def canonical_intent(operation):
    """Review-only canonical labels for old regression cases. Not sent to the model."""
    op = operation
    kind = op['op']
    if kind in ('deform', 'transform'):
        if kind == 'transform' and (op['scale'] != [1, 1, 1] or op['rotation_degrees'] != [0, 0, 0]):
            raise ValueError('Regression operation is outside this intent protocol')
        scaling = op['scale'] != [1, 1, 1]
        values = [v-1 for v in op['scale']] if scaling else op['translation']
        axes = [i for i, value in enumerate(values) if abs(value) > 1e-9]
        if len(axes) != 1 or (scaling and op['translation'] != [0, 0, 0]):
            raise ValueError('Only one-axis existing-element edits can be labeled')
        axis = axes[0]
        frame = dict(intent='local_scale' if scaling else ('local_translate' if kind == 'deform' else 'object_translate'), target=op['target'], axis='XYZ'[axis])
        if scaling:
            frame['percent'] = float((Decimal(str(op['scale'][axis]))-1)*100)
        else:
            frame.update(amount=op['translation'][axis], unit='m')
        if kind == 'deform':
            frame.update(center=op['center'].copy(), radius=op['radius'].copy())
    elif kind in ('light_power', 'camera_lens'):
        frame = dict(intent=kind, target=op['target'], amount=op['watts'] if kind == 'light_power' else op['millimeters'], unit='W' if kind == 'light_power' else 'mm')
    elif kind == 'surface':
        frame = dict(intent=kind, target=op['target'], roughness=op['roughness'], metallic=op['metallic'], unit='fraction')
    elif kind == 'glow':
        frame = dict(intent=kind, target=op['target'], threshold=op['threshold'], strength=op['strength'], unit='fraction')
    else:
        raise ValueError('Unsupported canonical regression operation')
    compile_intent(frame, [op['target']])
    return frame
