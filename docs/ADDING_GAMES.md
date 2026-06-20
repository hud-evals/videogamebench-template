# Adding games & building — participant guide

This guide shows how to add a new Game Boy game to the template, score it, test it
locally, and build/deploy.

> **Tip:** ready-made prompts, menu-setup scripts, and checkpoint images for ~20
> classic games exist in the **VideoGameBench** project
> (<https://github.com/alexzhang13/videogamebench>), under `configs/<game>/` — you can
> copy them straight into `games/<game>/` here (that's how `pokemon_crystal`/`zelda`
> were set up). Optional, but a big shortcut.

---

## 1. Game folder layout

Each game is a folder under `games/`:

```
games/<game>/
  config.yaml        # required — emulator, rom, scoring, frame budgets
  prompt.txt         # optional — system prompt shown to the agent each turn
  preload.txt        # optional — menu/intro setup (sleep / press_key)
  checkpoints/        # optional — ordered 1.png, 2.png, … for checkpoint scoring
  ram_map.py         # optional — dense RAM reward (read() + reward())
```

The ROM itself goes in `roms/<file>` (see step 3), **not** in the game folder.

---

## 2. Add a new game — step by step

1. **Pick the game key & ROM filename.** Use the same key VideoGameBench uses. The
   expected ROM filename is in the original repo's `src/consts.py` `ROM_FILE_MAP`:

   | `--game` key | `roms/` filename |
   |---|---|
   | `pokemon_red` | `pokemon_red.gb` |
   | `pokemon_crystal` | `pokemon_crystal.gbc` |
   | `zelda` | `zelda_links_awakening.gbc` |
   | `super_mario_land` | `super_mario_land.gb` |
   | `kirby` | `kirby_dream_land.gb` |
   | `mega_man` | `mega_man_dr_wilys_revenge.gb` |
   | `donkey_kong` | `donkey_kong_land_2.gb` |
   | `castlevania` | `castlevania_the_adventure.gb` |
   | `scooby_doo` | `scooby_doo_classic_creep_capers.gbc` |
   | `dragon_warrior_monsters_2` | `dragon_warrior_monsters_2_cobis_journey.gbc` |

2. **Place the ROM** at `roms/<filename>`. ROMs are **copyrighted and not bundled** —
   supply your own legally-owned copy. `roms/` is git-ignored (except the test ROM),
   so ROMs are never committed.

3. **Copy the game's assets from VideoGameBench** (optional but recommended):
   ```bash
   # from a checkout of https://github.com/alexzhang13/videogamebench
   mkdir -p games/<game>
   cp configs/<game>/prompt.txt        games/<game>/
   cp configs/<game>/preload.txt       games/<game>/   # if present
   cp -R configs/<game>/checkpoints    games/<game>/   # if present
   ```

4. **Write `games/<game>/config.yaml`** (see reference below).

5. **Add a task** in `tasks.py`:
   ```python
   play_kirby = play_game.task(game="kirby", max_steps=1500)
   play_kirby.slug = "play-kirby"
   ALL_TASKS["play_kirby"] = play_kirby
   ```

6. **Test it** (step 6) and **deploy** (step 7).

---

## 3. `config.yaml` reference

```yaml
emulator: gba            # only "gba" (Game Boy / Color) is supported
rom: kirby_dream_land.gb # filename under roms/
boot_frames: 600         # frames to tick past the boot logo before play/preload
action_frames: 15        # default hold/advance length for a button press
scoring:                 # list of scorers; positive weights are normalized to 1.0
  - type: checkpoint
    threshold: 8         # perceptual-hash Hamming distance (lower = stricter)
    weight: 0.7
  - type: exploration
    target: 30           # unique screens for full marks
    threshold: 4
    weight: 0.3
```

If `scoring` is omitted, a single generic `exploration` scorer is used.

---

## 4. Scoring options

| `type` | What it measures | Needs |
|--------|------------------|-------|
| `exploration` | distinct screens seen / `target` (generic, ROM-agnostic dense reward) | nothing |
| `checkpoint` | progress through ordered `checkpoints/*.png` via perceptual hash (VideoGameBench's method) | `checkpoints/` PNGs |
| `ram` | dense reward read from Game Boy RAM | `ram_map.py` |

Final reward = Σ(scorer value × normalized weight); each scorer also reports a
`SubScore` you can see in the eval results.

---

## 5. Dense RAM scoring (`ram_map.py`)

For the richest signal, read game memory directly. Create `games/<game>/ram_map.py`
with two functions:

```python
def read(emulator) -> dict:
    """Pull raw values. emulator.read_memory(addr) reads one byte."""
    return {"badges": bin(emulator.read_memory(0xD356)).count("1")}

def reward(values: dict) -> float:
    """Collapse to a single number in [0, 1]. Taken as a max over the episode."""
    return min(values["badges"], 8) / 8
```

Then add `- type: ram` to `scoring`. A worked example ships:
`games/pokemon_crystal/ram_map.py` — a GBC game whose data lives in **WRAM bank 1**
(`read_memory(addr, bank=1)`). For a plain DMG game, omit the bank
(`read_memory(addr)`) — see the WRAM-banks note below.

### `emulator` API available inside `read()`

| call | reads |
|------|-------|
| `emulator.read_memory(addr)` | one byte at `addr`, currently-mapped bank |
| `emulator.read_memory(addr, bank=1)` | one byte from a specific bank |
| `emulator.read_memory_range(addr, n[, bank=1])` | `n` consecutive bytes |

### GBC WRAM banks (important)

On Game Boy **Color** games, `0xC000-0xCFFF` is fixed WRAM (bank 0) but
`0xD000-0xDFFF` is **banked** — the same address means different memory depending
on the mapped bank. Most player data (Pokémon Crystal etc.) lives in **WRAM bank
1**, so read those addresses with `bank=1`. Plain DMG games (Pokémon Red, Kirby,
Super Mario Land) aren't banked — omit `bank`. If values look like garbage, a wrong
bank is the usual cause.

### Finding addresses — tools

1. **Disassemblies / symbol files (most reliable).** The `pret` projects
   (`pokered`, `pokecrystal`, …) define every variable in `wram.asm`, and a build
   emits a `.sym` file mapping names → `BANK:ADDR`. Search for `wPartyCount`,
   `wPlayerMoney`, `wBadges`, etc. Repos: <https://github.com/pret>.
2. **Community RAM maps.** Data Crystal (<https://datacrystal.tcrf.net>) has
   per-game WRAM maps for many titles.
3. **Emulator RAM search / watchpoints.** BGB, SameBoy, Emulicious, or mGBA let
   you do a "search for a value → change it in-game → re-search" loop (like a
   memory scanner) and set write-watchpoints to catch the address a stat lives at.
4. **PyBoy diff search (no extra tools).** You already have PyBoy — find an address
   by snapshotting memory, changing one thing in-game, and diffing:
   ```python
   from emulator import GameBoyEmulator
   e = GameBoyEmulator(); e.load_game("roms/<game>.gb", boot_frames=600)
   before = e.read_memory_range(0xC000, 0x2000)          # whole WRAM (or bank: ..., bank=1)
   # ... drive e.step(...) until exactly ONE thing changes in-game (e.g. money +100) ...
   after = e.read_memory_range(0xC000, 0x2000)
   print([hex(0xC000+i) for i,(a,b) in enumerate(zip(before,after)) if a!=b])
   ```
   Narrow the candidate list by repeating with different changes.

### Verify & gate

- Confirm with `emulator.read_memory(addr[, bank])` once you're in a known state
  (e.g. right after earning a badge) and check the byte matches.
- **Gate** the reward so uninitialized RAM on the title/continue screen can't
  inflate the score — both examples return `0.0` until the party is non-empty.
- Keep `reward()` in `[0, 1]`; the scorer takes the max over the episode (monotonic).

---

## 6. `preload.txt` (skip menus/intro)

Runs once after boot, before the agent acts. One command per line; `#` comments:

```
sleep 10          # advance 10 seconds (10*60 frames)
press_key START   # tap a button: A B START SELECT UP DOWN LEFT RIGHT
press_key A
```

Copy VideoGameBench's `configs/<game>/preload.txt` to start the agent in actual
gameplay instead of on the title screen.

---

## 7. Test locally (no HUD infra)

```bash
python local_run.py --list                       # list games
python local_run.py --game kirby --steps 120 --out logs/kirby   # scripted smoke run + screenshots
python -m pytest tests/                           # unit/integration tests
hud serve env:env                                 # run the MCP server locally
```

`local_run.py` drives the real scenario + tools with a heuristic button sequence
and saves periodic screenshots to `--out` — handy for confirming a new game boots,
the preload reaches gameplay, and scoring accumulates.

---

## 8. Build & deploy

```bash
hud deploy .                          # build the image + deploy (slow; once)
hud sync tasks vgbench                # push tasks.py instances (fast)
hud eval vgbench --remote --full      # run the eval with a HUD agent
```

`hud deploy` builds `Dockerfile.hud` (installs deps via `pip install .`, copies the
modules + `games/` + `roms/` + `tests/`). Redeploy only when code, `games/`, ROMs,
or the Dockerfile change; task-only edits just need `hud sync tasks`.

### Providing ROMs to a remote deployment

ROMs are git-ignored and shouldn't be baked into a shareable public image. For
remote runs, inject them at deploy time (HUD deploy secrets/env, or a private fetch
at container startup) and write them to `roms/<filename>` before the eval runs. See
`roms/README.md`.

---

## 9. What to pull from the original VideoGameBench

From <https://github.com/alexzhang13/videogamebench>:

- `configs/<game>/` — prompts, preloads, checkpoint images for ~20 titles.
- `src/consts.py` — `ROM_FILE_MAP` (GB ROM filenames).
- The paper (arXiv:2505.18134) for scoring methodology and the official game list.

