import os
import re
import time
import sys
import types
from typing import Set, Dict
import random


# ── Python 3.13 互換のための audioop スタブ ─────────────────────────────────────
# Python 3.13 では audioop が削除され、discord.py の内部 import で失敗します。
# ボイス機能を使わない場合の起動回避用に最小限のスタブを用意します。
# 将来的に音声機能を使う場合は Python 3.12 へ切替 or 正式な audioop 実装をご利用ください。
try:
    import audioop as _audioop  # noqa: F401
except Exception:
    mod = types.ModuleType("audioop")

    class AudioopError(Exception):
        pass

    mod.error = AudioopError

    # パススルー系（データをそのまま返す）。discord.py が import だけ行うケースを想定。
    def _passthrough(fragment, *args, **kwargs):
        return fragment

    # rate 変換の戻り値は (fragment, state) が期待されることがあるためタプルで返す。
    def _ratecv(fragment, *args, **kwargs):
        return fragment, None

    # ADPCM 系は (fragment, state) を返すことがある
    def _adpcm_passthrough(fragment, *args, **kwargs):
        return fragment, None

    # よく使われる可能性のある関数のみ定義（不足したら追加）
    mod.mul = _passthrough
    mod.add = _passthrough
    mod.lin2lin = _passthrough
    mod.ratecv = _ratecv
    mod.tomono = _passthrough
    mod.tostereo = _passthrough
    mod.ulaw2lin = _passthrough
    mod.lin2ulaw = _passthrough
    mod.adpcm2lin = _adpcm_passthrough
    mod.lin2adpcm = _adpcm_passthrough

    sys.modules["audioop"] = mod

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0")) if os.getenv("WELCOME_CHANNEL_ID") else None
CHANNEL_IDS = {int(x) for x in os.getenv("CHANNEL_IDS", "").split(",") if x.strip().isdigit()}
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "60"))

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

# 反応する挨拶パターン（日本語/英語、ゆるめ正規表現）
GREET_PATTERNS = [
    r"\bhi+\b", r"\bhello+\b", r"\bhey+\b", r"\byo+\b",
    r"こん(?:にち|ちは)", r"おは(?:よ|よう)", r"こんば(?:ん|わ)は", r"やあ", r"やほ", r"はろー?", r"ﾊﾛｰ"
]
GREET_REGEX = re.compile("|".join(f"(?:{p})" for p in GREET_PATTERNS), re.IGNORECASE)

def is_target_channel(channel_id: int) -> bool:
    if not CHANNEL_IDS:
        return True  # 未指定なら全チャンネル対象
    return channel_id in CHANNEL_IDS

def is_greet_enabled(guild_id: int) -> bool:
    # 初期値 True（必要ならFalse始まりに変更）
    return greet_enabled_by_guild.get(guild_id, True)

@bot.event
async def on_ready():
    # ギルド限定でコマンド同期
    try:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)  # 既存定義をギルドにコピー
        await tree.sync(guild=guild)
        print(f"✅ Logged in as {bot.user} / Commands synced to guild {GUILD_ID}")
    except Exception as e:
        print("Slashコマンド同期に失敗:", e)

@bot.event
async def on_member_join(member: discord.Member):
    if WELCOME_CHANNEL_ID and member.guild.id == GUILD_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(f"ようこそ {member.mention} さん！ここは 172交流サーバーですよ。挨拶してね🎮")

@bot.event
async def on_message(message: discord.Message):
    # 自分やBotは無視
    if message.author.bot:
        return
    if message.guild is None:
        return
    if message.guild.id != GUILD_ID:
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
    if now - last < COOLDOWN_SECONDS:
        return  # クールダウン中はスルー
    last_greet_ts_by_user[message.author.id] = now

    # 返信文を少しバリエーション
    replies = [
        f"{message.author.display_name} さんいらっしゃい！今日も楽しんでこー！",
        f"それで、{message.author.display_name}さんは女の子？",
        f"はーい、じゃむさんですよー",
        f"きりりん呼んできてー",
        f"人妻と(荒野行動)やるわ",
        f"淫夢....いい響きだ",
        f"♂ばっかりやし…",
        f"文字起こし禁止！！",
        f"おはにょー",
    ]

    text = random.choice(replies)

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
    if interaction.guild is None or interaction.guild.id != GUILD_ID:
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
    if not TOKEN or not GUILD_ID:
        raise RuntimeError("DISCORD_TOKEN と GUILD_ID を設定してください。")
    bot.run(TOKEN)
