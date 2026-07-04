# -*- coding: utf-8 -*-
"""Keep-awake: 学習中のPCスリープを防止する(caffeine相当)。

SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) をプロセス生存中
維持する。ディスプレイは消えてよい(ES_DISPLAY_REQUIREDは立てない)。
単体起動のほか、motion_learning_supervisor が自動で有効化する。
"""
import ctypes, time, sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def hold_awake():
    if sys.platform != "win32":
        return False
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    return True


if __name__ == "__main__":
    if hold_awake():
        print("keep-awake active (system sleep inhibited while this process runs)")
        while True:
            time.sleep(300)
            hold_awake()  # 念のため定期再アサート
