import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Set, Optional, List
import asyncio

# discord モジュール対応
from audioop_stub import ensure_audioop_stub
ensure_audioop_stub()

from dotenv import load_dotenv

from bot_lib import Config, bot_main

from pk_log import init_logger
logger = init_logger(__name__, with_file=True)


def load_discord_config() -> Config:

    """
    172 Discordへログイン
    :return:
    """
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


def main():
    load_dotenv()
    cfg = load_discord_config()
    if not cfg.token or not cfg.guild_id:
        raise RuntimeError("DISCORD_TOKEN と GUILD_ID を設定してください。")
    asyncio.run(bot_main(cfg))


if __name__ == "__main__":
    main()
