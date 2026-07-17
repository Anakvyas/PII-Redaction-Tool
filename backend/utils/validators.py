"""Deterministic format validators used to raise/lower detector confidence."""
from __future__ import annotations


def luhn_is_valid(digits: str) -> bool:
    """Standard Luhn checksum — filters regex-matched digit strings down to
    numbers that are actually structurally valid card numbers."""
    cleaned = [int(c) for c in digits if c.isdigit()]
    if len(cleaned) < 12:
        return False
    checksum = 0
    parity = len(cleaned) % 2
    for i, digit in enumerate(cleaned):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def is_valid_ipv4(candidate: str) -> bool:
    parts = candidate.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not 0 <= int(part) <= 255:
            return False
        if len(part) > 1 and part[0] == "0":
            return False
    return True
