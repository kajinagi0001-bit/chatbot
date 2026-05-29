import io
import queue
import re
import threading
import time

import requests
from pydub import AudioSegment

from .config import AppConfig


def split_for_speech(text: str, max_length: int = 70) -> list[str]:
    pattern = r"(?<=[。！？、\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U00002728])"
    chunks = []
    for sentence in re.split(pattern, text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_length:
            chunks.append(sentence)
            continue
        chunks.extend(sentence[index : index + max_length] for index in range(0, len(sentence), max_length))
    return chunks


class VoicevoxTTS:
    def __init__(self, config: AppConfig):
        self.config = config
        self.speed = min(1.4, max(0.8, config.tts_speed))

    def synthesize(self, text: str) -> bytes | None:
        combined_audio = None

        for chunk in split_for_speech(text):
            audio_segment = self._speed_adjust(self._synthesize_chunk(chunk))
            if audio_segment is None:
                continue
            combined_audio = audio_segment if combined_audio is None else combined_audio + audio_segment

        if combined_audio is None:
            return None

        output = io.BytesIO()
        combined_audio.export(output, format="wav")
        return output.getvalue()

    def synthesize_parts(self, text: str):
        audio_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=2)

        def producer() -> None:
            try:
                for chunk in split_for_speech(text):
                    audio_segment = self._speed_adjust(self._synthesize_chunk(chunk))
                    if audio_segment is None:
                        continue

                    output = io.BytesIO()
                    audio_segment.export(output, format="wav")
                    audio_queue.put(output.getvalue())
            finally:
                audio_queue.put(None)

        threading.Thread(target=producer, daemon=True).start()

        while True:
            audio_data = audio_queue.get()
            if audio_data is None:
                break
            yield audio_data

    def _synthesize_chunk(self, text: str) -> AudioSegment | None:
        try:
            response = requests.get(
                "https://api.tts.quest/v3/voicevox/synthesis",
                params={
                    "text": text,
                    "speaker": self.config.voicevox_speaker_id,
                    "key": self.config.tts_quest_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            print(f"TTSのリクエストに失敗しました: {error}")
            return None

        status_url = data.get("audioStatusUrl")
        download_url = data.get("wavDownloadUrl") or data.get("mp3DownloadUrl")
        if not status_url or not download_url:
            print("TTS APIから音声URLを取得できませんでした。")
            return None

        if not self._wait_until_ready(status_url):
            return None

        try:
            audio_response = requests.get(download_url, timeout=30)
            audio_response.raise_for_status()
            audio_format = "wav" if "wav" in download_url else "mp3"
            return AudioSegment.from_file(io.BytesIO(audio_response.content), format=audio_format)
        except Exception as error:
            print(f"TTS音声の取得に失敗しました: {error}")
            return None

    def _wait_until_ready(self, status_url: str, max_wait_seconds: int = 30) -> bool:
        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            try:
                response = requests.get(status_url, timeout=10)
                response.raise_for_status()
                if response.json().get("isAudioReady"):
                    return True
            except requests.RequestException as error:
                print(f"TTS生成状況の確認に失敗しました: {error}")
                return False
            time.sleep(0.5)

        print("TTS生成がタイムアウトしました。")
        return False

    def _speed_adjust(self, audio_segment: AudioSegment | None) -> AudioSegment | None:
        if audio_segment is None or self.speed == 1.0:
            return audio_segment

        adjusted = audio_segment._spawn(
            audio_segment.raw_data,
            overrides={"frame_rate": int(audio_segment.frame_rate * self.speed)},
        )
        return adjusted.set_frame_rate(audio_segment.frame_rate)
