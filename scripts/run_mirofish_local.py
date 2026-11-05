"""Bounded local-only MiroFish run with its own Ollama process and fresh evidence."""
import argparse,json,os,subprocess,time,urllib.request,socket
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--timeout',type=int,default=1200);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];run=Path(a.run).resolve()
    if (run/'reddit_simulation.db').exists() or (run/'simulation.log').exists():
        raise RuntimeError('Use a fresh run directory; existing simulation evidence must be preserved')
    source=json.loads((run/'source.json').read_text());script=Path(source['runner'])
    import hashlib
    assert hashlib.sha256(script.read_bytes()).hexdigest()==source['runner_sha256']
    executable=root/'.venv-mirofish311/Scripts/python.exe'
    ollama=Path(os.environ['LOCALAPPDATA'])/'Programs/Ollama/ollama.exe'
    base='http://127.0.0.1:11435'
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',11435))==0:raise RuntimeError('Private simulation port is already in use')
    env=os.environ.copy();env.update({'OLLAMA_HOST':'127.0.0.1:11435','OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1','OLLAMA_CONTEXT_LENGTH':'8192',
      'LLM_BASE_URL':base+'/v1','OPENAI_BASE_URL':base+'/v1','OPENAI_API_BASE_URL':base+'/v1','LLM_API_KEY':'ollama-local','OPENAI_API_KEY':'ollama-local','LLM_MODEL_NAME':'qwen3:4b','MODEL_TIMEOUT':'240','PYTHONUNBUFFERED':'1','PYTHONUTF8':'1','DO_NOT_TRACK':'1'})
    for name in ('LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY'):env.pop(name,None)
    (run/'log').mkdir(exist_ok=True)
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with (run/'ollama.log').open('w',encoding='utf-8') as log:
        server=subprocess.Popen([str(ollama),'serve'],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        try:
            for _ in range(30):
                try:
                    with urllib.request.urlopen(base+'/api/tags',timeout=2) as response:tags=json.load(response)
                    break
                except OSError:time.sleep(1)
            else:raise RuntimeError('Private Ollama service did not start')
            if not any(m['name']=='qwen3:4b' for m in tags['models']):raise RuntimeError('Existing local qwen3:4b weights are missing; no implicit model download')
            started=time.monotonic()
            with (run/'simulation.log').open('w',encoding='utf-8') as output:
                try:
                    result=subprocess.run([str(executable),'-u',str(script),'--config',str(run/'simulation_config.json'),'--max-rounds','2','--no-wait'],cwd=run,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=a.timeout,creationflags=flags)
                    status={'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,'acceptance':'Requires database/action-log inspection; exit zero alone is not success'}
                except subprocess.TimeoutExpired:
                    status={'exit_code':None,'timed_out':True,'elapsed_seconds':time.monotonic()-started,'acceptance':'Incomplete; inspect retained logs'}
            (run/'process-result.json').write_text(json.dumps(status,indent=2),encoding='utf-8');print(json.dumps(status),flush=True)
        finally:
            if server.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill.exe','/PID',str(server.pid),'/T','/F'],capture_output=True)
                else:server.terminate()
                server.wait(timeout=20)

if __name__=='__main__':main()
