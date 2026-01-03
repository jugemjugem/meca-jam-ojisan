# Python
import os
import re
import time
import random
from dataclasses import dataclass
from typing import Dict, Set, Optional, List

# discord モジュール対応
from audioop_stub import ensure_audioop_stub
from omikuji_Dealer import pick_omikuji

ensure_audioop_stub()

import discord
from discord.ext import commands
from discord import app_commands

import asyncio

from pk_log import init_logger

logger = init_logger(__name__)

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

#######################################################


# 反応する挨拶パターン（日本語/英語、ゆるめ正規表現）
GREET_PATTERNS = [
    r"\bhi+\b", r"\bhello+\b", r"\bhey+\b", r"\byo+\b",
    r"こん(?:にち|ちは)", r"おは(?:よ|よう)", r"こんば(?:ん|わ)は", r"やあ", r"やほ", r"はろー?", r"ﾊﾛｰ"
    ,r"ちーっす"
    , r"ちっす"
]
GREET_REGEX = re.compile("|".join(f"(?:{p})" for p in GREET_PATTERNS), re.IGNORECASE)

class BotContext(commands.Cog):
    """BotContextクラスは、Botのコンテキスト情報を保持するためのクラスです。
    """

    def __init__(self, bot: commands.Bot, cfg: Config):
        self.bot = bot
        self.cfg = cfg
        self.greet_enabled_by_guild: Dict[int, bool] = {}
        self.last_greet_ts_by_user: Dict[int, float] = {}

    def is_greet_enabled(self, guild_id: int) -> bool:
        return self.greet_enabled_by_guild.get(guild_id, True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバーがサーバーに参加したときに呼び出されるイベントリスナーです。

        :param member: 参加したメンバーの情報
        :return: None
        """
        logger.debug("on_member_join begin")
        if self.cfg.welcome_channel_id and member.guild.id == self.cfg.guild_id:
            channel = member.guild.get_channel(self.cfg.welcome_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(f"ようこそ {member.mention} さん！ここは 172 のゲーム広場、気軽に挨拶してね🎮")
        logger.debug("on_member_join end")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 自分やBotは無視
        if message.author.bot:
            return
        if message.guild is None or message.guild.id != self.cfg.guild_id:
            return

        if not is_target_channel(message.channel.id, self.cfg.channel_ids):
            return

        content = (message.content or "").strip()
        if not content:
            # メッセージが空っぽなので、無視
            return

        logger.debug("on_message begin")
        # リプライまたはメンションがBot宛かどうか
        is_reply_to_bot = False
        if message.reference and isinstance(message.reference.resolved, discord.Message):
            is_reply_to_bot = message.reference.resolved.author == self.bot.user

        is_mention_to_bot = self.bot.user in message.mentions
        now = time.time()

        last = self.last_greet_ts_by_user.get(message.author.id, 0.0)
        if now - last < self.cfg.cooldown_seconds:
            logger.debug("on_message ... cooldown end")
            return  # クールダウン中はスルー
        self.last_greet_ts_by_user[message.author.id] = now

        # コンテキスト（必要に応じて増やせます）
        ctx = {
            "mention": message.author.mention,
            "display_name": message.author.display_name,
        }
        if is_reply_to_bot or is_mention_to_bot:
            # お返事
            default_templates = load_replies("replies_default.txt")
            text = pick_reply(default_templates, ctx)
            await message.reply(text, mention_author=True)
            logger.debug(f"on_message response {text} end")
            return
        else:
            # 素のコメント→ お返事対象かちぇっく。
            if not self.is_greet_enabled(message.guild.id):
                logger.debug(f"on_message no greet ... end")
                return

            if GREET_REGEX.search(content):
                # 挨拶検出

                if re.search(r"おは|ohayo|morning", content, re.IGNORECASE):
                    text = f"{message.author.mention} おはよう！朝活いく？☀"
                elif re.search(r"こんば|evening|night", content, re.IGNORECASE):
                    text = f"{message.author.mention} こんばんは！一戦どう？🌙"
                elif re.search(r"hi|hello|hey", content, re.IGNORECASE):
                    text = f"{message.author.mention} Hello! Ready to play? 🎮"
                else:
                    replies = [
                        f"{message.author.mention} いらっしゃい！今日も楽しんでこー！",
                        f"{message.author.mention} こんにちは！どのゲーム行く？",
                        f"{message.author.mention} おはよう！ナイスログイン☀",
                        f"{message.author.mention} こんばんは！集まってるよ〜🌙",
                    ]
                    text = replies[int(now) % len(replies)]

                await message.reply(text, mention_author=True)
                logger.debug(f"on_message greet {text} end")

    # /greet コマンド
    @app_commands.command(name="greet", description="挨拶返信の設定とテスト")
    @app_commands.describe(action="on/off/test")
    @app_commands.choices(action=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
        app_commands.Choice(name="test", value="test"),
    ])
    async def greet_command(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        if interaction.guild is None or interaction.guild.id != self.cfg.guild_id:
            await interaction.response.send_message("このサーバーでは使えません。", ephemeral=True)
            return
        if action.value == "on":
            self.greet_enabled_by_guild[interaction.guild.id] = True
            await interaction.response.send_message("挨拶返信：ON にしました。", ephemeral=True)
        elif action.value == "off":
            self.greet_enabled_by_guild[interaction.guild.id] = False
            await interaction.response.send_message("挨拶返信：OFF にしました。", ephemeral=True)
        else:
            await interaction.response.send_message("テストOK！ここで挨拶すると返信しますよ🎉", ephemeral=True)

    @app_commands.command(name="omikuji", description="今日のおみくじを引きます")
    async def omikuji_command(self, interaction: discord.Interaction):
        result = pick_omikuji()
        if not result:
            await interaction.response.send_message("おみくじの準備ができていないようです。", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⛩️ {interaction.user.display_name}さんの運勢",
            description=f"あなたの今日のタイプは **{result.name}** です！",
            color=discord.Color.random()
        )
        embed.add_field(name="属性", value=result.attribute, inline=True)
        embed.add_field(name="状態", value=result.state, inline=True)
        embed.add_field(name="運勢", value=result.emoji, inline=True)
        embed.add_field(name="お告げ", value=result.description, inline=False)
        embed.set_footer(text=f"運勢絵文字: {result.emoji}")

        await interaction.response.send_message(embed=embed)

async def bot_main(cfg: Config):
    logger.info("bot_main begin")
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def setup_hook() -> None:
        logger.info("setup_hook begin")
        try:
            guild = discord.Object(id=cfg.guild_id)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            logger.info(f"✅ Logged in as {bot.user} / Commands synced to guild {cfg.guild_id}")
        except Exception as e:
            logger.exception(e)
        logger.info("setup_hook end")

    await bot.add_cog(BotContext(bot, cfg))
    await bot.start(cfg.token)
    logger.info("bot_main end")
    pass

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logger.info("bot_main")
    cfg = Config.from_env()
    if not cfg.token or not cfg.guild_id:
        raise RuntimeError("DISCORD_TOKEN と GUILD_ID を設定してください。")
    asyncio.run(bot_main(cfg))
    logger.info("end")
