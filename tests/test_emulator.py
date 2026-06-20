"""Tests for the PyBoy Game Boy wrapper."""

import os

import pytest

from emulator import (
    BUTTON_MAP,
    GB_BUTTONS,
    RELEASE_MAP,
    GameBoyEmulator,
    sanitize_buttons,
)

ROM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "roms", "libbet.gb"
)
needs_rom = pytest.mark.skipif(not os.path.exists(ROM), reason="test ROM (libbet.gb) missing")


def test_button_maps_consistent():
    assert set(BUTTON_MAP) == set(RELEASE_MAP) == set(GB_BUTTONS)


def test_sanitize_buttons_normalizes_and_dedupes():
    valid, invalid = sanitize_buttons(["a", "UP", "x", "up"])
    assert valid == ["A", "UP"]
    assert invalid == ["x"]


def test_sanitize_start_select_reset_guard():
    valid, invalid = sanitize_buttons(["START", "SELECT"])
    assert valid == ["START"]
    assert any("SELECT" in str(i) for i in invalid)


def test_missing_rom_raises():
    emu = GameBoyEmulator()
    with pytest.raises(FileNotFoundError):
        emu.load_game(os.path.join(os.path.dirname(ROM), "does_not_exist.gb"))


@needs_rom
def test_boot_and_screen():
    emu = GameBoyEmulator()
    try:
        emu.load_game(ROM, boot_frames=200)
        img = emu.get_screen()
        assert img.size == (160, 144)
        assert img.mode == "RGB"
    finally:
        emu.close()


@needs_rom
def test_screen_changes_with_input():
    from scoring import hash_image

    emu = GameBoyEmulator()
    try:
        emu.load_game(ROM, boot_frames=300)
        h0 = hash_image(emu.get_screen())
        for combo in (["START"], ["A"], ["A"], ["DOWN"], ["A"]):
            emu.step({b: True for b in combo}, frames=20)
        h1 = hash_image(emu.get_screen())
        assert (h0 - h1) > 0  # the rendered frame actually advanced
    finally:
        emu.close()


@needs_rom
def test_read_memory_and_save_load_state(tmp_path):
    emu = GameBoyEmulator()
    try:
        emu.load_game(ROM, boot_frames=200)
        assert isinstance(emu.read_memory(0xC000), int)
        assert len(emu.read_memory_range(0xC000, 4)) == 4
        p = str(tmp_path / "s.state")
        emu.save_state(p)
        emu.load_state(p)  # should not raise
    finally:
        emu.close()
