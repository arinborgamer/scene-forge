import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modeling_training.finetune import adapter_source


class AdapterProvenanceTests(unittest.TestCase):
    def test_local_format_precedence_matches_peft(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'adapter_model.bin').write_bytes(b'legacy')
            self.assertEqual(adapter_source(root), dict(file='adapter_model.bin',
                             sha256=hashlib.sha256(b'legacy').hexdigest()))
            (root/'adapter_model.safetensors').write_bytes(b'safe')
            self.assertEqual(adapter_source(root), dict(file='adapter_model.safetensors',
                             sha256=hashlib.sha256(b'safe').hexdigest()))

    def test_missing_weight_file_fails_explicitly(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'no supported local adapter'):
                adapter_source(temp)


if __name__ == '__main__':
    unittest.main()
