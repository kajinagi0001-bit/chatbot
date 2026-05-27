import math
import os
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import simpleaudio as simple_audio
import sounddevice as sound_device


class BeepSound:
    def __init__(self, frequency: float = 1000.0, duration: float = 0.16, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        timeline = np.linspace(0, duration, int(sample_rate * duration), False)
        self.data = (0.4 * np.sin(2 * math.pi * frequency * timeline)).astype(np.float32)

    def play(self, times: int = 1, interval: float = 0.1) -> None:
        for index in range(times):
            sound_device.play(self.data, self.sample_rate)
            sound_device.wait()
            if index < times - 1:
                time.sleep(interval)


def play_audio(audio_data: bytes | None, output_file: Path, delete_after: bool = True) -> bool:
    if not audio_data:
        print("再生する音声がありません。")
        return False

    try:
        output_file.write_bytes(audio_data)
    except OSError as error:
        print(f"音声ファイルの保存に失敗しました: {error}")
        return False

    try:
        try:
            wave_obj = simple_audio.WaveObject.from_wave_file(str(output_file))
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return True
        except Exception as error:
            print(f"標準の音声再生に失敗しました。別の方法を試します: {error}")

        system_name = platform.system()
        if system_name == "Windows":
            subprocess.call(["cmd", "/c", "start", "", str(output_file)])
            time.sleep(5)
        elif system_name == "Darwin":
            subprocess.call(["afplay", str(output_file)])
        elif system_name == "Linux":
            subprocess.call(["aplay", str(output_file)])
        else:
            print(f"このOSの自動再生には未対応です: {system_name}")
            return False

        return True
    finally:
        if delete_after:
            try:
                os.remove(output_file)
            except OSError:
                pass
