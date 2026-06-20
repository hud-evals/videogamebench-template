"""Tests for the scorers and ScoreBoard."""

from PIL import Image

from hud.graders import EvaluationResult
from scoring import (
    CheckpointScorer,
    ExplorationScorer,
    RamScorer,
    ScoreBoard,
    hash_image,
)


def _distinct_imgs(n=4):
    """Images with a white block at different x positions -> distinct hashes."""
    imgs = []
    for i in range(n):
        im = Image.new("RGB", (160, 144), (0, 0, 0))
        for x in range(i * 30, i * 30 + 28):
            for y in range(40, 110):
                im.putpixel((x, y), (255, 255, 255))
        imgs.append(im)
    return imgs


class _FakeEmu:
    def __init__(self, value):
        self.value = value

    def read_memory(self, addr):
        return self.value


class _FakeMap:
    def read(self, emu):
        return {"x": emu.read_memory(0)}

    def reward(self, values):
        return values["x"] / 10.0


def test_exploration_counts_distinct_screens():
    imgs = _distinct_imgs(4)
    s = ExplorationScorer(target_unique=4, threshold=2)
    for im in imgs:
        s.on_step(screen=im)
    s.on_step(screen=imgs[0])  # duplicate, ignored
    assert s.info()["unique_screens"] == 4
    assert s.value() == 1.0


def test_exploration_value_capped_at_one():
    s = ExplorationScorer(target_unique=2, threshold=2)
    for im in _distinct_imgs(4):
        s.on_step(screen=im)
    assert s.value() == 1.0


def test_checkpoint_advances_in_order():
    imgs = _distinct_imgs(4)
    hashes = [hash_image(im) for im in imgs]
    s = CheckpointScorer(hashes, threshold=2)
    s.on_step(screen=imgs[0])
    s.on_step(screen=imgs[1])
    assert s.value() == 0.5
    s.on_step(screen=imgs[2])
    s.on_step(screen=imgs[3])
    assert s.value() == 1.0


def test_checkpoint_does_not_skip_ahead():
    """A frame matching a LATER checkpoint must not skip the ones before it."""
    imgs = _distinct_imgs(4)
    hashes = [hash_image(im) for im in imgs]
    s = CheckpointScorer(hashes, threshold=2)
    # Feed only the final checkpoint image while still at idx 0.
    s.on_step(screen=imgs[3])
    assert s.idx == 0
    assert s.value() == 0.0
    # Reaching the first checkpoint advances exactly one step.
    s.on_step(screen=imgs[0])
    assert s.idx == 1


def test_ram_scorer_is_monotonic():
    s = RamScorer(_FakeMap())
    s.on_step(emulator=_FakeEmu(5))  # reward 0.5
    s.on_step(emulator=_FakeEmu(2))  # reward 0.2 -> best stays 0.5
    assert s.value() == 0.5


def test_scoreboard_combines_weighted():
    imgs = _distinct_imgs(4)
    hashes = [hash_image(im) for im in imgs]
    board = ScoreBoard(
        [
            CheckpointScorer(hashes, threshold=2, weight=0.5),
            RamScorer(_FakeMap(), weight=0.5),
        ]
    )
    for im in imgs:
        board.on_step(screen=im, emulator=_FakeEmu(10))  # ram reward 1.0
    result = board.result()
    assert isinstance(result, EvaluationResult)
    assert result.reward == 1.0  # 0.5*1.0 + 0.5*1.0
    assert {s.name for s in result.subscores} == {"checkpoint", "ram"}
    assert abs(sum(s.weight for s in result.subscores) - 1.0) < 1e-6


def test_scoreboard_single_scorer():
    board = ScoreBoard([ExplorationScorer(target_unique=4, threshold=2)])
    for im in _distinct_imgs(2):
        board.on_step(screen=im)
    result = board.result()
    assert result.reward == 0.5
    assert result.subscores[0].weight == 1.0


def test_scoreboard_reward_matches_subscores():
    """ScenarioResult validates reward == sum(value*weight); ensure it holds."""
    board = ScoreBoard(
        [
            ExplorationScorer(target_unique=4, threshold=2, weight=0.3),
            RamScorer(_FakeMap(), weight=0.7),
        ]
    )
    for im in _distinct_imgs(2):
        board.on_step(screen=im, emulator=_FakeEmu(4))  # ram 0.4
    result = board.result()
    expected = sum(s.value * s.weight for s in result.subscores)
    assert abs(result.reward - expected) < 0.01
