import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from modeling_training.transfer_review import assess


class TransferReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)/'source.blend'
        self.source.write_bytes(b'preserved source fixture')
        op = {'op': 'deform', 'target': 'Body', 'center': [0, 0, 0], 'radius': [1, 1, 1],
              'translation': [0, 0, 0], 'scale': [1.1, 1, 1]}
        self.case = {'input': str(self.source), 'prompt': 'Grow the local X patch by 10 percent',
                     'editable': 'Body', 'expected_operation': op}
        state = {'id': 'Body', 'points': [[.1, 0, 0], [2, 0, 0]],
                 'topology_sha256': 'topology', 'weights_sha256': 'skin',
                 'materials': ['skin'], 'world_matrix': [1, 0, 0, 1]}
        after = {**copy.deepcopy(state), 'points': [[.109801, 0, 0], [2, 0, 0]]}
        self.execution = {'before': {'Body': state}, 'states': [after],
                          'plan': {'operations': [op]}, 'trace': {'rigs_preserved': True, 'created': []}}
        self.request = {'input': str(self.source), 'prompt': self.case['prompt'],
                        'input_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest()}

    def test_exact_edit_and_preservation_pass(self):
        self.assertTrue(assess(self.case, self.execution, {'passed': True}, self.request)['passed'])
        rounded = copy.deepcopy(self.execution)
        rounded['plan']['operations'][0]['scale'][0] += 1e-9
        self.assertTrue(assess(self.case, rounded, {'passed': True}, self.request)['passed'])

    def test_schema_valid_wrong_edit_and_unmentioned_changes_fail(self):
        for point in [[.09, 0, 0], [.109801, .001, 0]]:
            execution = copy.deepcopy(self.execution)
            execution['states'][0]['points'][0] = point
            self.assertFalse(assess(self.case, execution, {'passed': True}, self.request)['passed'])
        execution = copy.deepcopy(self.execution)
        execution['states'][0]['points'][1][0] += .001
        self.assertFalse(assess(self.case, execution, {'passed': True}, self.request)['passed'])

    def test_weights_rig_source_and_reload_failures_are_visible(self):
        execution = copy.deepcopy(self.execution)
        execution['states'][0]['weights_sha256'] = 'changed'
        execution['trace']['rigs_preserved'] = False
        self.assertFalse(assess(self.case, execution, {'passed': True}, self.request)['passed'])
        self.assertFalse(assess(self.case, self.execution, {'passed': False}, self.request)['passed'])
        self.source.write_bytes(b'changed source')
        self.assertFalse(assess(self.case, self.execution, {'passed': True}, self.request)['passed'])
