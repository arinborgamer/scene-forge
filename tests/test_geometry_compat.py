import os
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from geometry_lab.triposr_compat import local_dino_config, marching_cubes


class GeometryCompatibilityTests(unittest.TestCase):
    def test_pinned_config_does_not_request_remote_files(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'
            path.write_text('{}')
            with patch.dict(os.environ,SCENEFORGE_TRIPOSR_DINO_CONFIG=str(path)):
                self.assertEqual(local_dino_config(repo_id='facebook/dino-vitb16',filename='config.json'),str(path))
                with self.assertRaises(ValueError):
                    local_dino_config(repo_id='other/repo',filename='config.json')

    @unittest.skipUnless(importlib.util.find_spec('skimage') and importlib.util.find_spec('trimesh'),
                         'Run analytical extraction in isolated geometry environment')
    def test_extraction_preserves_asymmetric_axes_and_outward_winding(self):
        import numpy as np
        import torch
        import trimesh
        axes=torch.meshgrid(*(torch.arange(40,dtype=torch.float32) for _ in range(3)),indexing='ij')
        center=[16.,20.,22.]
        radius=[8.,5.,3.]
        field=1-sum(((axes[i]-center[i])/radius[i])**2 for i in range(3))
        vertices,faces=marching_cubes(field,0.)
        # Apply the same final coordinate reversal as upstream's helper.
        actual=vertices.numpy()[:,[2,1,0]]
        mesh=trimesh.Trimesh(vertices=actual,faces=faces.numpy(),process=False)
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_winding_consistent)
        self.assertGreater(mesh.volume,0)
        np.testing.assert_allclose(mesh.bounds,[np.array(center)-radius,np.array(center)+radius],atol=.15)


if __name__=='__main__':
    unittest.main()
