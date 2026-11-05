"""Evaluate declared model intents before Blender; no model output is repaired."""
import json

from modeling_training.intent_ops import validate_intent, compile_intent
from modeling_training.transfer_review import equivalent


def score(raw, row):
    result = dict(schema_valid=False, frame_schema_valid=False, intent_exact=False,
                  output_protocol='typed_intent_v1')
    try:
        frame = json.loads(raw)
        expected = row['operation']
        existing = [expected['target']] if 'target' in expected else []
        validate_intent(frame, existing)
        result.update(frame_schema_valid=True, operation=frame,
                      scope_exact=frame['intent'] == expected['intent'])
        if frame['intent'] == 'unsupported':
            result.update(schema_valid=True, compiled_operation=None,
                          intent_exact=expected['intent'] == 'unsupported' and frame['feature'] == expected['feature'])
        else:
            actual = compile_intent(frame, existing)
            wanted = row.get('expected_operation')
            if wanted is None and expected['intent'] != 'unsupported':
                wanted = compile_intent(expected, existing)
            result.update(schema_valid=True, compiled_operation=actual,
                          intent_exact=wanted is not None and equivalent(actual, wanted))
    except (ValueError, TypeError, KeyError) as exc:
        result['error'] = str(exc)
    return result
