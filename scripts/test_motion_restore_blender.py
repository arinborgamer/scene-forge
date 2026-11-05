"""Regression: keyframe edits must affect the mesh and restore after FCurve.update().

Run in background Blender with -- --input a_prepared_motion.blend --output new_report.json.
The real import verifier is the test seam; no mocked Blender/RNA objects are used.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modeling_lab.import_motion import main

if '--verify' not in sys.argv:
    sys.argv.append('--verify')
main()
