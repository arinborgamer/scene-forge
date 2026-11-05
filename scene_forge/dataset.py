"""Export explicitly reviewed local planning examples. Does not train or upload anything."""
import hashlib
import json
from pathlib import Path

from .schema import SceneError, validate_scene


def scene_digest(scene):
    canonical = json.dumps(validate_scene(scene), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def collect_examples(root):
    examples, skipped, seen = [], [], set()
    for folder in sorted(Path(root).iterdir()):
        if not folder.is_dir():
            continue
        try:
            def read(name):
                return json.loads((folder / name).read_text(encoding='utf-8'))
            review = read('review.json')
            if review.get('approved') is not True:
                raise SceneError('Not explicitly approved')
            for name in ('reviewer', 'rights_note', 'quality_notes'):
                if not isinstance(review.get(name), str) or not review[name].strip():
                    raise SceneError('Review must include ' + name)
            if read('status.json').get('state') != 'complete' or read('validation.json').get('passed') is not True:
                raise SceneError('Job must be complete and structurally valid')
            scene = validate_scene(read('scene.json'))
            digest = scene_digest(scene)
            if review.get('scene_sha256') != digest:
                raise SceneError('Review hash does not match current scene')
            provenance = read('provenance.json')
            context = provenance.get('training_context', {})
            if provenance.get('provider') != 'ollama' or context.get('revision') is not False:
                raise SceneError('Only captured AI generation examples are supported; demos and revision patches are excluded')
            messages = context.get('messages')
            if (not isinstance(messages, list) or len(messages) != 2
                or [m.get('role') for m in messages] != ['system', 'user']
                or not all(isinstance(m.get('content'), str) and m['content'] for m in messages)):
                raise SceneError('Original system and user context is missing')
            if digest in seen:
                raise SceneError('Duplicate scene')
            seen.add(digest)
            examples.append({'messages': messages + [{'role': 'assistant', 'content': json.dumps(scene)}],
                'metadata': {'job': folder.name, 'scene_sha256': digest, 'base_model': provenance['model'],
                             'reviewer': review['reviewer'], 'rights_note': review['rights_note'],
                             'quality_notes': review['quality_notes']}})
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            skipped.append({'job': folder.name, 'reason': str(exc)})
    return examples, skipped


def export_dataset(root, destination):
    examples, skipped = collect_examples(root)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwriting of a curated dataset.
    with destination.open('x', encoding='utf-8') as stream:
        for example in examples:
            stream.write(json.dumps(example, ensure_ascii=False) + '\n')
    return {'accepted_examples': len(examples), 'skipped': skipped,
            'output': str(destination.resolve()),
            'note': 'Review candidates only. No training, upload or train/test split performed.'}
