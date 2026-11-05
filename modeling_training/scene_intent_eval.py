"""Score scene selection and direction before executing; wrong valid targets stay wrong."""
import json

from modeling_training.scene_intent_ops import validate_intent,compile_intent
from modeling_training.intent_ops import UnsupportedIntent
from modeling_training.transfer_review import equivalent


def score(raw,row):
    result=dict(schema_valid=False,frame_schema_valid=False,intent_exact=False,
                output_protocol='scene_intent_v1')
    try:
        frame=json.loads(raw)
        validate_intent(frame,row['scene'])
        result.update(frame_schema_valid=True,operation=frame,
                      scope_exact=frame['intent']==row['operation']['intent'])
        if frame['intent']=='unsupported':
            result.update(schema_valid=True,compiled_operation=None,
                intent_exact=row['operation']['intent']=='unsupported' and frame['feature']==row['operation']['feature'])
        else:
            actual=compile_intent(frame,row['scene'])
            expected=row.get('expected_operation')
            if expected is None and row['operation']['intent']!='unsupported':
                expected=compile_intent(row['operation'],row['scene'])
            result.update(schema_valid=True,compiled_operation=actual,
                          intent_exact=expected is not None and equivalent(actual,expected))
    except (ValueError,TypeError,KeyError,UnsupportedIntent) as exc:
        result['error']=str(exc)
    return result
