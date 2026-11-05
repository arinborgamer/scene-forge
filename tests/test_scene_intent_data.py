import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modeling_training.scene_intent_data import verify_manifest,verify_companion


class FrozenSceneDataTests(unittest.TestCase):
    def make(self,root):
        rows=[dict(id='a',prompt='request')]
        (root/'test.jsonl').write_text(json.dumps(rows[0])+'\n')
        (root/'test.json').write_text(json.dumps(rows))
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        manifest=dict(profile='scene_intent',files=dict(test=dict(count=1,
            sha256=sha(root/'test.jsonl'),json_sha256=sha(root/'test.json'))))
        (root/'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_consumed_companion_is_bound_to_frozen_jsonl(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            expected=self.make(root)
            rows,_=verify_companion(root/'test.json',expected)
            self.assertEqual(rows[0]['id'],'a')
            (root/'test.json').write_text(json.dumps([dict(id='changed')]))
            with self.assertRaisesRegex(ValueError,'companion changed'):
                verify_companion(root/'test.json',expected)

    def test_mutating_manifest_cannot_rescue_changed_cases(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            expected=self.make(root)
            changed=json.loads(json.dumps(expected))
            changed['files']['test']['count']=99
            (root/'manifest.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'manifest changed'):
                verify_manifest(root,expected)
