import shutil
import threading
import time
from collections.abc import Callable

import speech_recognition as sr

from .audio import BeepSound
from .config import AppConfig, EXIT_PHRASES, WAKEUP_PHRASES


class SpeechListener:
    def __init__(self, config: AppConfig):
        self.config = config
        self.has_flac = shutil.which("flac") is not None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = config.speech_energy_threshold
        self.recognizer.dynamic_energy_threshold = False

        self.is_running = False
        self.is_active = False
        self.cancel_listening = threading.Event()
        self.listen_thread: threading.Thread | None = None

        self.ready_beep = BeepSound(frequency=1200)
        self.done_beep = BeepSound(frequency=1000)
        self.sleep_beep = BeepSound(frequency=800)

    def listen_once(self, timeout: int | None = None) -> str | None:
        self.ready_beep.play()
        text = self._listen_with_timeout(timeout or self.config.listening_timeout_seconds)
        if text:
            self.done_beep.play()
        else:
            self.sleep_beep.play(times=2)
        return text

    def run_wakeup_loop(self, on_speech: Callable[[str], None]) -> None:
        if not self.has_flac:
            print("音声認識に必要な flac が見つかりません。Raspberry Piで `sudo apt install -y flac` を実行してください。")
            return

        self.is_running = True
        print("音声待機を開始しました。呼びかけると会話を始めます。")
        self.done_beep.play()

        while self.is_running:
            try:
                text = self._listen_with_timeout(self.config.idle_listen_timeout_seconds)
                if not text:
                    continue
                if self._contains_any_phrase(text, WAKEUP_PHRASES):
                    self._run_active_loop(on_speech)
            except KeyboardInterrupt:
                self.stop()
            except Exception as error:
                print(f"音声待機中にエラーが発生しました: {error}")
                time.sleep(1)

    def stop(self) -> None:
        self.is_running = False
        self.is_active = False
        self.cancel_listening.set()
        self.sleep_beep.play(times=2)

    def _run_active_loop(self, on_speech: Callable[[str], None]) -> None:
        self.is_active = True
        silence_count = 0
        self.ready_beep.play()
        print("聞いています。")

        while self.is_running and self.is_active:
            text = self._listen_with_timeout(self.config.listening_timeout_seconds)
            if not text:
                silence_count += 1
                if silence_count <= self.config.active_silence_retries:
                    print("もう少し待っています。")
                    continue
                print("反応がないため待機に戻ります。")
                self._return_to_idle()
                return
            if self._contains_any_phrase(text, EXIT_PHRASES):
                print("待機に戻ります。")
                self._return_to_idle()
                return
            silence_count = 0
            on_speech(text)

    def _return_to_idle(self) -> None:
        self.is_active = False
        self.sleep_beep.play(times=2)

    def _listen_with_timeout(self, timeout: int) -> str | None:
        if not self.has_flac:
            print("音声認識に必要な flac が見つかりません。Raspberry Piで `sudo apt install -y flac` を実行してください。")
            return None

        self.cancel_listening.clear()
        result = [None]

        def listen_worker() -> None:
            try:
                with sr.Microphone() as source:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
                if self.cancel_listening.is_set():
                    return
                result[0] = self.recognizer.recognize_google(audio, language=self.config.speech_language)
                print(f"認識: {result[0]}")
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                print("音声を聞き取れませんでした。")
            except sr.RequestError as error:
                print(f"音声認識サービスでエラーが発生しました: {error}")
            except Exception as error:
                print(f"音声入力でエラーが発生しました: {error}")

        self.listen_thread = threading.Thread(target=listen_worker, daemon=True)
        self.listen_thread.start()
        self.listen_thread.join(timeout + 1)

        if self.listen_thread.is_alive():
            self.cancel_listening.set()
            return None
        return result[0]

    @staticmethod
    def _contains_any_phrase(text: str, phrases: list[str]) -> bool:
        normalized = text.lower().replace("、", "").replace("。", "").replace("!", "").replace("?", "")
        return any(phrase in normalized for phrase in phrases)
