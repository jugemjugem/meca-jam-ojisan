# Python
import os
import re
import time
import random
from dataclasses import dataclass
from typing import Dict, Set, Optional, List, Callable, override
from collections.abc import Generator

from pk_log import init_logger

logger = init_logger(__name__)


@dataclass(frozen=True)
class Omikuji:
    """
    おみくじの情報を保持するデータクラス。
    """

    name: str      # くじの名前 (例: "てと吉")
    attribute: str # 属性 (例: "属性：悪役令嬢")
    state: str     # 状態 (例: "状態：運命掌握中")
    emoji: str     # 絵文字 (例: "🌸 てと吉")
    lack: str      # 普通のおみくじの、小吉とか末吉とか。
    description: str # おみくじの説明文

# おみくじの Null オブジェクト
HAZURE_OMIKUJI = Omikuji("ハズレ", "失敗", "デバッグ中", "💥", "大凶", "エラーでありんす")


class OmikujiReader(object):
    """
    おみくじの入力に関するクラス

    使い方：
        おみくじを１つづつ取得するオブジェクト
    """

    def omikuji_gen(self) -> Generator[Omikuji, None, None]:
        """
        単純に１つ返す
        :return: はずれを１つ返す
        """
        yield HAZURE_OMIKUJI


class OmikujiWriter(object):
    """
    おみくじの出力に関するクラス
    """

    async def print_omikuji(self, omikuji: Omikuji):
        OmikujiWriter.default_omikuji_printer(omikuji)

    @staticmethod
    def default_omikuji_printer(omikuji: Omikuji):
        """
        Omikuji を印刷するデフォルト関数
        設定されていないときは、コンソールに出力する

        :param omikuji: An instance of the Omikuji class containing details such as name,
                        attribute, state, lack, description, and associated emoji.
        :type omikuji: Omikuji
        :return: None
        """
        print(f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃　　　　１７２　うらない       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃{omikuji.emoji} {omikuji.name}
┃属性：{omikuji.attribute}
┃状態：{omikuji.state}
┃くじ：{omikuji.lack}
┃{omikuji.description}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━""")


class FileOmikujiReader(OmikujiReader):
    """
    おみくじファイルから、リスト読み取りして返するクラス
    """

    default_file_name: str = "omikuji-txt.txt"

    def __init__(self, file_name: Optional[str] = None):
        """
        :param file_name: おみくじファイルのパス
        """
        self._file_name:str = file_name if file_name else FileOmikujiReader.default_file_name

    def __str__(self):
        return f"{self.__class__.__name__}(file_name={self._file_name})"

    @override
    def omikuji_gen(self) -> Generator[Omikuji, None, None]:

        """
        おみくじファイルを読み込み、Omikujiオブジェクトのリストを返します。


        :return: 読み込まれた、おみくじ配列
        """
        results: List[Omikuji] = []
        try:
            if not os.path.isfile(self._file_name):
                yield HAZURE_OMIKUJI

            with open(self._file_name, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            # 3行1セットで処理 (1:名前/絵文字/属性, 2:状態, 3:説明)
            for i in range(0, len(lines) - 2, 3):
                try:
                    # 1行目: "🌸 てと吉" と "属性：悪役令嬢" が混在している、
                    # あるいは改行されている可能性を考慮したパース
                    line1 = lines[i]
                    line2 = lines[i + 1]
                    line3 = lines[i + 2]

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
                        attr = "不明"  # 1行目に属性がない場合
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
            with open(self._file_name, "r", encoding="utf-8") as f:
                content = [l.strip() for l in f if l.strip()]

            for i in range(0, len(content) - 3, 4):
                header = content[i]  # "🌸 てと吉"
                attr_line = content[i + 1]  # "属性：..."
                state_line = content[i + 2]  # "状態：..."
                desc = content[i + 3]  # "説明..."

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
            yield from results
        except Exception as e:
            logger.error(f"Error loading omikuji file {self._file_name}: {e}")
            yield HAZURE_OMIKUJI


class OmikujiIterator(object):
    """
    おみくじ List[Omikuji]　をループするためのWrapperIterator
    """
    def __init__(self, omikuji_data: List[Omikuji]):
        self._omikuji_data: List[Omikuji] = omikuji_data
        self._index: int = 0


    def __next__(self) -> Omikuji:
        if self._index >= len(self._omikuji_data):
            raise StopIteration
        omikuji = self._omikuji_data[self._index]
        self._index += 1
        return omikuji


class OmikujiDealer:
    """
    おみくじを管理するオブジェクト
    """

    def __init__(self,*,
                 reader: OmikujiReader = OmikujiReader(),
                 writer: OmikujiWriter = OmikujiWriter()
                 ):
        """
        普通のコンストラクタ
        :param reader: 読み込む人
        :param writer: 書き込む人
        """
        self._omikuji_reader: OmikujiReader = reader
        self._omikuji_writer: OmikujiWriter = writer
        self._omikuji_data: List[Omikuji] = []

    def __len__(self):
        return len(self._omikuji_data)

    def __iter__(self) -> OmikujiIterator:
        return OmikujiIterator(self._omikuji_data)


    def load_omikuji(self, new_reader: Optional[OmikujiReader]=None) -> bool:
        """
        おみくじファイル、読み込みなおす
        :param new_reader: 新しく読み込む元 -- Noneのばあい、以前のものから再読み込み
        :return: 成否
        """
        try:
            logger.info(f"ℹ️ Loading omikuji with {new_reader}")
            if new_reader:
                # 新しいものが設定されたら、それ。
                # ELSE、以前のものから再読み込み
                self._omikuji_reader = new_reader
            self._omikuji_data = list(self._omikuji_reader.omikuji_gen())

            return len(self._omikuji_data)>0  # 空っぽじゃなければOK
        except Exception as e:
            logger.error(f"❌ Error loading omikuji file {self._omikuji_reader}: {e}")
            return False

    def do_omikuji(self,*,
                   index:Optional[int]=None
                   ):
        """
        おみくじを引いて、Printするのをまとめただけの関数
        :return:  None
        """
        temp = self.pick_omikuji(index=index)
        self.print_omikuji(temp)

    def pick_omikuji(self,*,
                     index:Optional[int]=None
                     ) -> Omikuji:
        """
        おみくじを引く
        :param index: 引くおみくじのindex -- NULL ならば、ランダム選択
        :return: おみくじ item -- 読み込まれていないときは、ハズレを返す
        """
        if not self._omikuji_data:
            return HAZURE_OMIKUJI
        if index is not None:
            # index 指定ならそのおみくじを持ってくる
            return self._omikuji_data[index]
        else:
            # 指定されていなければ、ランダム選択
            return random.choice(self._omikuji_data)

    async def print_omikuji(self, omikuji: Omikuji):
        await self._omikuji_writer.print_omikuji(omikuji)

    def replace_printer(self, writer: OmikujiWriter):
        self._omikuji_writer = writer


def test_func2():
    print("test2")
    dealer = OmikujiDealer(reader=FileOmikujiReader("omikuji-txt.txt"),)
    dealer.load_omikuji(None)

    for x in dealer:
        print(x)
        dealer.print_omikuji(x)
    print("-----------------------------------------------------------")
    dealer.do_omikuji()
    dealer.do_omikuji()
    dealer.do_omikuji()

if __name__ == "__main__":
    test_func2()
