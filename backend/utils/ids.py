from __future__ import annotations

import uuid


def new_id(prefix: str = "") -> str:
    token = uuid.uuid4().hex
    return f"{prefix}_{token}" if prefix else token
