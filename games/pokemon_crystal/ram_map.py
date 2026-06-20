"""Dense RAM-based reward for Pokémon Crystal.

Addresses are from the pokecrystal disassembly (English Pokémon Crystal). Crystal
is a Game Boy Color game and keeps its player data in **WRAM bank 1** (the
switchable 0xD000-0xDFFF region), so every read passes ``bank=WRAM_BANK``.

A different game/region/revision needs different addresses — see
`docs/ADDING_GAMES.md` ("Finding RAM addresses") for how to discover/verify them.

``read(emulator)`` pulls raw values; ``reward(values)`` collapses them to [0, 1].
The RamScorer takes the max over the episode, so progress never decreases.
"""

from __future__ import annotations

from typing import Any

WRAM_BANK = 1  # Crystal player data lives in WRAM bank 1 (WRAMX)

# --- WRAM addresses (pokecrystal, English) ----------------------------------
WRAM_PARTY_COUNT = 0xDCD7          # number of Pokémon in party (0..6)
WRAM_PARTY_MON1 = 0xDCDF           # start of party-mon structs
PARTYMON_STRUCT_LEN = 0x30         # 48 bytes per party mon
PARTYMON_LEVEL_OFFSET = 0x1F       # level byte within each struct
WRAM_MONEY = 0xD84E                # 3-byte big-endian *binary* (Gen 2, not BCD)
WRAM_JOHTO_BADGES = 0xD857         # bitfield, 8 Johto badges
WRAM_KANTO_BADGES = 0xD858         # bitfield, 8 Kanto badges

# --- normalization caps -----------------------------------------------------
MAX_LEVEL_SUM = 100.0   # ~ a healthy mid-game party
MAX_MONEY = 99999.0
MAX_BADGES = 16.0       # 8 Johto + 8 Kanto

W_BADGES = 0.5
W_LEVELS = 0.4
W_MONEY = 0.1


def _byte(emulator: Any, addr: int) -> int:
    return emulator.read_memory(addr, bank=WRAM_BANK)


def read(emulator: Any) -> dict[str, Any]:
    party_count = _byte(emulator, WRAM_PARTY_COUNT)
    valid_party = party_count if 0 <= party_count <= 6 else 0

    levels = [
        _byte(emulator, WRAM_PARTY_MON1 + i * PARTYMON_STRUCT_LEN + PARTYMON_LEVEL_OFFSET)
        for i in range(valid_party)
    ]

    badges = bin(_byte(emulator, WRAM_JOHTO_BADGES)).count("1") + bin(
        _byte(emulator, WRAM_KANTO_BADGES)
    ).count("1")

    b0, b1, b2 = (emulator.read_memory(WRAM_MONEY + i, bank=WRAM_BANK) for i in range(3))
    money = (b0 << 16) | (b1 << 8) | b2

    return {
        "party_count": valid_party,
        "levels": levels,
        "level_sum": sum(levels),
        "badges": badges,
        "money": money,
    }


def reward(values: dict[str, Any]) -> float:
    # Only count progress once the player actually has Pokémon — avoids rewarding
    # uninitialized RAM on the title/continue screen.
    if not (1 <= values.get("party_count", 0) <= 6):
        return 0.0

    badges = min(values["badges"], MAX_BADGES) / MAX_BADGES
    levels = min(values["level_sum"], MAX_LEVEL_SUM) / MAX_LEVEL_SUM
    money = min(values["money"], MAX_MONEY) / MAX_MONEY
    return W_BADGES * badges + W_LEVELS * levels + W_MONEY * money
