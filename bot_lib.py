# Python
import os
import re
import time
import random
from dataclasses import dataclass
from typing import Dict, Set, Optional

@dataclass(frozen=True)
class Config:
    """
    Discordボットの設定を表すデータクラスです。
    """
    token: str
    guild_id: int
    welcome_channel_id: Optional[int]
    channel_ids: Set[int]
    cooldown_seconds: int

    @staticmethod
    def from_env() -> "Config":
        token = os.getenv("DISCORD_TOKEN") or ""
        guild_id = int(os.getenv("GUILD_ID", "0"))
        welcome_env = os.getenv("WELCOME_CHANNEL_ID")
        welcome_channel_id = int(welcome_env) if (welcome_env and welcome_env.isdigit()) else None
        channel_ids = {
            int(x) for x in os.getenv("CHANNEL_IDS", "").split(",") if x.strip().isdigit()
        }
        cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", "60"))
        return Config(
            token=token,
            guild_id=guild_id,
            welcome_channel_id=welcome_channel_id,
            channel_ids=channel_ids,
            cooldown_seconds=cooldown_seconds,
        )


def is_target_channel(channel_id: int, channel_ids: Set[int]) -> bool:
    return True if not channel_ids else (channel_id in channel_ids)


class SafeDict(dict):
    def __missing__(self, key):
        # 未知のプレースホルダはそのまま残す
        return "{" + key + "}"


def load_replies(path: str) -> list[str]:
    replies = []
    if not os.path.isfile(path):
        return replies
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip("\n")
            if not s or s.lstrip().startswith("#"):
                continue
            replies.append(s)
    return replies

def pick_reply(templates: list[str], context: dict) -> str | None:
    if not templates:
        return None
    tpl = random.choice(templates)
    return tpl.format_map(SafeDict(context))
