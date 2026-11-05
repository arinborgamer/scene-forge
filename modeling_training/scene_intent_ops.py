"""Scene-aware typed edits; scale direction is explicit, never inferred by the compiler."""
import copy
import hashlib
import json
from pathlib import Path

from modeling_training import intent_ops, vfx_ops
from modeling_lab import operations
from scene_forge import schema

SCHEMAS=copy.deepcopy(intent_ops.SCHEMAS)
SCHEMAS['local_scale']=schema.obj(dict(intent=schema.enum('local_scale'),target=operations.NAME,
    axis=schema.enum('X','Y','Z'),direction=schema.enum('increase','decrease'),
    percent=schema.number(.01,50),**intent_ops.REGION))
ELEMENT_TYPES=dict(local_translate='MESH',object_translate='MESH',local_scale='MESH',
                   surface='MESH',light_power='LIGHT',camera_lens='CAMERA',glow='GLARE_NODE')
SYSTEM=intent_ops.SYSTEM.replace('"axis":"X","percent":8,',
    '"axis":"X","direction":"increase","percent":8,').replace(
    'local_scale changes only the named axis inside the ellipsoid: positive percent increases, negative reduces.',
    'local_scale changes only the named axis inside the ellipsoid. direction is increase or decrease; percent is the unsigned positive magnitude. A negative signed scaling percent means decrease with the same unsigned magnitude.')+'''
The user payload contains request and scene. scene lists selectable element names and types.
Match the element named in request to its exact scene name. Another existing element is still a wrong target.
For example a reduction by 9 percent uses "direction":"decrease","percent":9.
Movement amounts retain their original signed values. Emit direction only for local_scale.'''


def compiler_sha256():
    value=hashlib.sha256()
    for path in map(Path,(__file__,intent_ops.__file__,vfx_ops.__file__,operations.__file__,schema.__file__)):
        value.update(path.name.encode())
        value.update(path.read_bytes())
    return value.hexdigest()


def validate_scene(scene):
    if not isinstance(scene,list) or not 1<=len(scene)<=32:
        raise ValueError('A bounded scene catalog is required')
    names=[]
    for item in scene:
        if not isinstance(item,dict) or set(item)!={'name','type'}:
            raise ValueError('Scene entries contain only name and type')
        schema.validate(item['name'],operations.NAME,'scene.name')
        if item['type'] not in ('MESH','LIGHT','CAMERA','GLARE_NODE'):
            raise ValueError('Unsupported scene element type')
        names.append(item['name'])
    if len(set(names))!=len(names):
        raise ValueError('Duplicate scene element names')
    return scene


def prompt(request,scene):
    validate_scene(scene)
    if not isinstance(request,str) or not request.strip():
        raise ValueError('A natural-language request is required')
    return json.dumps(dict(request=request,scene=scene),separators=(',',':'))


def from_legacy(frame):
    result=copy.deepcopy(frame)
    if result['intent']=='local_scale':
        result['direction']='decrease' if result['percent']<0 else 'increase'
        result['percent']=abs(result['percent'])
    return result


def validate_intent(frame,scene):
    validate_scene(scene)
    if not isinstance(frame,dict) or frame.get('intent') not in SCHEMAS:
        raise ValueError('Unknown scene intent')
    schema.validate(frame,SCHEMAS[frame['intent']],'scene_intent')
    if frame['intent']!='unsupported':
        available={e['name']:e['type'] for e in scene}
        if available.get(frame['target'])!=ELEMENT_TYPES[frame['intent']]:
            raise ValueError('Target is absent from the scene or has the wrong type')
    return frame


def compile_intent(frame,scene):
    validate_intent(frame,scene)
    legacy=copy.deepcopy(frame)
    if legacy['intent']=='local_scale':
        direction=legacy.pop('direction')
        legacy['percent']*=1 if direction=='increase' else -1
    # Literal frame compilation. This function never reads the request text.
    return intent_ops.compile_intent(legacy,[e['name'] for e in scene])


def canonical_intent(operation):
    return from_legacy(intent_ops.canonical_intent(operation))
