# MiroFish local feasibility and bounded customer experiment

Research completed 27 October 2026. This is a source investigation and proposed run recipe, **not a completed customer simulation**. The parent task owns installation and execution after training. No model calls or package installations were performed by this research task.

## Decision

Use the existing offline fork's **Reddit simulation runner directly**, with a small manually declared scenario and a local Ollama endpoint. This exercises real MiroFish/OASIS code while avoiding the full application's graph-construction and report-generation pipeline. It is a local simulated discussion, not contact with Reddit users or a prediction of customer demand.

| Component | Inspected version | Finding |
|---|---|---|
| MiroFish upstream | `7657031ac01184afe2cb220f5ee3545573b5e843` | Full backend requires Zep Cloud; its config rejects `ZEP_API_URL` overrides. |
| MiroFish Offline | `313fe642853ff9fff05e3ecae2e439886c2d29f4` | Full app substitutes Neo4j/Ollama. Its standalone Reddit runner does not import the app's graph services. |
| CAMEL | `camel-ai==0.2.78` | Accepts custom model-name strings and a configured OpenAI-compatible endpoint. |
| OASIS | `camel-oasis==0.2.5` | Reddit agent generation defaults to an in-process igraph graph; simulation uses SQLite. |

Both inspected MiroFish checkouts contain **AGPL-3.0** license text. CAMEL and OASIS source headers use Apache-2.0. Keep notices and review applicable license obligations before distributing a modified or hosted product; these are separate dependencies, not training data. [Upstream license](https://github.com/666ghj/MiroFish/blob/7657031ac01184afe2cb220f5ee3545573b5e843/LICENSE), [offline fork license](https://github.com/nikmcfly/MiroFish-Offline/blob/313fe642853ff9fff05e3ecae2e439886c2d29f4/LICENSE), [upstream configuration](https://github.com/666ghj/MiroFish/blob/7657031ac01184afe2cb220f5ee3545573b5e843/backend/app/config.py).

## Exact direct-run path

The local script is `output/research-mirofish-offline/backend/scripts/run_reddit_simulation.py`. It imports `python-dotenv`, CAMEL and OASIS, reads adjacent `reddit_profiles.json`, constructs the model, creates the agent graph and SQLite environment, seeds configured posts using `ManualAction`, and runs `LLMAction` for selected agents. It supports `--config`, `--max-rounds` and `--no-wait`. Use a **fresh output directory** for every attempt: the runner deletes an existing simulation database and opens its logs in write mode. This is an upstream behavior, not a recommendation to overwrite evidence. [Pinned runner](https://github.com/nikmcfly/MiroFish-Offline/blob/313fe642853ff9fff05e3ecae2e439886c2d29f4/backend/scripts/run_reddit_simulation.py).

No Neo4j service is needed for that path: `generate_reddit_agent_graph` constructs `AgentGraph()` and the default backend is `igraph`. The Neo4j Python dependency may still need installation because it is imported by OASIS. This does not establish that the complete MiroFish website works without its graph database. [Agent graph](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_agent/agent_graph.py), [Reddit generator](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_agent/agents_generator.py#L518).

### Profiles

`reddit_profiles.json` must be a JSON **array**. The OASIS generator directly reads these keys from each item: `username`, `bio`, `persona`, `mbti`, `gender`, `age`, `country`. It assigns `agent_id` from the **array index**, ignoring a profile's `user_id`. Keep array positions, `agent_configs.agent_id` and seed `poster_agent_id` aligned as 0, 1, 2, 3. For compatibility with MiroFish's own serializer, also include `user_id`, `name`, `karma`, `created_at`. [Generator](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_agent/agents_generator.py#L518), [fork profile serializer](https://github.com/nikmcfly/MiroFish-Offline/blob/313fe642853ff9fff05e3ecae2e439886c2d29f4/backend/app/services/oasis_profile_generator.py#L1081).

Proposed fictional personas: a budget-conscious Blender hobbyist, a freelance animator concerned with revision time, a small-studio technical artist concerned with editable assets and pipeline compatibility, and an independent VFX artist concerned with compositing and cleanup. Their opinions must be identified as simulated. Do not claim demographic fields or MBTI make these agents representative of real customers.

### Minimal two-round configuration

```json
{
  "simulation_id": "scene-forge-hypothesis-smoke",
  "llm_model": "qwen3:4b",
  "time_config": {
    "total_simulation_hours": 1,
    "minutes_per_round": 30,
    "agents_per_hour_min": 4,
    "agents_per_hour_max": 4,
    "peak_activity_multiplier": 1,
    "off_peak_activity_multiplier": 1
  },
  "agent_configs": [
    {"agent_id": 0, "active_hours": [0], "activity_level": 1},
    {"agent_id": 1, "active_hours": [0], "activity_level": 1},
    {"agent_id": 2, "active_hours": [0], "activity_level": 1},
    {"agent_id": 3, "active_hours": [0], "activity_level": 1}
  ],
  "event_config": {
    "initial_posts": [{
      "poster_agent_id": 0,
      "content": "Hypothetical product discussion: Scene Forge is an experimental Blender workflow with narrow trained tool instructions and editable outputs. General cinematic production, realistic character generation and broad VFX automation are not proven. A possible future $200/month subscription is a hypothesis, not a current offer. What evidence and workflow benefits would you need before considering it?"
    }]
  }
}
```

This configuration activates all four agents in both rounds. The default active hours would exclude midnight, and default off-peak scaling could produce zero agents, so those defaults must not be used for this small run. The seed is authored setup content and must be excluded from any count of model-generated statements. [Pinned selection and event logic](https://github.com/nikmcfly/MiroFish-Offline/blob/313fe642853ff9fff05e3ecae2e439886c2d29f4/backend/scripts/run_reddit_simulation.py).

## Local-model compatibility

Set the runner's `LLM_BASE_URL` to `http://127.0.0.1:11434/v1`, `LLM_API_KEY` to a nonsecret dummy value such as `ollama`, and `LLM_MODEL_NAME` to an **already installed** Ollama model. Never leave the endpoint blank: the runner's fallback is an OpenAI model. The script copies these values into the OpenAI client's environment, then calls `ModelFactory.create` with the `OPENAI` platform. That platform name alone does not imply a paid request; the configured URL determines the server. [Runner](https://github.com/nikmcfly/MiroFish-Offline/blob/313fe642853ff9fff05e3ecae2e439886c2d29f4/backend/scripts/run_reddit_simulation.py), [CAMEL OpenAI backend](https://github.com/camel-ai/camel/blob/v0.2.78/camel/models/openai_model.py).

CAMEL 0.2.78 converts unknown model strings to `UnifiedModelType`, so a Qwen name is not rejected by the factory. `UnifiedModelType` uses GPT-4o-mini's token-counting convention as a fallback: this is an approximate counter, not a call to that model and not the true Qwen tokenizer. [Factory](https://github.com/camel-ai/camel/blob/v0.2.78/camel/models/model_factory.py), [type adapter](https://github.com/camel-ai/camel/blob/v0.2.78/camel/types/unified_model_type.py).

**No compatibility patch is proven necessary from the inspected source.** If a bounded local wrapper is needed to control generation, override only model construction to use CAMEL's `OPENAI_COMPATIBLE_MODEL` (or `OLLAMA`) with explicit `url`, dummy `api_key`, timeout, retries and generation limits. Leave the fetched runner unchanged and record the wrapper as integration code. These alternatives accept the same chat-completion/tool interface; valid local tool calls still require runtime verification. [Compatible backend](https://github.com/camel-ai/camel/blob/v0.2.78/camel/models/openai_compatible_model.py), [Ollama backend](https://github.com/camel-ai/camel/blob/v0.2.78/camel/models/ollama_model.py).

For the smallest test, precreate the fresh working directory and its `log` subdirectory, use it as the subprocess working directory, and pass absolute paths to the script and config. OASIS opens relative log files on import. Keep the local model unloaded while Blender/Qwen training owns the GPU. The Reddit recommendation path uses its Reddit ranking function; this recipe does not require the full fork's graph embeddings. [OASIS platform](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_platform/platform.py), [social agent logging](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_agent/agent.py).

## Verification and interpretation

Inspect the database and logs after execution. OASIS catches exceptions inside individual agents and returns them, so a completed loop or exit code zero is insufficient. Confirm four registered users, completed rounds, and **non-seeded** model-selected actions. For a useful discussion, require at least one actual generated post/comment, then report how many participants contributed text. Likes or `DO_NOTHING` do not constitute a written debate. Preserve errors and unsuccessful attempts. [Agent execution](https://github.com/camel-ai/oasis/blob/v0.2.5/oasis/social_agent/agent.py#L116).

Any themes are prompts for real interviews, not evidence of willingness to pay, market size, company success or revenue. Four fictional personas sharing one local model are highly correlated and sensitive to their seed descriptions. The longer product goal needs actual user tests even if this smoke test succeeds.

## REA evidence

The parent task recovered the initially unavailable MCP analysis through `rea-agents@6.4.0` CLI. Retained JSON: `output/mirofish-rea-evidence.json` (UTF-16). Evidence ID: `ev_05bb740ab575c165f9a7491a0837bef9a85179baba4a97d82834584a451442cf`. The supplied result records eight JavaScript files parsed, zero parse failures, and 98 findings. This is static frontend evidence; it neither executes Vue components nor proves Python backend or model behavior. The direct-run recommendation above comes from the separately cited Python source inspection.
# 28 October local retry status

The bounded v3 retry exited zero after 554.969 seconds, but read-only SQLite inspection
found zero comments, one seeded post, four signups and eight refresh actions. Its
`output/mirofish-customer-review-v3/acceptance.json` records failure to produce customer
discussion. Raw completion/tool parsing remains unverified. This simulation has not
validated demand, pricing or the animation product. Further diagnosis is separate from
the current modeling-training milestone.

