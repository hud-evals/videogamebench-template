"""Tasks for the VideoGameBench HUD environment.

Each task is a (game, max_steps) instance of the ``play-game`` template. Push to
a taskset with ``hud sync tasks <taskset>`` and run with ``hud eval <taskset>``.

    hud deploy .
    hud sync tasks vgbench
    hud eval vgbench --remote --full
"""

from hud import Taskset

# `env` is re-exported so `hud eval tasks.py` can serve the Environment from here.
from env import env, play_game  # noqa: F401

# Underscore-prefixed so the collector counts each task once (via the Taskset
# below), not also as a bare module global — that would double-count the slugs.
_test = play_game(game="test", max_steps=150)
_test.slug = "play-libbet-test"

# Pokémon Crystal — requires pokemon_crystal.gbc in roms/. RAM (dense) + checkpoint + exploration.
_pokemon_crystal = play_game(game="pokemon_crystal", max_steps=2000)
_pokemon_crystal.slug = "play-pokemon-crystal"

# Zelda: Link's Awakening DX — requires zelda_links_awakening.gbc in roms/. Checkpoint + exploration.
_zelda = play_game(game="zelda", max_steps=2000)
_zelda.slug = "play-zelda"

taskset = Taskset("vgbench", [_test, _pokemon_crystal, _zelda])
