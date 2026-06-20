# ROMs

Game ROMs are **copyrighted** and are **not** shipped with this template (except
the bundled homebrew test ROM). Place your **legally-owned** ROMs here, matching
the `rom:` filename in each game's `games/<game>/config.yaml`.

| Game            | Expected file in `roms/` |
|-----------------|--------------------------|
| `test` (bundled)| `libbet.gb` ✅ included    |
| `pokemon_crystal` | `pokemon_crystal.gbc`  |
| `zelda`         | `zelda_links_awakening.gbc` |

`libbet.gb` is **"Libbet and the Magic Floor"** by Damian Yerrick / Martin Korth,
distributed under the **zlib License** (see `libbet.LICENSE.txt`) — free to bundle
and redistribute. Source: https://github.com/pinobatch/libbet

## Providing ROMs at deploy time

`roms/` is git-ignored (except the test ROM) so you never commit copyrighted data.
For remote runs, inject your ROM into the deployed image/container rather than
baking it into a public image — e.g. via `hud deploy` secrets/env or a private
fetch at startup. See the top-level `README.md` ("Providing ROMs").
