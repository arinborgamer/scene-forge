"""Prepare fictional customer personas; no predicted adoption or real participants."""
import argparse,json,hashlib,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--bounded',action='store_true');a=p.parse_args()
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    brief=('Scene Forge is an experimental Blender tool-use system. It has a small locally fine-tuned Qwen adapter for bounded single-object edits. '+
           'CGI lighting, camera, surface and compositor controls are under evaluation. Existing geometry and procedural tools supply the scenes; '+
           'it cannot currently create production-ready realistic humans, full movies, general sculpting or reliable arbitrary animation. '+
           'The proposed 200 USD monthly price is an unvalidated idea, not a live offer. No measured customer demand or render cost is available. '+
           'This discussion is a fictional scenario for identifying questions to test with real users, not a business forecast.')
    roles=[('hobby_artist','A hobby Blender artist who values editable files and affordable experimentation. Ask whether existing free tools already solve the problem.'),
           ('freelance_artist','A freelance product-visualization artist who values precise repeatable edits, time saved, client confidentiality and revision control.'),
           ('studio_td','A small studio technical director who needs rig compatibility, batch reproducibility, license provenance, failure reports and integration cost estimates.'),
           ('indie_filmmaker','An indie filmmaker who wants controllable characters and environments but questions claims not backed by an editable unseen-scene demonstration.')]
    profiles=[]
    for i,(name,role) in enumerate(roles):
        profiles.append({'user_id':i,'username':name,'name':name,'bio':role,'persona':role+' '+brief+' Discuss benefits, objections and what evidence would change your view. Do not invent experience using an unavailable feature. All characters are fictional.',
                         'mbti':'unspecified','gender':'unspecified','age':30,'country':'unspecified','karma':0,'created_at':'2026-10-27'})
    config={'simulation_id':'scene_forge_hypothetical_review','llm_model':'qwen3:4b',
            'time_config':{'total_simulation_hours':1,'minutes_per_round':30,'agents_per_hour_min':4,'agents_per_hour_max':4,'peak_hours':[],'off_peak_hours':[],'peak_activity_multiplier':1,'off_peak_activity_multiplier':1},
            'agent_configs':[{'agent_id':i,'active_hours':list(range(24)),'activity_level':1} for i in range(4)],
            'event_config':{'initial_posts':[{'poster_agent_id':0,'content':brief+' What would make this useful to your workflow, and what would stop you from considering it?'}]}}
    for name,value in [('reddit_profiles.json',profiles),('simulation_config.json',config),('scope.json',{'real_customers':False,'predictive_validation':False,'manually_seeded_posts':1,'profiles_authored_by':'Codex','purpose':'Small local MiroFish integration experiment; hypotheses for real interviews'})]:
        (out/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
    repo=Path('output/research-mirofish-offline').resolve();script=repo/'backend/scripts/run_reddit_simulation.py'
    source={'repository':'https://github.com/nikmcfly/MiroFish-Offline','commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'runner_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'runner':str(script)}
    if a.bounded:
        original=script.read_text(encoding='utf-8')
        replacements={
            '_scripts_dir = os.path.dirname(os.path.abspath(__file__))':f'_scripts_dir = {str(script.parent)!r}',
            '        return ModelFactory.create(\n            model_platform=ModelPlatformType.OPENAI,\n            model_type=llm_model,\n        )': '''        from camel.models import OpenAIModel
        class LocalBoundedModel(OpenAIModel):
            @property
            def token_limit(self):
                # CAMEL 0.2.78 otherwise mistakes max_tokens for context capacity.
                return 8192
        return LocalBoundedModel(model_type=llm_model, api_key=llm_api_key,
            url=llm_base_url, timeout=180, max_retries=0,
            model_config_dict={"max_tokens":256,"temperature":0.2,"reasoning_effort":"none"})''',
            'semaphore=30,':'semaphore=1,',
        }
        for old,new in replacements.items():
            if original.count(old)!=1:raise ValueError(f'Upstream patch anchor changed: {old}')
            original=original.replace(old,new)
        patched=out/'run_reddit_bounded.py';patched.write_text(original,encoding='utf-8')
        source.update(upstream_runner=source['runner'],upstream_runner_sha256=source['runner_sha256'],runner=str(patched),runner_sha256=hashlib.sha256(patched.read_bytes()).hexdigest(),local_changes=['One concurrent model request','256 output-token cap separate from 8192 context budget','reasoning_effort none','180-second request timeout without retries','Preserve upstream module import paths'])
    (out/'source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    print(out)

if __name__=='__main__':main()
