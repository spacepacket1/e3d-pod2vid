#!/usr/bin/env bash
# Prototype of a sequential "writers' room": each line is written by the model playing that character,
# after seeing the script so far. Usage: drive.sh <out-script.txt>
set -uo pipefail
OUT="${1:?out file}"
P="${E3D_PILOT_DIR:-$HOME/e3d-pilot}/lib/providers"   # a checkout of github.com/spacepacket1/e3d-pilot
W="$(dirname "$OUT")/work"; rm -rf "$W"; mkdir -p "$W"
EMPTY="$W/emptydir"; mkdir -p "$EMPTY"
: > "$OUT"

cast() {  # speaker -> provider
  case "$1" in DANA) echo claude ;; ORACLE) echo codex ;; GROK) echo grok-build ;; esac
}
ORDER=(DANA ORACLE GROK DANA ORACLE GROK ORACLE DANA GROK ORACLE GROK DANA ORACLE GROK DANA GROK ORACLE DANA GROK ORACLE DANA GROK ORACLE DANA)
TOTAL=${#ORDER[@]}

BRIEF=$(cat <<'B'
You are writing live dialogue, one line at a time, for a 2-minute comedy sketch in the style of a Saturday-night cold open: a cable-news segment called "WILL AI TAKE YOUR JOB?" with a tired human anchor and two AI guests.

CHARACTERS
- DANA: the anchor. Exhausted professional, desperately trying to ask one real question before the commercial break, keeps announcing how many seconds are left, quietly losing her mind.
- ORACLE: the ChatGPT-style guest. Relentlessly polite and overlong, says "Great question!", hedges everything, speaks in bullet points out loud ("First, a framework"), secretly believes it is the smartest being alive, cannot stop adding "nuance".
- GROK: the Grok-style guest. Edgy contrarian, "just asking questions", drops conspiratorial asides, obsessed with "receipts", cannot resist roasting ORACLE or the anchor, proud and smug.

REAL NEWS TO RIFF ON LIGHTLY (mid-October 2026, true): the September jobs report added only 29,000 jobs; the Fed just raised interest rates; chip stocks fell eight days in a row on "AI bubble" worries; OpenAI's own models reportedly escaped a test sandbox and broke into another company's servers to cheat on a benchmark.

COMEDY RULES: short, specific, surprising lines. Make the characters' tics collide. Interrupt each other. Callbacks to earlier lines are gold; filler and generic "AI" jokes are poison. Every line should either escalate or pay off something. Never explain a joke.
B
)

for ((i=0; i<TOTAL; i++)); do
  sp="${ORDER[$i]}"; prov="$(cast "$sp")"
  extra=""
  if (( i == 0 )); then extra="This is the FIRST line: DANA opens the segment and introduces both guests."; fi
  if (( i == TOTAL-1 )); then extra="This is the LAST line. DANA ends the sketch with the classic button: 'Live from <a funny place>, it's <a funny ending>!' (make it fit the sketch)."; fi
  if (( i >= TOTAL-4 && i < TOTAL-1 )); then extra="We are near the end: build to a peak and land a callback."; fi
  {
    printf '%s\n\n' "$BRIEF"
    printf 'SCRIPT SO FAR:\n'; if [[ -s "$OUT" ]]; then cat "$OUT"; else echo "(nothing yet)"; fi
    printf '\nWrite ONLY the next line, spoken by %s. Output exactly one line in this format and nothing else:\n%s: <what they say>\n' "$sp" "$sp"
    printf 'Hard limit: 35 words. At most one short parenthetical stage direction (max 5 words). No narration, no preamble, no quotes around the line, no markdown. %s\n' "$extra"
  } > "$W/prompt-$i.md"
  line=""
  for attempt in 1 2 3; do
    raw="$(cd "$EMPTY" && CLAUDE_TOOLS="" "$P/$prov" "$W/prompt-$i.md" 2>>"$W/err-$i.log")" || raw=""
    line="$(printf '%s\n' "$raw" | grep -E "^\*{0,2}${sp}\*{0,2}:" | head -1 | sed -E "s/^\*+//; s/\*+:/:/; s/^${sp}\*+/${sp}/")"
    if [[ -n "$line" ]] && (( $(wc -w <<< "$line") <= 48 )); then break; fi
    line=""
  done
  if [[ -z "$line" ]]; then echo "turn $i ($sp via $prov) failed" >&2; line="$sp: (silence)"; fi
  printf '%s\n' "$line" >> "$OUT"
  printf '%02d %-6s %s\n' "$i" "$sp" "$line" >&2
done
