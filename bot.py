import os
import re
import time
from typing import Set, Dict

# discord モジュール対応
from audioop_stub import ensure_audioop_stub
ensure_audioop_stub()

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from bot_lib import Config, load_replies, pick_reply

load_dotenv()
cfg = Config.from_env()

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True  # 文字メッセージに反応する場合は必須（Dev Portal側でもON）
intents.members = True          # 参加イベント用

bot = commands.Bot(command_prefix="!", intents=intents)

# Slashコマンド用ツリー
tree = bot.tree

# ギルド限定の状態（ON/OFF）
greet_enabled_by_guild: Dict[int, bool] = {}
# ユーザー単位のクールダウン
last_greet_ts_by_user: Dict[int, float] = {}

def is_target_channel(channel_id: int) -> bool:
    if not cfg.channel_ids:
        return True  # 未指定なら全チャンネル対象
    return channel_id in cfg.channel_ids

def is_greet_enabled(guild_id: int) -> bool:
    # 初期値 True（必要ならFalse始まりに変更）
    return greet_enabled_by_guild.get(guild_id, True)

@bot.event
async def on_ready():
    # ギルド限定でコマンド同期
    try:
        guild = discord.Object(id=cfg.guild_id)
        tree.copy_global_to(guild=guild)  # 既存定義をギルドにコピー
        await tree.sync(guild=guild)
        print(f"✅ Logged in as {bot.user} / Commands synced to guild {cfg.guild_id}")
    except Exception as e:
        print("Slashコマンド同期に失敗:", e)

@bot.event
async def on_member_join(member: discord.Member):
    if cfg.welcome_channel_id and member.guild.id == cfg.guild_id:
        channel = member.guild.get_channel(cfg.welcome_channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(f"ようこそ {member.mention} さん！ここは 172交流サーバーですよ。挨拶してね🎮")

@bot.event
async def on_message(message: discord.Message):
    # 自分やBotは無視
    if message.author.bot:
        return
    if message.guild is None:
        return
    if message.guild.id != cfg.guild_id:
        return

    # リプライまたはメンションがBot宛かどうか
    is_reply_to_bot = False
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        is_reply_to_bot = message.reference.resolved.author == bot.user

    is_mention_to_bot = bot.user in message.mentions

    if not is_target_channel(message.channel.id):
        return
    if not is_greet_enabled(message.guild.id):
        return
    # どちらかに当てはまらなければ無視（※全チャンネル対象の場合）
    if not (is_reply_to_bot or is_mention_to_bot):
        return
    content = message.content.strip()
    if not content:
        return

    # 挨拶検出
    now = time.time()
    last = last_greet_ts_by_user.get(message.author.id, 0.0)
    if now - last < cfg.cooldown_seconds:
        return  # クールダウン中はスルー
    last_greet_ts_by_user[message.author.id] = now

    default_templates = load_replies("replies_default.txt")
    # コンテキスト（必要に応じて増やせます）
    ctx = {
        "mention": message.author.mention,
        "display_name": message.author.display_name,
    }

    text = pick_reply(default_templates, ctx)

    await message.reply(text, mention_author=True)

# ── Slash Commands ────────────────────────────────────────────────────────────
@tree.command(name="greet", description="挨拶返信の設定とテスト")
@app_commands.describe(action="on/off/test")
@app_commands.choices(action=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
    app_commands.Choice(name="test", value="test")
])
async def greet_command(interaction: discord.Interaction, action: app_commands.Choice[str]):
    if interaction.guild is None or interaction.guild.id != cfg.guild_id:
        await interaction.response.send_message("このサーバーでは使えません。", ephemeral=True)
        return

    if action.value == "on":
        greet_enabled_by_guild[interaction.guild.id] = True
        await interaction.response.send_message("挨拶返信：ON にしました。", ephemeral=True)
    elif action.value == "off":
        greet_enabled_by_guild[interaction.guild.id] = False
        await interaction.response.send_message("挨拶返信：OFF にしました。", ephemeral=True)
    else:  # test
        await interaction.response.send_message("テストOK！ここで挨拶すると返信しますよ🎉", ephemeral=True)


if __name__ == "__main__":
    if not cfg.token or not cfg.guild_id:
        raise RuntimeError("DISCORD_TOKEN と GUILD_ID を設定してください。")
    bot.run(cfg.token)
