"""Read saved-project geometry metrics without changing or re-saving the project."""
import argparse
import json
from pathlib import Path
import sys
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--project', required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
project=Path(args.project).resolve()
bpy.ops.wm.open_mainfile(filepath=str(project))
scene=bpy.context.scene
body=next(o for o in scene.objects if o.get('forge_role')=='organic_body')
rig=next(o for o in scene.objects if o.get('forge_role')=='actor')
sub=next(m for m in body.modifiers if m.type=='SUBSURF')
old_level=sub.levels
sub.levels=sub.render_levels
bpy.context.view_layer.update()
evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
metrics={'base_vertices':len(body.data.vertices), 'base_faces':len(body.data.polygons),
    'render_skin_faces':len(evaluated.data.polygons), 'render_subdivision_levels':sub.render_levels,
    'rig_bones':len(rig.data.bones),
    'wind_leaf_meshes':sum(o.get('forge_role')=='wind_foliage' for o in scene.objects),
    'saved_render_engine':scene.render.engine, 'saved_fps':scene.render.fps,
    'saved_frame_count':scene.frame_end, 'saved_resolution':[scene.render.resolution_x,scene.render.resolution_y],
    'render_device':scene.get('forge_render_device'),
    'note':'Read-only project inspection; no re-save, no trained model, no artistic-quality score.'}
sub.levels=old_level
(project.parent/'geometry_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print('SAVED_PROJECT_METRICS',json.dumps(metrics),flush=True)
