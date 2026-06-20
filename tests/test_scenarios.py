"""End-to-end tests for the play-game scenario and tools."""

import asyncio
import os

import pytest
from mcp.types import ImageContent

import env
from env import play_game, press_buttons, screenshot, wait
from hud.graders import EvaluationResult

ROM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roms", "libbet.gb"
)
needs_rom = pytest.mark.skipif(not os.path.exists(ROM), reason="test ROM (libbet.gb) missing")


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _has_image(blocks):
    return any(isinstance(b, ImageContent) for b in blocks)


def test_tools_error_cleanly_when_no_game():
    async def _t():
        env._teardown()
        blocks = await press_buttons(["A"])
        texts = [getattr(b, "text", "") for b in blocks]
        assert any("No game" in t for t in texts)

    run(_t())


@needs_rom
def test_play_game_full_cycle():
    async def _t():
        gen = play_game.func(game="test", max_steps=15)
        prompt = await gen.asend(None)
        assert "Libbet" in prompt or "Game Boy" in prompt

        blocks = await press_buttons(["A"], frames=15)
        assert _has_image(blocks)
        assert _has_image(await wait(20))
        assert _has_image(await screenshot())

        result = await gen.asend("done")
        assert isinstance(result, EvaluationResult)
        assert 0.0 <= result.reward <= 1.0
        assert result.done is True
        assert result.info["game"] == "test"
        assert env._session["emulator"] is None  # cleaned up

    run(_t())


@needs_rom
def test_invalid_buttons_rejected():
    async def _t():
        gen = play_game.func(game="test", max_steps=10)
        await gen.asend(None)
        blocks = await press_buttons(["NOPE", "ZZZ"])
        texts = [getattr(b, "text", "") for b in blocks]
        assert any("No valid buttons" in t for t in texts)
        await gen.asend("done")

    run(_t())


@needs_rom
def test_exploration_registers_progress():
    async def _t():
        gen = play_game.func(game="test", max_steps=40)
        await gen.asend(None)
        for combo in (["START"], ["A"], ["A"], ["DOWN"], ["A"], ["UP"], ["RIGHT"], ["LEFT"], ["B"], ["A"]):
            await press_buttons(combo, frames=20)
        result = await gen.asend("done")
        assert result.info["exploration"]["unique_screens"] >= 2
        assert result.reward > 0.0

    run(_t())
