"""Local Ollama integration. No paid services, model downloads, or generated code."""
import copy
import json
import urllib.error
import urllib.parse
import urllib.request

from .schema import SCHEMA, PATCH_SCHEMA, SceneError, apply_revision, demo_scene, organic_scene, validate_scene
from .capabilities import UnsupportedRequest, preflight, check_plan_coverage

SYSTEM = """You plan short editable Blender scenes. Output only JSON matching the supplied schema.
Capabilities: blocky or low-poly humanoids; houses, trees, crystals, rocks, pillars, cubes,
spheres; matte, metal, glass and emissive materials; golden_hour, moonlight or studio
lighting; dolly, orbit or static camera. Motion: idle, wave, walk, walk_and_wave.
This is a procedural motion renderer, not a generative motion model.
World: Z up, meters, ground at Z=0. Actors face the path; default forward +X.
Keep actors near the origin and props at least 1.5m away from the walking corridor.
Put buildings and tall trees behind actors (positive Y). Put the focal prop near the end
of the path but not touching the character. Keep start/end Z=0. Walking speed <=2m/s.
For idle or wave use identical start and end positions. walk_until is the fraction of
the scene used for walking. No rain, sculpting, speech, complex actions, facial animation,
photorealism, external assets, or arbitrary VFX are implemented. Explain requested unsupported
features honestly in limitations; never claim they are implemented. Always include the
procedural-motion limitation. IDs must be unique lower-case identifiers. Prefer 4-8 props for
blocky scenes only. An explicit no-extra-props request means props must be [].
Organic character capability: style organic, camera portrait or full_body, exactly one actor
with action idle or wave and identical start/end. Waving REQUIRES full_body camera.
This creates a connected original amphibian-like humanoid,
skin pigment/pores, amber eyes, eyelid blinks, breathing, gentle head movement and a forest
set with branching trees, wind-bent leaves and ferns. Wave raises the right arm with elbow
and wrist articulation, while feet stay planted. Actor color controls SKIN. The organic
forest is built automatically: use props [] unless the user explicitly requests an extra
supported prop. Never substitute primitive tree props for ferns or forest foliage. It is procedural anatomy, not
neural mesh generation or arbitrary sculpting. Optional morphology controls require all five
values: head_width 0.8-1.2, muzzle_length 0.8-1.2, ear_length 0.7-1.3, cheek_fullness 0.8-1.2,
brow_height -0.06 to 0.06. The four multipliers default to 1 and brow_height to 0.
Use organic when explicitly asked for an organic/detailed creature. It cannot walk or talk
yet. Explain unsupported requests. Never use portrait or full_body camera for blocky scenes.
For revisions preserve IDs and all unspecified settings from the supplied previous scene.
Never output scripts, paths, network addresses, commands or extra keys.
TIMED SEQUENCES: For blocky/low_poly characters, use schema_version 2, action sequence,
and an ordered sequence array. Each step has action and duration_seconds.
Actions: walk (requires target [x,y,0]), hold (stay still), look_at_camera (turn HEAD
to the scene camera while body stays still), wave (stationary arm gesture).
Only walk accepts target. Durations must sum exactly to scene duration_seconds.
Walk peak speed is 1.5*distance/duration and must be <=2 m/s. Actor start is the initial
position; actor end equals the last walk target. Include walk_until=0.6 as a legacy field;
it is ignored for sequences. Use a hold step for an explicit pause. Use sequences whenever
ordered actions, timed pauses or head-to-camera looks are requested. Organic sequences
are NOT supported. For a generic character, prefer blocky; never choose organic walking.
Return unsupported_requests: [] only if every requested capability can be represented.
Otherwise list objects with feature and request_quote (an exact excerpt from the user's
request) there. Do NOT list general limitations, example-scene features, or features the
user did not request. A blocky wave THEN walk THEN hold THEN look_at_camera is fully
supported and must have unsupported_requests: []. Camera looks work with static, orbit
and dolly cameras. General caveats belong only in limitations.
Never replace an unsupported asset with a supported
primitive and claim fulfillment. Chairs, sitting, running, jumping and talking are absent.
"""


def local_endpoint(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise SceneError("This free local prototype only connects to Ollama on localhost")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise SceneError("Use a plain local Ollama base URL, e.g. http://127.0.0.1:11434")
    return url.rstrip("/")


def request_json(base_url, route, payload=None, timeout=180):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(local_endpoint(base_url) + route, data=data,
                                     headers={"Content-Type": "application/json"})
    # Local traffic must not be routed through a configured HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", errors="replace")
        raise SceneError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SceneError("Cannot reach local Ollama or generation timed out. Start Ollama and verify the model is installed. " + str(exc)) from exc


def models(base_url="http://127.0.0.1:11434"):
    return [item["name"] for item in request_json(base_url, "/api/tags", timeout=10).get("models", [])]


def plan(prompt, model="qwen3:4b", base_url="http://127.0.0.1:11434", previous=None, on_response=None):
    if not prompt.strip() or len(prompt) > 6000:
        raise SceneError("Prompt must contain between 1 and 6000 characters")
    capability = preflight(prompt)
    if capability['unsupported']:
        raise UnsupportedRequest(capability['unsupported'])
    if model not in models(base_url):
        raise SceneError(f"Local model {model!r} is not installed. Choose an installed model; no downloads were started.")
    schema = copy.deepcopy(PATCH_SCHEMA if previous is not None else SCHEMA)
    schema['required'].append('unsupported_requests')
    content = {"request": prompt, "schema": schema}
    system = SYSTEM
    if previous is not None:
        content["previous_scene"] = validate_scene(previous)
        system += "\nREVISION MODE: Output only a JSON patch containing requested changed fields. Do not repeat unchanged fields. actors and props are partial updates merged by ID; new objects need all fields. Existing morphology controls also merge by field, so a head-width edit can include only morphology.head_width. remove_ids deletes existing IDs. Changing an actor color requires only its id and color. Preserve all other properties."
    else:
        content["example_scene"] = organic_scene() if any(word in prompt.lower() for word in ('organic', 'portrait', 'creature')) else demo_scene()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": json.dumps(content)}]
    errors = []
    for attempt in range(2):
        response = request_json(base_url, "/api/chat", {
            "model": model, "messages": messages, "format": schema, "stream": False,
            "think": False, "keep_alive": 0,
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 2200},
        }, timeout=600)
        raw = response.get("message", {}).get("content", "")
        if on_response:
            on_response({'attempt': attempt+1, 'response': response})
        try:
            if response.get("done_reason") == "length":
                raise SceneError("Model response exceeded token limit")
            data = json.loads(raw)
            # Validate the declared field before trusting it, but do not ask the model
            # to "repair" an explicit report that the user's request is unsupported.
            if not isinstance(data, dict) or 'unsupported_requests' not in data:
                raise SceneError('Model must explicitly report unsupported_requests, or [] if all are supported')
            if 'unsupported_requests' in data:
                from .schema import validate
                validate(data['unsupported_requests'], SCHEMA['properties']['unsupported_requests'])
                if data['unsupported_requests']:
                    for unmet in data['unsupported_requests']:
                        if unmet['request_quote'].strip().casefold() not in prompt.casefold():
                            raise SceneError('Unsupported request report quotes text absent from the user request. Report only actually requested unsupported features; otherwise unsupported_requests must be [].')
                    raise UnsupportedRequest([entry['feature'] for entry in data['unsupported_requests']])
            scene = apply_revision(previous, data) if previous is not None else validate_scene(data)
            coverage = check_plan_coverage(prompt, scene)
            if not coverage['passed']:
                raise SceneError('Requested motion omitted from plan: ' + ', '.join(coverage['missing']))
            required = "Character motion is procedural, not generated by a trained motion model."
            if required not in scene["limitations"]:
                scene["limitations"] = [required] + scene["limitations"][:11]
            return scene, {"provider": "ollama", "model": model, "attempts": attempt + 1,
                           "total_duration_ns": response.get("total_duration"),
                           "eval_count": response.get("eval_count"), "repair_errors": errors,
                           "capability_check": capability, "prompt_coverage": coverage,
                           "training_context": {"messages": messages[:2], "revision": previous is not None}}
        except (json.JSONDecodeError, SceneError) as exc:
            errors.append(str(exc))
            messages.extend([{"role": "assistant", "content": raw[:12000]},
                             {"role": "user", "content": f"Fix this validation error and return JSON matching the requested schema: {exc}"}])
    raise SceneError("Local model could not produce a valid scene: " + "; ".join(errors))
