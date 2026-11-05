import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from geometry_lab.bundle import verify
from geometry_lab.prepare_triposr import CODE,MODEL,DINO,digest,source_files
from geometry_lab import triposr_compat


class GeometryBundleTests(unittest.TestCase):
    def setup_bundle(self,bundle):
        for name in ('source/tsr','model','dino'):
            (bundle/name).mkdir(parents=True,exist_ok=True)
        (bundle/'source/tsr/system.py').write_bytes(b'pinned code')
        (bundle/'source/LICENSE').write_bytes(b'MIT')
        files=[]
        for repo,revision,name,local in [('stabilityai/TripoSR',MODEL,'config.yaml','model/config.yaml'),
                                         ('stabilityai/TripoSR',MODEL,'model.ckpt','model/model.ckpt'),
                                         ('facebook/dino-vitb16',DINO,'config.json','dino/config.json')]:
            p=bundle/local
            p.write_bytes(b'fixture bytes')
            files.append(dict(repo=repo,revision=revision,file=name,path=str(p.resolve()),bytes=p.stat().st_size,sha256=digest(p)))
        manifest=dict(code_revision=CODE,adapted_source=str((bundle/'source').resolve()),files=files,
                      compatibility_sha256=digest(triposr_compat.__file__))
        (bundle/'source-manifest.json').write_text(json.dumps(manifest))
        (bundle/'source-integrity.json').write_text(json.dumps(dict(code_revision=CODE,complete=True,
            provider_manifest_sha256=digest(bundle/'source-manifest.json'),source_files=source_files(bundle/'source'))))

    def test_complete_source_and_exact_local_paths(self):
        with TemporaryDirectory() as temp:
            bundle=Path(temp)/'bundle'
            self.setup_bundle(bundle)
            self.assertEqual(verify(bundle)['code_revision'],CODE)
            (bundle/'source/tsr/system.py').write_bytes(b'modified code')
            with self.assertRaisesRegex(ValueError,'source inventory'):
                verify(bundle)

    def test_copied_bundle_cannot_verify_old_files_and_load_new_ones(self):
        with TemporaryDirectory() as temp:
            bundle,moved=Path(temp)/'bundle',Path(temp)/'moved'
            self.setup_bundle(bundle)
            shutil.copytree(bundle,moved)
            with self.assertRaisesRegex(ValueError,'moved source'):
                verify(moved)
            (bundle/'model/model.ckpt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact changed'):
                verify(bundle)
