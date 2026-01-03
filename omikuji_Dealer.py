# Python
import os
import re
import time
import random
from dataclasses import dataclass
from typing import Dict, Set, Optional, List

from pk_log import init_logger

logger = init_logger(__name__)

@dataclass(frozen=True)
class Omikuji:
    name: str
    attribute: str
    state: str
    emoji: str
    lack: str
    description: str

def load_omikuji(path: str) -> List[Omikuji]:
    """
    おみくじファイルを読み込み、Omikujiオブジェクトのリストを返します。
    """
    results = []
    if not os.path.isfile(path):
        return results

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # 3行1セットで処理 (1:名前/絵文字/属性, 2:状態, 3:説明)
    for i in range(0, len(lines) - 2, 3):
        try:
            # 1行目: "🌸 てと吉" と "属性：悪役令嬢" が混在している、
            # あるいは改行されている可能性を考慮したパース
            line1 = lines[i]
            line2 = lines[i+1]
            line3 = lines[i+2]

            # 絵文字と名前を分離 (例: "🌸 てと吉")
            match_name = re.match(r"(\S+)\s+(.+)", line1)
            emoji = match_name.group(1) if match_name else "🔮"
            name = match_name.group(2) if match_name else line1

            # 属性 (例: "属性：悪役令嬢")
            attr = line2.replace("属性：", "")
            # 状態 (例: "状態：運命掌握中")
            # ファイル構造が 属性・状態・説明 の順なので、line2, line3から抽出
            state = ""
            desc = line3
            
            # もしファイルが「属性」「状態」の2行に分かれている場合を想定した調整
            if "状態：" in line2:
                state = line2.replace("状態：", "")
                attr = "不明" # 1行目に属性がない場合
            elif "状態：" in line3:
                state = line3.replace("状態：", "")
                # その次の行が説明になるはずなので、インデックスを調整するか
                # ファイルが3行固定なら line2=属性, line3=状態 とみなす
                pass

            # 今回のテキスト形式(名前行、属性行、状態行、説明行)に合わせて厳密にやるなら:
            # 実際のテキストは 1:名前, 2:属性, 3:状態, 4:説明 の4行構成に見えます。
            # 添付されたテキストを確認し、4行1セットでループ回します。
        except Exception as e:
            logger.error(f"Error parsing omikuji line {i}: {e}")
            continue
            
    # シンプルに、現在の omikuji-txt.txt の構造（名前、属性、状態、説明の4行）に合わせて再定義
    results = []
    content = []
    with open(path, "r", encoding="utf-8") as f:
        content = [l.strip() for l in f if l.strip()]
    
    for i in range(0, len(content) - 3, 4):
        header = content[i] # "🌸 てと吉"
        attr_line = content[i+1] # "属性：..."
        state_line = content[i+2] # "状態：..."
        desc = content[i+3] # "説明..."
        
        m = re.match(r"(\S+)\s+(.+)", header)
        emoji = m.group(1) if m else "🔮"
        name = m.group(2) if m else header
        
        results.append(Omikuji(
            name=name,
            attribute=attr_line.replace("属性：", ""),
            state=state_line.replace("状態：", ""),
            emoji=emoji,
            lack="大吉",
            description=desc
        ))
    return results

# グローバルまたはクラス内でロード
OMIKUJI_DATA = load_omikuji("omikuji-txt.txt")

def pick_omikuji() -> Optional[Omikuji]:
    if not OMIKUJI_DATA:
        return None
    return random.choice(OMIKUJI_DATA)

def format_omikuji(omikuji: Omikuji) -> str:
    return f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃　　　　１７２　うらない       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃{omikuji.emoji} {omikuji.name}
┃属性：{omikuji.attribute}
┃状態：{omikuji.state}
┃くじ：{omikuji.lack}
┃{omikuji.description}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def test_func():
    print("test")
    print(format_omikuji(pick_omikuji()))
    print(format_omikuji(pick_omikuji()))
    print(format_omikuji(pick_omikuji()))

if __name__ == "__main__":
    test_func()
