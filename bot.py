import os
import re
import time
from typing import Set, Dict
import asyncio

# discord モジュール対応
from audioop_stub import ensure_audioop_stub
ensure_audioop_stub()

from dotenv import load_dotenv

from bot_lib import Config, bot_main


def main():
    load_dotenv()
    cfg = Config.from_env()
    if not cfg.token or not cfg.guild_id:
        raise RuntimeError("DISCORD_TOKEN と GUILD_ID を設定してください。")
    asyncio.run(bot_main(cfg))


if __name__ == "__main__":
    main()
