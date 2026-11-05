"""Conservative checks for known requests; not a general language-understanding gate."""
import re


class UnsupportedRequest(ValueError):
    def __init__(self, features):
        self.features = list(features)
        super().__init__('Unsupported request: ' + '; '.join(self.features))


PATTERNS = {
    'sitting': r'\b(?:sit|sits|sitting|seated)\b',
    'chair asset': r'\bchairs?\b',
    'running': r'\brunning\b|\bruns?\s+(?:toward|away|to)\b',
    'jumping': r'\b(?:jump|jumps|jumping)\b',
    'dancing': r'\b(?:dance|dances|dancing)\b',
    'kneeling': r'\b(?:kneel|kneels|kneeling)\b',
    'speech/lip sync': r'\b(?:speaks?|speaking|talks?|talking|lip[- ]?sync)\b',
    'walking': r'\b(?:walk|walks|walking)\b',
    'waving': r'\b(?:wave|waves|waving)\b',
    'pause': r'\b(?:pause|pauses|pausing|wait|waits|waiting)\b|\bstand(?:s|ing)?\s+still\b',
    'camera look': r'\b(?:look\w*|turn\w*)\b[^.!?;\n]{0,55}\bcamera\b',
}
UNSUPPORTED = set(PATTERNS) - {'walking', 'waving', 'camera look', 'pause'}


def requested_features(prompt):
    """Recognize explicit English requests and nearby negation; unknowns remain unknown."""
    found = set()
    for clause in re.split(r'[.!?;,\n]|\b(?:but|then)\b', prompt.lower()):
        for feature, pattern in PATTERNS.items():
            for match in re.finditer(pattern, clause):
                prefix = clause[:match.start()]
                # Bounded heuristic. The model must also report unmet requirements.
                if re.search(r"\b(?:no|not|never|without|don't|do not)\b(?:\s+[\w'-]+){0,4}\s*$", prefix):
                    continue
                found.add(feature)
    return found


def preflight(prompt):
    requested = requested_features(prompt)
    blocked = sorted(requested & UNSUPPORTED)
    return {'recognized_requests': sorted(requested), 'unsupported': blocked,
            'passed': not blocked,
            'scope': 'Known English capability checks only; not complete semantic verification.'}


def check_plan_coverage(prompt, scene):
    """Reject known requested motions omitted by the planner, including on revisions."""
    requested = requested_features(prompt)
    offered = set()
    for actor in scene['actors']:
        actions = {actor['action']}
        actions.update(step['action'] for step in actor.get('sequence', []))
        if actions & {'walk', 'walk_and_wave'}:
            offered.add('walking')
        if actions & {'wave', 'walk_and_wave'}:
            offered.add('waving')
        if 'look_at_camera' in actions:
            offered.add('camera look')
        if actions & {'hold', 'idle'}:
            offered.add('pause')
    missing = sorted((requested - UNSUPPORTED) - offered)
    return {'passed': not missing, 'missing': missing,
            'recognized_requests': sorted(requested), 'planned_motions': sorted(offered),
            'scope': 'Presence checks, not proof of exact timings, actor assignment or all prompt semantics.'}
