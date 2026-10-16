"""
scene_cards.py  —  e3d-pod2vid

Animated concept cards for the e3d-pilot interview video: boxes and arrows that appear on the word being spoken.
Each scene has a hand-written spec (SPECS); the engine resolves every cue word to a time using the diarization word
timings, renders 900x506 frames with Pillow, and encodes one mp4 per scene.

  python3 scene_cards.py render [scene ...]     # render cards (all scenes with a spec when none given)
  python3 scene_cards.py check                  # layout sanity (overlaps / out of bounds) and cue resolution
  python3 scene_cards.py still <scene>          # final-state PNG for a scene
"""
import json
import re
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
CARDS = OUT / 'pilot-interview' / 'cards'
CW, CH, FPS = 900, 506, 24

STYLE = {   # fill, border
    'n': ((24, 29, 42), (100, 108, 130)),
    'ai': ((66, 44, 10), (255, 170, 60)),
    'hu': ((12, 48, 70), (120, 220, 255)),
    'ok': ((13, 62, 42), (111, 207, 151)),
    'bad': ((74, 24, 24), (255, 107, 107)),
    'dim': ((20, 24, 34), (70, 76, 94)),
}
BG, PANEL, GRID = (4, 6, 14), (9, 12, 21), (18, 22, 34)
AMBER, TEXT, EDGE = (255, 170, 60), (240, 242, 248), (176, 182, 198)

# node: (id, label, x, y, cue, style)    edge: (from, to, cue, label)   x, y are fractions of the card
SPECS = {
    0: dict(title='The marketing pitch', nodes=[('p', 'PROMPT', .16, .5, 'prompt', 'hu'), ('a', 'AI\n???', .5, .5, 'disappears', 'ai'), ('f', 'Flawless,\nready-to-ship\nfeature', .84, .5, 'flawless', 'ok')],
            edges=[('p', 'a', 'enter', ''), ('a', 'f', 'returns', '10 minutes')]),
    1: dict(title='A binary expectation', nodes=[('b', 'Black box', .5, .5, 'black', 'ai'), ('w', 'Worked\nflawlessly', .2, .2, 'flawlessly', 'ok'), ('h', 'Hallucinated\nwildly', .8, .2, 'hallucinated', 'bad'), ('r', 'Broke the\nrepository', .8, .8, 'broke', 'bad')],
            edges=[('b', 'w', 'flawlessly', ''), ('b', 'h', 'hallucinated', ''), ('h', 'r', 'broke', '')]),
    3: dict(title="Today's mission", nodes=[('e', 'FutCo E3D\necosystem', .5, .28, 'ecosystem', 'ai'), ('m', 'The mechanics', .2, .75, 'mechanics', 'ok'), ('h', 'The usual\nAI hype', .8, .75, 'hype', 'bad')],
            edges=[('e', 'm', 'mechanics', ''), ('e', 'h', 'hype', '')]),
    6: dict(title='From wild to disciplined', nodes=[('w', 'Autonomous agents\nrunning wild', .24, .3, 'autonomous', 'bad'), ('f', 'Rigorous\nfactory floor', .76, .7, 'factory', 'ok')],
            edges=[('w', 'f', 'moving', 'moving away')]),
    7: dict(title='One Mac mini', nodes=[('m', 'Single Mac mini', .22, .3, 'mac', 'hu'), ('s', 'Massive\nserver farm', .78, .3, 'server', 'dim'), ('b', 'Strict boundaries', .3, .78, 'boundaries', 'ok'), ('c', 'Raw compute', .74, .78, 'compute', 'dim')],
            edges=[('b', 'c', 'prioritize', 'over')]),
    10: dict(title='A factory that built its own memory', nodes=[('f', 'AI factory floor', .22, .5, 'factory', 'ai'), ('b', 'E3D Brain:\nits own memory layer', .78, .5, 'memory', 'ok')],
             edges=[('f', 'b', 'debate', 'debate, design, build')]),
    12: dict(title='Separation of powers', nodes=[('d', 'Discover\nopportunity', .13, .42, 'discover', 'ai'), ('s', 'Write the\nspec', .38, .42, 'specification', 'ai'), ('c', 'Write the\ncode', .63, .42, 'code', 'ai'), ('m', 'Approve\nits own merge', .87, .42, 'merge', 'ai'), ('x', 'Never the same AI\nfor all four', .5, .82, 'merge', 'bad')],
             edges=[('d', 's', 'specification', ''), ('s', 'c', 'code', ''), ('c', 'm', 'merge', '')]),
    13: dict(title='Human-gated stages', nodes=[('l', 'LLM', .16, .5, 'llm', 'ai'), ('s', 'Chasing speed', .5, .18, 'speed', 'dim'), ('g', 'Distinct\nhuman gates', .82, .5, 'distinct', 'hu')],
             edges=[('l', 'g', 'forces', 'forced through')]),
    15: dict(title='Jev: semantic duplicate detection', nodes=[('i', 'New AI idea', .18, .22, 'redundant', 'ai'), ('j', 'Jev', .5, .5, 'jev', 'hu'), ('k', 'Keyword search\n"add a caching layer"', .22, .78, 'keyword', 'dim'), ('m', 'Maps the\nactual intent', .82, .5, 'intent', 'ok')],
             edges=[('i', 'j', 'jev', ''), ('j', 'm', 'intent', '')]),
    16: dict(title='Same problem, different words', nodes=[('a', 'Human ticket:\n"implement Redis"', .22, .22, 'redis', 'hu'), ('b', 'AI proposal:\n"add a caching layer"', .22, .78, 'caching', 'ai'), ('g', 'Same architectural\ngap', .78, .5, 'underlying', 'ok'), ('k', 'Keyword search:\nno match', .5, .5, 'keyword', 'bad')],
             edges=[('a', 'g', 'underlying', ''), ('b', 'g', 'overlap', '')]),
    18: dict(title='Gate 1: a human approves', nodes=[('j', 'Idea cleared\nby Jev', .16, .5, 'jev', 'ok'), ('h', 'Human\nreviews', .5, .5, 'human', 'hu'), ('a', 'Approve', .84, .5, 'approve', 'ok'), ('n', 'No code written yet', .5, .85, 'code', 'dim')],
             edges=[('j', 'h', 'human', ''), ('h', 'a', 'approve', '')]),
    19: dict(title='Draft and negotiate', nodes=[('g', 'Human\napproval', .16, .5, 'approval', 'hu'), ('d', 'Draft\nspecification', .5, .5, 'draft', 'ai'), ('n', 'Negotiate\nphase', .84, .5, 'negotiate', 'ai')],
             edges=[('g', 'd', 'draft', ''), ('d', 'n', 'negotiate', '')]),
    21: dict(title="A writers' room", nodes=[('c1', 'Claude', .14, .25, 'claude', 'ai'), ('c2', 'Codex', .38, .25, 'codex', 'ai'), ('c3', 'Grok', .62, .25, 'grok', 'ai'), ('c4', 'Devin', .86, .25, 'devin', 'ai'), ('s', 'Draft spec', .5, .75, 'writers', 'hu')],
             edges=[('c1', 's', 'claude', ''), ('c2', 's', 'codex', ''), ('c3', 's', 'grok', ''), ('c4', 's', 'devin', '')]),
    22: dict(title='The human is the showrunner', nodes=[('t', 'Models debate\nplot holes', .24, .35, 'debating', 'ai'), ('h', 'Human\nshowrunner', .76, .35, 'showrunner', 'hu'), ('g', 'Greenlight before\nanyone builds', .5, .78, 'greenlight', 'ok')],
             edges=[('t', 'h', 'showrunner', ''), ('h', 'g', 'greenlight', '')]),
    24: dict(title='Two rounds of review', nodes=[('r1', 'Round 1\nblind and independent', .26, .28, 'zero', 'ai'), ('r2', 'Round 2\npositions revealed', .74, .28, 'reveals', 'ai'), ('m', 'Defend · Revise\nRebut · Concede', .74, .74, 'defend', 'hu'), ('z', 'Zero groupthink', .26, .74, 'groupthink', 'ok')],
             edges=[('r1', 'r2', 'reveals', ''), ('r2', 'm', 'defend', '')]),
    25: dict(title='When models disagree', nodes=[('d', 'Models\ndisagree', .18, .5, 'disagree', 'ai'), ('b', 'Bounded\nrevision rounds', .56, .22, 'bounded', 'ai'), ('s', 'A single AI:\nwishy-washy middle', .56, .8, 'wishy', 'bad')],
             edges=[('d', 'b', 'hash', 'hash it out')]),
    27: dict(title='Named dissent, then a hard stop', nodes=[('u', 'Unresolved\ndisagreement', .18, .3, 'unresolved', 'ai'), ('h', 'NEEDS HUMAN\nhard stop', .5, .5, 'hard', 'bad'), ('l', 'Dissent logged:\nwhere they diverged', .82, .22, 'logs', 'n'), ('o', 'Operator\ndecides', .82, .78, 'operator', 'hu')],
             edges=[('u', 'h', 'hard', ''), ('h', 'l', 'logs', ''), ('h', 'o', 'operator', '')]),
    28: dict(title='Still no access to main', nodes=[('s', 'Spec refined', .16, .3, 'refined', 'ok'), ('h', 'Human signs off', .5, .3, 'signs', 'hu'), ('m', 'Main codebase:\nstill off limits', .8, .74, 'main', 'bad')],
             edges=[('s', 'h', 'signs', ''), ('h', 'm', 'main', '')]),
    30: dict(title='Branch vs worktree', nodes=[('b', 'Git branch\nsame folder,\nfiles change in place', .25, .4, 'standard', 'dim'), ('w', 'Git worktree\nseparate, isolated\nfolder', .75, .4, 'worktree', 'ok')],
             edges=[('b', 'w', 'worktree', 'vs')]),
    31: dict(title='A sandbox with ceilings', nodes=[('s', 'AI works in one\nisolated directory', .5, .25, 'sandboxed', 'ai'), ('f', 'Hard limit:\nfiles modified', .24, .76, 'files', 'bad'), ('l', 'Hard limit:\nlines changed', .76, .76, 'lines', 'bad')],
             edges=[('s', 'f', 'files', ''), ('s', 'l', 'cut', 'cut off')]),
    33: dict(title='A draft pull request only', nodes=[('a', 'AI', .1, .42, 'restricted', 'ai'), ('d', 'Draft\npull request', .35, .42, 'draft', 'ai'), ('h', 'Human\napprove/merge', .65, .42, 'human', 'hu'), ('m', 'Main\nbranch', .9, .42, 'main', 'ok'), ('s', 'Tied to the exact\nHEAD SHA', .65, .82, 'sha', 'n')],
             edges=[('a', 'd', 'draft', ''), ('d', 'h', 'human', ''), ('h', 'm', 'main', '')]),
    34: dict(title='A new commit voids the approval', nodes=[('t', 'Tuesday\nyou approve', .24, .28, 'tuesday', 'hu'), ('w', 'Wednesday\nAI adds one commit', .76, .28, 'wednesday', 'ai'), ('v', 'Approval voided', .5, .78, 'voided', 'bad')],
             edges=[('t', 'w', 'wednesday', ''), ('w', 'v', 'voided', 'new hash')]),
    36: dict(title='Factories forget', nodes=[('f', 'Factory floor', .2, .5, 'factories', 'ai'), ('v', 'Locked down\nlike a bank vault', .5, .2, 'vault', 'ok'), ('m', 'No memory of\nyesterday\'s mistakes', .8, .75, 'remember', 'bad')],
             edges=[('f', 'm', 'remember', '')]),
    37: dict(title='The agents needed a brain', nodes=[('a', 'E3D agents', .16, .5, 'agents', 'ai'), ('b', 'Persistent\nmemory', .5, .5, 'persistent', 'ok'), ('d', 'A permanent\nfiling cabinet', .84, .5, 'filing', 'bad')],
             edges=[('a', 'b', 'brain', 'needed'), ('b', 'd', 'filing', 'dangerous')]),
    39: dict(title='Debate before a line of code', nodes=[('r', 'AI grading\nits own work', .2, .28, 'violate', 'bad'), ('p', 'E3D Pilot\nfactory floor', .5, .66, 'rigorous', 'ai'), ('b', 'Architecture of\nits own future brain', .8, .28, 'architecture', 'ok'), ('c', 'then code', .5, .92, 'code', 'dim')],
             edges=[('p', 'b', 'architecture', 'debates')]),
    40: dict(title='Two review passes', nodes=[('c', 'Adversarial\ncommittee', .18, .5, 'committee', 'ai'), ('p1', 'Review pass 1', .5, .24, 'massive', 'n'), ('p2', 'Review pass 2', .5, .76, 'passes', 'n'), ('i', 'Real systemic\nissues caught', .84, .5, 'caught', 'ok')],
             edges=[('c', 'p1', 'massive', ''), ('c', 'p2', 'passes', ''), ('p1', 'i', 'caught', ''), ('p2', 'i', 'caught', '')]),
    42: dict(title='Instrument it internally first', nodes=[('x', 'Standalone\nprovenance product', .24, .3, 'standalone', 'bad'), ('i', 'Instrument it inside\nE3D Pilot first', .76, .7, 'internally', 'ok')],
             edges=[('x', 'i', 'instead', 'Claude: instead')]),
    43: dict(title='Dogfood, then extract', nodes=[('d', 'Dogfood\ninternally', .15, .5, 'dogfooding', 'hu'), ('p', 'Prove it answers\nreal attribution\nquestions', .5, .5, 'prove', 'ai'), ('e', 'Extract only if\nexternal demand', .85, .5, 'demand', 'ok')],
             edges=[('d', 'p', 'prove', ''), ('p', 'e', 'demand', '')]),
    45: dict(title='Scope kept to evidence', nodes=[('s', 'Synthesizer records\nthe nuance', .26, .35, 'synthesizer', 'ai'), ('m', 'Memory scope limited\nto what is\nevidence-based', .74, .65, 'constrained', 'ok')],
             edges=[('s', 'm', 'constrained', '')]),
    48: dict(title='Advisory, never authority', nodes=[('m', 'Memory note', .16, .5, 'memory', 'ai'), ('a', 'Advisory', .5, .5, 'advisory', 'ok'), ('x', 'Authority:\nnone', .84, .5, 'authority', 'bad')],
             edges=[('m', 'a', 'advisory', ''), ('a', 'x', 'authority', 'never')]),
    49: dict(title='A standing label on every recall', nodes=[('n', 'Retrieved\nnote', .13, .5, 'pulls', 'ai'), ('l', 'Label:\ncannot authorize', .45, .5, 'label', 'hu'), ('s', 'Spending', .86, .14, 'spending', 'bad'), ('g', 'Signing', .86, .38, 'sign', 'bad'), ('p', 'Publishing', .86, .62, 'publish', 'bad'), ('e', 'External actions', .86, .86, 'external', 'bad')],
             edges=[('n', 'l', 'label', ''), ('l', 's', 'spending', ''), ('l', 'g', 'sign', ''), ('l', 'p', 'publish', ''), ('l', 'e', 'external', '')]),
    51: dict(title='The scary side is writing', nodes=[('l', 'Server logs,\ntranscripts,\njournals', .18, .3, 'logs', 'ai'), ('v', 'Permanent vault\nin plain text', .82, .5, 'permanent', 'n'), ('s', 'Passwords · API keys\n· wallet seeds', .45, .84, 'password', 'bad')],
             edges=[('l', 'v', 'dropping', ''), ('s', 'v', 'seed', 'swept up')]),
    52: dict(title='The secret scrubber', nodes=[('l', 'Information\nleakage', .24, .3, 'leakage', 'bad'), ('s', 'Secret scrubber', .76, .7, 'scrubber', 'ok')],
             edges=[('l', 's', 'scrubber', 'neutralized by')]),
    54: dict(title='Fail hard', nodes=[('w', 'Write\nattempt', .12, .4, 'write', 'ai'), ('s', 'Scrubber', .4, .4, 'detects', 'hu'), ('a', 'Whole write\naborted', .82, .22, 'aborted', 'bad'), ('l', 'Audit log:\ndetector type only', .82, .62, 'audit', 'n'), ('t', 'Strict mode for\nautonomous agents', .4, .84, 'strict', 'ai')],
             edges=[('w', 's', 'detects', ''), ('s', 'a', 'aborted', 'secret found'), ('s', 'l', 'audit', '')]),
    55: dict(title='Secret, or just a jumble?', nodes=[('s', 'Write rejected', .2, .25, 'slams', 'bad'), ('q', 'Real secret\nor random string?', .5, .65, 'difference', 'ai'), ('e', 'Public Ethereum\naddress', .8, .25, 'ethereum', 'hu')],
             edges=[('q', 's', 'slams', ''), ('q', 'e', 'ethereum', '')]),
    57: dict(title='Context-aware heuristics', nodes=[('h', '64-character\nhex string', .18, .35, 'hex', 'ai'), ('c', 'Nearby words:\nprivate · secret\nseed · key=', .5, .8, 'private', 'hu'), ('r', 'Write rejected', .84, .35, 'rejected', 'bad')],
             edges=[('h', 'r', 'tripped', 'wire tripped'), ('c', 'r', 'private', '')]),
    58: dict(title='Seed phrases', nodes=[('w', 'apple · river · truck', .26, .3, 'apple', 'ai'), ('b', 'BIP-39 word list', .74, .3, 'bip39', 'hu'), ('n', 'Normal English text\nis not blocked', .5, .78, 'normal', 'ok')],
             edges=[('w', 'b', 'bip39', 'checked against')]),
    60: dict(title='The audit log', nodes=[('a', 'audit.jsonl\nappend-only', .2, .5, 'append', 'hu'), ('p', 'Principal ID', .75, .14, 'principal', 'n'), ('t', 'Tool used', .75, .38, 'tool', 'n'), ('f', 'File path', .75, .62, 'path', 'n'), ('s', 'Exact timestamp', .75, .86, 'timestamp', 'n')],
             edges=[('a', 'p', 'principal', ''), ('a', 't', 'tool', ''), ('a', 'f', 'path', ''), ('a', 's', 'timestamp', '')]),
    61: dict(title='The log never holds note text', nodes=[('a', 'Audit log', .18, .5, 'audit', 'hu'), ('y', 'Records: who,\nwhat, when', .82, .26, 'crucially', 'ok'), ('n', 'Never: note bodies\nor query text', .82, .74, 'never', 'bad')],
             edges=[('a', 'y', 'crucially', ''), ('a', 'n', 'never', 'no second leak')]),
    63: dict(title='Owner-triggered jobs', nodes=[('o', 'Human owner\n(command line)', .2, .5, 'human', 'hu'), ('c', 'consolidate', .8, .14, 'consolidate', 'ai'), ('s', 'supersede', .8, .38, 'supersede', 'ai'), ('f', 'forget', .8, .62, 'forget', 'ai'), ('r', 'reflect', .8, .86, 'reflect', 'ai')],
             edges=[('o', 'c', 'consolidate', ''), ('o', 's', 'supersede', ''), ('o', 'f', 'forget', ''), ('o', 'r', 'reflect', '')]),
    64: dict(title='Proposals, never silent edits', nodes=[('j', 'Cognition\njob', .15, .35, 'jobs', 'ai'), ('b', 'Reads sections\nof the brain', .5, .15, 'read', 'n'), ('p', 'Proposals', .85, .35, 'proposals', 'ai'), ('i', 'The inbox rule:\nno silent edits', .5, .82, 'inbox', 'hu')],
             edges=[('b', 'j', 'read', ''), ('j', 'p', 'proposals', '')]),
    66: dict(title='Nothing is permanent until a human accepts', nodes=[('m', 'Model\nproposal', .12, .5, 'cannot', 'ai'), ('i', 'Inbox\nstatus: proposed', .38, .5, 'reviews', 'n'), ('h', 'Human\naccepts', .64, .5, 'manually', 'hu'), ('c', 'Curated\nmemory', .88, .5, 'permanent', 'ok')],
             edges=[('m', 'i', 'reviews', ''), ('i', 'h', 'manually', ''), ('h', 'c', 'accepts', '')]),
    67: dict(title='Overconfident models', nodes=[('l', 'LLM', .18, .5, 'hallucinate', 'ai'), ('c', '"I am 99% sure\nthis is optimal"', .6, .25, 'sure', 'bad'), ('q', 'How does FutCo\nhandle that?', .6, .78, 'handle', 'hu')],
             edges=[('l', 'c', 'sure', '')]),
    69: dict(title='We do not trust internal feelings', nodes=[('f', 'Algorithm\'s internal\nfeelings', .22, .25, 'feelings', 'bad'), ('c', 'How to rank\nwhich lessons matter?', .5, .78, 'prioritize', 'hu')],
             edges=[('f', 'c', 'prioritize', 'refused')]),
    70: dict(title='Grounded lessons', nodes=[('l', 'Proposed\nlesson', .15, .5, 'lesson', 'ai'), ('c', 'Cites verifiable\nexternal identifiers', .5, .5, 'cites', 'hu'), ('r', 'Rank rises', .86, .5, 'rank', 'ok')],
             edges=[('l', 'c', 'cites', ''), ('c', 'r', 'rank', 'real-world evidence')]),
    72: dict(title='Receipts, or it sinks', nodes=[('p', 'Profound lesson,\nzero citations', .22, .3, 'philosophical', 'ai'), ('s', 'Sinks to the bottom', .3, .82, 'sinks', 'bad'), ('e', 'Observed evidence\nin the real world', .78, .3, 'exclusively', 'ok')],
             edges=[('p', 's', 'sinks', '')]),
    73: dict(title='Fifty changes to review', nodes=[('j', 'Supersede job', .18, .25, 'supersede', 'ai'), ('m', '50 old notes\n→ 1 master note', .5, .5, 'consolidated', 'ai'), ('r', 'Review\n50 changes', .82, .25, 'review', 'hu'), ('d', 'Crucial detail\nlost?', .82, .78, 'deleted', 'bad')],
             edges=[('j', 'm', 'consolidated', ''), ('m', 'r', 'review', ''), ('m', 'd', 'deleted', '')]),
    75: dict(title='Shadow mode and replay', nodes=[('s', 'Shadow mode:\nproposals go to a\ntemporary directory', .26, .28, 'sandbox', 'ai'), ('g', 'Vault backed by Git:\ncheck out last March', .76, .28, 'git', 'hu'), ('r', 'Replay evaluation', .5, .78, 'replay', 'ok')],
             edges=[('g', 'r', 'replay', '')]),
    76: dict(title='March vs. April', nodes=[('m', 'March: what the AI\nwould have proposed', .25, .35, 'march', 'ai'), ('a', 'April: what the human\nactually did', .75, .35, 'april', 'hu'), ('c', 'Compare', .5, .8, 'compares', 'ok')],
             edges=[('m', 'c', 'compares', ''), ('a', 'c', 'compares', '')]),
    78: dict(title='The undo store', nodes=[('u', 'Atom-by-atom\nundo store', .5, .2, 'undo', 'ok'), ('r', 'File is\nrewritten', .2, .68, 'rewritten', 'ai'), ('s', 'Original bytes saved\nin a private directory', .76, .68, 'saved', 'hu')],
             edges=[('s', 'r', 'saved', 'before')]),
    79: dict(title='One command to undo', nodes=[('m', 'Mistake\nfound', .12, .38, 'mistake', 'bad'), ('c', 'undo', .4, .38, 'undo', 'hu'), ('r', 'Originals restored\nbyte for byte', .8, .38, 'restores', 'ok'), ('u', 'unless you edited\nthose files since', .8, .8, 'provided', 'dim')],
             edges=[('m', 'c', 'undo', ''), ('c', 'r', 'restores', '')]),
    81: dict(title='Explicit boundaries', nodes=[('w', 'AI does\nwhatever it wants', .2, .2, 'whatever', 'bad'), ('a', 'Prove\nthe work', .16, .76, 'prove', 'hu'), ('b', 'Cite\noutcomes', .5, .76, 'cite', 'hu'), ('c', 'Pass independent\nreviews', .84, .76, 'independent', 'hu'), ('p', 'Production', .62, .24, 'production', 'ok')],
             edges=[('a', 'p', 'prove', ''), ('b', 'p', 'cite', ''), ('c', 'p', 'independent', '')]),
    82: dict(title='The contractor', nodes=[('a', 'AI model:\nhighly capable,\ninherently dangerous', .24, .5, 'contractor', 'ai'), ('k', 'Master keys\non day one', .8, .5, 'keys', 'bad')],
             edges=[('a', 'k', 'hand', 'do not hand over')]),
    84: dict(title='From debate floor to memory vault', nodes=[('p', 'E3D Pilot\nmulti-model debate,\nisolated worktrees', .2, .5, 'pilot', 'ai'), ('b', 'E3D Brain\ngoverned, self-designed\nmemory vault', .8, .5, 'brain', 'ok')],
             edges=[('p', 'b', 'strictly', '')]),
    85: dict(title='Defensive AI engineering', nodes=[('a', 'Debated its own\narchitecture', .16, .3, 'debated', 'ai'), ('b', 'Fail-hard\nsecret scrubbers', .5, .3, 'scrubbers', 'ok'), ('c', 'Grounded outcomes,\nnot self-scored\nconfidence', .82, .3, 'grounded', 'hu'), ('m', 'A masterclass in\ndefensive AI engineering', .5, .8, 'masterclass', 'n')],
             edges=[('a', 'm', 'masterclass', ''), ('b', 'm', 'masterclass', ''), ('c', 'm', 'masterclass', '')]),
    87: dict(title='Why disagreement matters', nodes=[('m', 'Different models,\ndifferent training', .22, .28, 'architectures', 'ai'), ('b', 'Unique blind spots\nthe others catch', .78, .28, 'blind', 'ok'), ('w', "The writers' room needs\ndiverse opinions", .5, .78, 'writers', 'hu')],
             edges=[('m', 'b', 'blind', ''), ('b', 'w', 'writers', '')]),
    88: dict(title='Will disagreement disappear?', nodes=[('d', 'Same internet\ndata', .2, .3, 'scrape', 'ai'), ('c', 'Converging\ncapability ceiling', .5, .72, 'converge', 'ai'), ('x', 'Natural disagreement\ndisappears?', .8, .3, 'disappear', 'bad')],
             edges=[('d', 'c', 'converge', ''), ('c', 'x', 'disappear', '')]),
    90: dict(title='Your call', nodes=[('b', 'Let the black box\nact on its own?', .24, .32, 'black', 'bad'), ('f', 'Build a rigorous\nfactory floor?', .76, .32, 'factory', 'ok'), ('h', "How do you grade your\nAI's homework?", .5, .8, 'homework', 'hu')],
             edges=[]),
}

_font_cache = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _font_cache:
        for p in ('/System/Library/Fonts/Helvetica.ttc', '/System/Library/Fonts/SFNS.ttf'):
            if Path(p).exists():
                try:
                    _font_cache[key] = ImageFont.truetype(p, size, index=1 if bold and p.endswith('.ttc') else 0)
                    break
                except Exception:
                    continue
        else:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def norm(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def load_words():
    utts = json.loads((OUT / 'e3d-pilot-notebooklm-diarization.json').read_text())['utterances']
    return [(norm(w['text']), w['start'] / 1000.0) for u in utts for w in u['words']]


def scene_windows():
    sys.path.insert(0, str(ROOT))
    import make_pilot_interview as m
    sc = {}
    for c in m.orig_plan():
        s = sc.setdefault(c['scene'], {'t0': c['start'], 'len': 0.0, 'layout': c['layout']})
        s['len'] += c['len']
    return sc


def cue_time(words, cue, t0, t1, after=0.0):
    key = norm(cue)
    for w, t in words:
        if t < t0 - 0.05 or t > t1:
            continue
        if t >= after and (w == key or (len(key) >= 4 and w.startswith(key))):
            return t - t0
    return None


def resolve(spec, words, t0, dur):
    """Appearance time of every node and edge, in seconds from the scene start."""
    nodes, edges = {}, []
    n = len(spec['nodes'])
    for i, (nid, label, x, y, cue, style) in enumerate(spec['nodes']):
        t = cue_time(words, cue, t0, t0 + dur)
        found = t is not None
        t = max(0.5, (t - 0.08) if found else (i + 1) / (n + 1) * dur * 0.85)
        nodes[nid] = dict(id=nid, label=label, x=x, y=y, style=style, t=t, found=found, cue=cue)
    for a, b, cue, label in spec.get('edges', []):
        t = cue_time(words, cue, t0, t0 + dur)
        te = max(nodes[a]['t'], nodes[b]['t'], (t - 0.08) if t is not None else 0) + 0.12
        edges.append(dict(a=a, b=b, t=te, label=label))
    return nodes, edges


def sprite(label, style):
    fill, border = STYLE[style]
    f = font(24)
    lines = label.split('\n')
    d = ImageDraw.Draw(Image.new('RGB', (4, 4)))
    w = max(d.textlength(l, font=f) for l in lines)
    lh = 30
    pw, ph = int(w + 40), lh * len(lines) + 26
    img = Image.new('RGBA', (pw + 12, ph + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, 6 + pw, 6 + ph], radius=12, fill=fill + (255,), outline=border + (255,), width=3)
    for i, l in enumerate(lines):
        tw = d.textlength(l, font=f)
        d.text((6 + (pw - tw) / 2, 6 + 13 + i * lh), l, font=f, fill=TEXT + (255,))
    return img, (pw, ph)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def rect_edge(cx, cy, w, h, tx, ty):
    """Point where the ray from the rectangle centre toward (tx, ty) leaves the rectangle."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else 1e9
    sy = (h / 2) / abs(dy) if dy else 1e9
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


class Card:
    def __init__(self, spec, nodes, edges):
        self.spec, self.nodes, self.edges = spec, nodes, edges
        for n in nodes.values():
            n['img'], n['size'] = sprite(n['label'], n['style'])
            n['cx'], n['cy'] = n['x'] * CW, 60 + n['y'] * (CH - 90)
        grid = Image.new('RGB', (CW, CH), PANEL)
        gd = ImageDraw.Draw(grid)
        for gx in range(0, CW, 45):
            gd.line([(gx, 0), (gx, CH)], fill=GRID)
        for gy in range(0, CH, 45):
            gd.line([(0, gy), (CW, gy)], fill=GRID)
        self.bg = grid.convert('RGBA')

    def frame(self, t):
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        ta = ease(t / 0.5)
        d.text((24, 18), self.spec['title'].upper(), font=font(20), fill=tuple(int(c * ta + PANEL[i] * (1 - ta)) for i, c in enumerate(AMBER)))
        for e in self.edges:
            p = ease((t - e['t']) / 0.5)
            if p <= 0:
                continue
            a, b = self.nodes[e['a']], self.nodes[e['b']]
            x0, y0 = rect_edge(a['cx'], a['cy'], a['size'][0] + 8, a['size'][1] + 8, b['cx'], b['cy'])
            x1, y1 = rect_edge(b['cx'], b['cy'], b['size'][0] + 14, b['size'][1] + 14, a['cx'], a['cy'])
            xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
            d.line([(x0, y0), (xe, ye)], fill=EDGE + (255,), width=3)
            if p >= 0.98:
                import math
                ang = math.atan2(y1 - y0, x1 - x0)
                for s in (-0.5, 0.5):
                    d.line([(x1, y1), (x1 - 14 * math.cos(ang + s), y1 - 14 * math.sin(ang + s))], fill=EDGE + (255,), width=3)
                if e['label']:
                    f = font(16, False)
                    lw = d.textlength(e['label'], font=f)
                    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                    d.rounded_rectangle([mx - lw / 2 - 6, my - 12, mx + lw / 2 + 6, my + 12], radius=6, fill=PANEL + (255,))
                    d.text((mx - lw / 2, my - 9), e['label'], font=f, fill=(200, 205, 215, 255))
        for n in sorted(self.nodes.values(), key=lambda n: n['t']):
            p = (t - n['t']) / 0.3
            if p <= 0:
                continue
            s = 0.6 + 0.4 * ease(p)
            spr = n['img']
            if s < 0.999:
                spr = spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.LANCZOS)
            if p < 1:
                a = int(255 * ease(p))
                spr = spr.copy()
                spr.putalpha(spr.getchannel('A').point(lambda v: v * a // 255))
            pulse = t - n['t']
            if 0 <= pulse < 0.9:
                r = 6 + 22 * (pulse / 0.9)
                alpha = int(120 * (1 - pulse / 0.9))
                ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                w, h = n['size']
                od.rounded_rectangle([n['cx'] - w / 2 - r, n['cy'] - h / 2 - r, n['cx'] + w / 2 + r, n['cy'] + h / 2 + r], radius=14 + r // 2,
                                     outline=STYLE[n['style']][1] + (alpha,), width=3)
                im = Image.alpha_composite(im, ov)
            im.alpha_composite(spr, (int(n['cx'] - spr.width / 2), int(n['cy'] - spr.height / 2)))
        return im.convert('RGB')


def check_layout(card, sid):
    probs = []
    ns = list(card.nodes.values())
    for n in ns:
        w, h = n['size']
        if n['cx'] - w / 2 < 4 or n['cx'] + w / 2 > CW - 4 or n['cy'] - h / 2 < 40 or n['cy'] + h / 2 > CH - 4:
            probs.append(f'{n["id"]} out of bounds')
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            if abs(a['cx'] - b['cx']) < (a['size'][0] + b['size'][0]) / 2 + 8 and abs(a['cy'] - b['cy']) < (a['size'][1] + b['size'][1]) / 2 + 8:
                probs.append(f'{a["id"]} overlaps {b["id"]}')
    return probs


def build(sid, words, win):
    spec = SPECS[sid]
    nodes, edges = resolve(spec, words, win['t0'], win['len'])
    return Card(spec, nodes, edges), nodes


def render_scene(args):
    sid, win = args
    words = load_words()
    out = CARDS / f'scene_{sid:03d}.mp4'
    if out.exists() and out.stat().st_size > 1000:
        return sid, 'cached'
    card, _ = build(sid, words, win)
    dur = win['len'] + 1.5
    n = int(dur * FPS)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{CW}x{CH}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(card.frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return sid, 'ok'


def main():
    CARDS.mkdir(parents=True, exist_ok=True)
    words, wins = load_words(), scene_windows()
    what = sys.argv[1] if len(sys.argv) > 1 else 'render'
    ids = [int(x) for x in sys.argv[2:]] or sorted(SPECS)
    if what == 'check':
        for sid in ids:
            card, nodes = build(sid, words, wins[sid])
            miss = [n['cue'] for n in nodes.values() if not n['found']]
            probs = check_layout(card, sid)
            if miss or probs:
                print(sid, 'cue not found:', miss, 'layout:', probs)
        print('checked', len(ids), 'scenes;', 'non-split scenes with specs:', [s for s in ids if wins[s]['layout'] != 'split'])
    elif what == 'still':
        sid = ids[0]
        card, _ = build(sid, words, wins[sid])
        path = CARDS / f'still_{sid:03d}.png'
        card.frame(wins[sid]['len']).save(path)
        print(path)
    else:
        with Pool(4) as pool:
            for sid, st in pool.imap_unordered(render_scene, [(s, wins[s]) for s in ids]):
                print('scene', sid, st, flush=True)


if __name__ == '__main__':
    main()
