
from logging import getLogger, StreamHandler, FileHandler, Formatter, INFO, ERROR, WARNING


def init_logger(name :str, with_file:bool=False):
    logger = getLogger(name)

    logger.setLevel(INFO) # loggerがINFOに設定されていると、ハンドラーにもINFO以上のログのみ継承される

    # StreamHandlerの設定
    ch = StreamHandler()
    ch.setLevel(INFO) # ハンドラーにもそれぞれログレベル、フォーマットの設定が可能
    ch_formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.addHandler(ch) # StreamHandlerの追加

    if with_file:
        # FileHandlerの設定
        fh = FileHandler('log/test.log') # 引数には出力ファイルのパスを指定
        fh.setLevel(WARNING) # ハンドラーには、logger以下のログレベルを設定することは出来ない(この場合、DEBUGは不可)
        fh_formatter = Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(funcName)s - %(message)s')
        logger.addHandler(fh) # FileHandlerの追加

    return logger

