"""Finish the Graphify AST/document pass without any paid model calls."""
import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster,score_all
from graphify.analyze import god_nodes,surprising_connections,suggest_questions
from graphify.report import generate
from graphify.export import to_json
from graphify.diagnostics import diagnose_extraction
from graphify.cache import save_semantic_cache
from graphify.detect import save_manifest

root=Path(__file__).resolve().parents[1];out=root/'graphify-out'
def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
def write(name,data):(out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
ast=read('.graphify_ast.json');sem=read('.graphify_chunk_01.json');detect=read('.graphify_detect.json')
assert isinstance(sem['nodes'],list) and isinstance(sem['edges'],list)
files=(out/'.graphify_uncached.txt').read_text(encoding='utf-8').splitlines()
for path in files:
    actual=len(Path(path).read_text(encoding='utf-8').splitlines())
    if sem.get('coverage',{}).get(path)!=actual:raise ValueError(f'Incomplete semantic coverage: {path}')
for n in sem['nodes']:n['_origin']='semantic'
for e in sem['edges']:e['_origin']='semantic'
save_semantic_cache(sem['nodes'],sem['edges'],sem.get('hyperedges',[]),root=str(root),allowed_source_files=files,prompt_file=r'C:\Users\arinjoy\.codex\skills\graphify\references\extraction-spec.md')
write('.graphify_semantic.json',sem)
nodes={n['id']:n for n in ast['nodes']}
for n in sem['nodes']:nodes.setdefault(n['id'],n)
merged={'nodes':list(nodes.values()),'edges':ast['edges']+sem['edges'],'hyperedges':sem.get('hyperedges',[]),'input_tokens':sem.get('input_tokens',0),'output_tokens':sem.get('output_tokens',0)}
write('.graphify_extract.json',merged)
health=diagnose_extraction(merged,directed=True,root=str(root));write('health.json',health)
G=build_from_json(merged,root=str(root),directed=True)
if G.number_of_nodes()==0:raise ValueError('Empty graph')
communities=cluster(G);cohesion=score_all(G,communities)
# Labels describe inspected cluster anchors; they do not assert new relationships.
anchors=[('check_plan_coverage()', 'Scene Validation'),('operation_blender.py','Mesh Operations'),
 ('blender_scene.py','Scene Construction'),('evaluate_operations.py','Modeling Reviews'),
 ('assets.py','Assets and Shape Models'),('qwen-vfx-corpus-v2: 320 train, 12 validation, 24 test','Training Data and Evidence'),
 ('organic.py','Characters and Foliage'),('finetune.py','Qwen Fine Tuning'),
 ('blender_extension/__init__.py','Blender Extension'),('build_project_graph.py','Project Knowledge Graph'),
 ('Scene Forge local Qwen3:4b scene planner','Animation Workflow Evidence'),('manifest.json','Asset Source Manifest'),
 ('modeling_lab/__init__.py','Shape Experiment Package'),('modeling_training/__init__.py','Training Package'),
 ('scene_forge/__init__.py','Scene Forge Package'),('scene-forge','Project Packaging'),('Run-SceneForge.ps1','Windows Launcher')]
labels={}
for cid,members in communities.items():
    names={G.nodes[n].get('label',n) for n in members}
    labels[cid]=next((name for anchor,name in anchors if anchor in names),'External Library References')
gods=god_nodes(G);surprises=surprising_connections(G,communities);questions=suggest_questions(G,communities,labels)
if not to_json(G,communities,str(out/'graph.json'),community_labels=labels):raise ValueError('Graph shrink refused')
tokens={'input':merged['input_tokens'],'output':merged['output_tokens']}
report=generate(G,communities,cohesion,labels,gods,surprises,detect,tokens,str(root),suggested_questions=questions)
report=report.replace('- Token cost: 0 input · 0 output','- Semantic token usage: unavailable from the agent tool; zero placeholders are not measured usage.')
report+='\n\n## Extraction limitations\n\nExternal import endpoints may be represented without extracted source definitions. See health.json for dangling references, four self-loops and relationships collapsed onto the same directed node pairs. The raw extraction is retained. Labels describe inspected cluster anchors. This graph is a snapshot, not proof that a feature works. DATA_INDEX.md links measured artifact evidence.\n'
(out/'GRAPH_REPORT.md').write_text(report,encoding='utf-8')
write('.graphify_analysis.json',{'communities':{str(k):v for k,v in communities.items()},'cohesion':{str(k):v for k,v in cohesion.items()},'gods':gods,'surprises':surprises,'questions':questions})
write('.graphify_labels.json',{str(k):v for k,v in labels.items()})
save_manifest(detect['files'],root=root)
print(json.dumps({'nodes':G.number_of_nodes(),'edges':G.number_of_edges(),'communities':len(communities),'health':health},default=str))
