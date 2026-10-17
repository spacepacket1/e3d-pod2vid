# Cold open experiment: "Will AI Take Your Job?"

A two-minute sketch written by three AI models and voiced with synthetic voices. Video: https://www.youtube.com/watch?v=OGuKzdwQzrE

This folder is for reference: the **original, unedited draft** the models wrote, the **final script** that was voiced, and the small scripts and prompts that produced them.

| File | What it is |
| --- | --- |
| `script-raw.txt` | The writers' room output exactly as generated: 24 lines, 688 words, one line per turn |
| `script-final.txt` | The edited script that was voiced: 17 lines, about 320 spoken words |
| `producer-prompt.md` | The editing prompt (it ends with the raw draft it was given) |
| `drive.sh` | The sequential writers' room: each line written by the model playing that character |
| `tts_build.py` | Voices each line (ElevenLabs stock voices) and builds the timeline and audio |
| `render.py` | Renders the faceless news-desk video from the timeline and audio |

## How it was made

1. **Writers' room (`drive.sh`).** Three characters, three models: DANA the anchor (Claude), ORACLE (an OpenAI model) and GROK (Grok). Each line was generated after seeing the script so far, with a 35-word cap and a shared brief that included a few real news items from mid-October 2026 (the September jobs report, a Fed rate hike, a chip-stock slide, a reported AI sandbox escape).
2. **Producer pass.** A head-writer prompt cut the draft to 17 lines, limited each character's catchphrase to two uses (the second one had to be a twist), kept the best original lines, and fixed the countdown.
3. **Corrections.** Three factual slips in the edit were fixed by hand ("jobs gone" should have been "added", "hiking again", "three robots" for two).
4. **Voices and picture.** Stock ElevenLabs voices, a faceless animated news desk, a ticker of the real headlines, and an "AI-generated satire" label.

## What the raw draft shows

The first six lines are sharp. After that each model starts imitating its own previous line: ORACLE repeats "Great question! First, a framework..." and GROK repeats "Love the X. Receipts: ... I'm just asking...". Escalation stalls. Sequential generation, line by line, tends to collapse into per-model templates, which is why the producer pass mattered more than any rewording of the prompts. Compare `script-raw.txt` with `script-final.txt` to see what the editing changed.

This is AI-generated satire. The characters are fictional personas and do not represent any company.
