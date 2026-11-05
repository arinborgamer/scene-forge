"""Small, bounded scene language. Model responses are data, never Python."""
import copy
import math
import re


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def number(low, high):
    return {"type": "number", "minimum": low, "maximum": high}


def vector(low=-15, high=15):
    return {"type": "array", "items": number(low, high), "minItems": 3, "maxItems": 3}


ID = {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,31}$", "maxLength": 32}
COLOR = {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$", "maxLength": 7}
ACTOR = obj({
    "id": ID, "color": COLOR, "start": vector(), "end": vector(),
    "action": enum("walk", "walk_and_wave", "wave", "idle", "sequence"),
    "walk_until": number(0.2, 0.85),
})
# Optional semantic sculpt controls. Existing scene files remain valid.
MORPHOLOGY = obj({
    "head_width": number(0.8, 1.2), "muzzle_length": number(0.8, 1.2),
    "ear_length": number(0.7, 1.3), "cheek_fullness": number(0.8, 1.2),
    "brow_height": number(-0.06, 0.06),
})
DEFAULT_MORPHOLOGY = {'head_width': 1, 'muzzle_length': 1, 'ear_length': 1,
                      'cheek_fullness': 1, 'brow_height': 0}
ACTOR["properties"]["morphology"] = MORPHOLOGY
STEP = {'anyOf': [
    obj({'action': enum('walk'), 'duration_seconds': number(0.25, 20), 'target': vector()}),
    obj({'action': enum('hold', 'look_at_camera', 'wave'), 'duration_seconds': number(0.25, 20)}),
]}
ACTOR['properties']['sequence'] = {'type': 'array', 'items': STEP, 'minItems': 1, 'maxItems': 8}
PROP = obj({
    "id": ID, "kind": enum("house", "tree", "crystal", "rock", "pillar", "cube", "sphere"),
    "position": vector(), "scale": number(0.2, 3), "color": COLOR,
    "material": enum("matte", "metal", "glass", "emissive"),
})
SCHEMA = obj({
    "schema_version": {"type": "integer", "enum": [1, 2]},
    "title": {"type": "string", "minLength": 1, "maxLength": 100},
    "duration_seconds": number(3, 20),
    "fps": {"type": "integer", "enum": [24, 30]},
    "seed": {"type": "integer", "minimum": 0, "maximum": 999999},
    "style": enum("blocky", "low_poly", "organic"),
    "lighting": enum("golden_hour", "moonlight", "studio"),
    "ground_color": COLOR,
    "camera": enum("dolly", "orbit", "static", "portrait", "full_body"),
    "actors": {"type": "array", "items": ACTOR, "minItems": 1, "maxItems": 2},
    "props": {"type": "array", "items": PROP, "maxItems": 24},
    "limitations": {"type": "array", "items": {"type": "string", "maxLength": 240}, "maxItems": 12},
})
SCHEMA['properties']['unsupported_requests'] = {
    'type': 'array', 'maxItems': 12,
    'description': 'Only unmet features explicitly requested by the user, with exact evidence from their prompt. Otherwise []. General implementation limits belong in limitations.',
    'items': obj({'feature': {'type': 'string', 'minLength': 1, 'maxLength': 240},
                  'request_quote': {'type': 'string', 'minLength': 3, 'maxLength': 240}}),
}

# Revisions contain only changed fields. Entity updates merge by stable ID, not index.
PATCH_SCHEMA = copy.deepcopy(SCHEMA)
PATCH_SCHEMA["required"] = []
for _name in ("actors", "props"):
    PATCH_SCHEMA["properties"][_name]["minItems"] = 0
    PATCH_SCHEMA["properties"][_name]["items"]["required"] = ["id"]
PATCH_SCHEMA['properties']['actors']['items']['properties']['morphology']['required'] = []
PATCH_SCHEMA["properties"]["remove_ids"] = {"type": "array", "items": ID, "maxItems": 24}


class SceneError(ValueError):
    pass


def validate(value, schema=SCHEMA, path="scene"):
    """Validate the supported JSON-schema subset, including finite numbers."""
    if 'anyOf' in schema:
        failures = []
        for variant in schema['anyOf']:
            try:
                return validate(value, variant, path)
            except SceneError as exc:
                failures.append(str(exc))
        raise SceneError(f'{path}: no matching action variant: ' + '; '.join(failures))
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "number": (int, float)}
    if not isinstance(value, types[kind]) or (kind in ("number", "integer") and isinstance(value, bool)):
        raise SceneError(f"{path}: expected {kind}")
    if kind in ("number", "integer"):
        if not math.isfinite(value):
            raise SceneError(f"{path}: must be finite")
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise SceneError(f"{path}: outside allowed range")
    if "const" in schema and value != schema["const"]:
        raise SceneError(f"{path}: expected {schema['const']}")
    if "enum" in schema and value not in schema["enum"]:
        raise SceneError(f"{path}: must be one of {schema['enum']}")
    if kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 10000):
            raise SceneError(f"{path}: invalid length")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise SceneError(f"{path}: invalid format")
    elif kind == "object":
        missing = set(schema.get("required", [])) - value.keys()
        extra = value.keys() - schema["properties"].keys()
        if missing or extra:
            raise SceneError(f"{path}: missing {sorted(missing)}, unknown {sorted(extra)}")
        for key, item in value.items():
            validate(item, schema["properties"][key], f"{path}.{key}")
    elif kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 10000):
            raise SceneError(f"{path}: invalid number of items")
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]")
    return value


def validate_scene(scene):
    validate(scene)
    if scene["style"] == "organic":
        if len(scene["actors"]) != 1 or scene["actors"][0]["action"] not in ("idle", "wave"):
            raise SceneError("Organic characters support one stationary idle or waving actor; walking is not supported")
        if scene["camera"] not in ("portrait", "full_body"):
            raise SceneError("Organic characters require portrait or full_body camera")
        if scene['actors'][0]['action'] == 'wave' and scene['camera'] != 'full_body':
            raise SceneError("Organic waving requires full_body camera so the gesture is visible")
    elif scene["camera"] in ("portrait", "full_body") or any("morphology" in a for a in scene["actors"]):
        raise SceneError("Portrait/full_body cameras and morphology controls require organic style")
    ids = [item["id"] for item in scene["actors"] + scene["props"]]
    if len(ids) != len(set(ids)):
        raise SceneError("Object IDs must be unique")
    for actor in scene["actors"]:
        from .sequences import validate_sequence
        try:
            validate_sequence(actor, scene)
        except ValueError as exc:
            raise SceneError(str(exc)) from exc
        if actor["start"][2] != 0 or actor["end"][2] != 0:
            raise SceneError("Actors must stand on the ground: start/end Z must equal 0")
        distance = math.dist(actor["start"], actor["end"])
        if actor["action"] in ("idle", "wave") and distance > 0.001:
            raise SceneError("Idle/wave actors must have identical start and end positions")
        walk_time = scene["duration_seconds"] * actor["walk_until"]
        if actor['action'] != 'sequence' and distance > walk_time * 2:
            raise SceneError("Walking speed exceeds 2 m/s; shorten the path or extend the duration")
    for prop in scene["props"]:
        if prop["position"][2] < 0:
            raise SceneError("Prop positions must be on or above the ground")
    return copy.deepcopy(scene)


def apply_revision(previous, patch):
    validate(patch, PATCH_SCHEMA, "revision")
    result = validate_scene(previous)
    remove = patch.get("remove_ids", [])
    known = {item["id"] for item in result["actors"] + result["props"]}
    if set(remove) - known:
        raise SceneError("Cannot remove unknown object IDs")
    for key, value in patch.items():
        if key == "remove_ids":
            continue
        if key in ("actors", "props"):
            ids = [item["id"] for item in value]
            if len(ids) != len(set(ids)) or set(ids) & set(remove):
                raise SceneError("Revision contains duplicate or conflicting object updates")
            for update in value:
                existing = next((item for item in result[key] if item["id"] == update["id"]), None)
                if existing is None:
                    result[key].append(copy.deepcopy(update))
                else:
                    merged=copy.deepcopy(update)
                    if 'morphology' in merged:
                        merged['morphology'] = dict(existing.get('morphology', DEFAULT_MORPHOLOGY), **merged['morphology'])
                    if 'action' in merged and merged['action'] != 'sequence':
                        existing.pop('sequence', None)
                    existing.update(merged)
        else:
            result[key] = copy.deepcopy(value)
    for key in ("actors", "props"):
        result[key] = [item for item in result[key] if item["id"] not in remove]
    return validate_scene(result)


def organic_scene():
    return validate_scene({
        "schema_version": 1, "title": "The Verdant Keeper", "duration_seconds": 6,
        "fps": 24, "seed": 73, "style": "organic", "lighting": "moonlight",
        "ground_color": "#152e2a", "camera": "portrait",
        "actors": [{"id": "keeper", "color": "#328b83", "start": [0, 0, 0],
                    "end": [0, 0, 0], "action": "idle", "walk_until": 0.6,
                    "morphology": {"head_width": 1, "muzzle_length": 1,
                                   "ear_length": 1, "cheek_fullness": 1, "brow_height": 0}}],
        "props": [],
        "limitations": ["Organic anatomy is procedurally constructed, not generated by a trained 3D model.",
                        "A bounded original creature design supports facial proportion changes, not arbitrary sculpting.",
                        "Idle performance is procedural; no speech, walking, or learned facial performance."]})


def demo_scene():
    return validate_scene({
        "schema_version": 1, "title": "The Amber Discovery", "duration_seconds": 15,
        "fps": 24, "seed": 17, "style": "blocky", "lighting": "golden_hour",
        "ground_color": "#304945", "camera": "dolly",
        "actors": [{"id": "explorer", "color": "#dc713e", "start": [-3, 0, 0],
                    "end": [1.4, 0, 0], "action": "walk_and_wave", "walk_until": 0.6}],
        "props": [
            {"id": "beacon", "kind": "crystal", "position": [3, 0, 0], "scale": 0.85,
             "color": "#69efdf", "material": "emissive"},
            {"id": "home_west", "kind": "house", "position": [-4, 3.5, 0], "scale": 1,
             "color": "#d2b49b", "material": "matte"},
            {"id": "home_east", "kind": "house", "position": [1, 4, 0], "scale": 1.2,
             "color": "#9baaaa", "material": "matte"},
            {"id": "cedar_west", "kind": "tree", "position": [-6, 1.3, 0], "scale": 1.3,
             "color": "#54765f", "material": "matte"},
            {"id": "cedar_east", "kind": "tree", "position": [5, 3, 0], "scale": 1.4,
             "color": "#54765f", "material": "matte"},
            {"id": "stone", "kind": "rock", "position": [4, -1.4, 0], "scale": 0.5,
             "color": "#829693", "material": "matte"},
        ],
        "limitations": ["Character motion is procedural, not generated by a trained motion model.",
                         "This prototype supports blocky characters and a bounded prop library."],
    })
