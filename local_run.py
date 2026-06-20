"""Local smoke-runner — drive a game with a simple scripted agent, no HUD infra.

This is a developer convenience for verifying a game boots, the tools return
screenshots, and scoring accumulates. It is NOT the real eval harness (that's an
external HUD agent driving the MCP server); it just exercises the same scenario +
tools locally with a heuristic button sequence.

Usage:
    python local_run.py --game test --steps 60
    python local_run.py --game test --steps 80 --out logs/test
    python local_run.py --list
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random

import env
import games_loader
from env import play_game, press_buttons, screenshot, wait

# A reasonable cycling sequence for menu-driven Game Boy games.
BUTTON_CYCLE = [
    ["START"], ["A"], ["A"], ["DOWN"], ["A"], ["UP"], ["RIGHT"],
    ["LEFT"], ["DOWN"], ["A"], ["B"], ["UP"], ["RIGHT"], ["A"],
]


async def run_game(game: str, steps: int, out_dir: str | None, seed: int) -> None:
    rng = random.Random(seed)
    gen = play_game.func(game=game, max_steps=steps)
    prompt = await gen.asend(None)
    print(f"\n=== {game} ===")
    print(prompt.strip().splitlines()[0])

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        env._session["emulator"].get_screen().save(os.path.join(out_dir, "step_000.png"))

    for i in range(1, steps + 1):
        combo = BUTTON_CYCLE[i % len(BUTTON_CYCLE)]
        if rng.random() < 0.15:  # occasionally just wait
            await wait(20)
        else:
            await press_buttons(combo, frames=18)
        if out_dir and i % max(1, steps // 6) == 0:
            env._session["emulator"].get_screen().save(
                os.path.join(out_dir, f"step_{i:03d}.png")
            )

    result = await gen.asend("local scripted run finished")
    print(f"reward : {result.reward:.4f}  (done={result.done})")
    print(f"content: {result.content}")
    for s in result.subscores or []:
        print(f"  - {s.name:11} value={s.value:.3f} weight={s.weight:.2f}")
    print(f"info   : {result.info}")
    if out_dir:
        print(f"screenshots saved to {out_dir}/")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", default="test")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--out", default=None, help="dir to save periodic screenshots")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", action="store_true", help="list available games and exit")
    args = ap.parse_args()

    if args.list:
        print("Available games:", games_loader.list_games())
        return

    asyncio.run(run_game(args.game, args.steps, args.out, args.seed))


if __name__ == "__main__":
    main()
