import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('trimesh') and importlib.util.find_spec('scipy'),
                     'Run reconstruction checks in isolated geometry environment')
class ReconstructionTests(unittest.TestCase):
    def test_declared_axes_scale_and_translation_restore_same_surface(self):
        import numpy as np
        import trimesh
        from geometry_lab.reconstruction_review import evaluate
        box=trimesh.creation.box(extents=(.8,.4,1.8))
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],float)
        candidate=(box.vertices@rotation.T)*.5+np.array([.2,-.3,.7])
        result=evaluate(box.vertices,box.faces,candidate,box.faces,count=8000)
        self.assertLess(result['candidate_to_reference']['mean_mm'],result['independent_same_surface_sampling_floor']['mean_mm']*1.2)
        self.assertAlmostEqual(result['alignment']['uniform_scale'],2.)

    def test_wrong_body_width_is_not_hidden_by_alignment(self):
        import trimesh
        import numpy as np
        from geometry_lab.reconstruction_review import evaluate
        box=trimesh.creation.box(extents=(.8,.4,1.8))
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],float)
        candidate=box.vertices.copy()
        candidate[:,0]*=.2
        candidate=candidate@rotation.T
        result=evaluate(box.vertices,box.faces,candidate,box.faces,count=8000)
        self.assertGreater(result['reference_to_candidate']['p95_mm'],100)
