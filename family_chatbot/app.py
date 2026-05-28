import threading
import time

from .audio import play_audio
from .config import AppConfig, DEFAULT_SYSTEM_PROMPT
from .family import FamilyStore
from .llm import ChatBrain
from .memory import ConversationMemory
from .search import WebSearch
from .speech import SpeechListener
from .speech_text import prepare_for_speech
from .tts import VoicevoxTTS


def main() -> None:
    config = AppConfig()
    if not config.openai_api_key:
        print("OPENAI_API_KEY が設定されていません。環境変数を設定してから起動してください。")
        return

    memory = ConversationMemory(config.conversation_log_path, DEFAULT_SYSTEM_PROMPT)
    family = FamilyStore.load(config.family_state_path)
    brain = ChatBrain(config, memory, WebSearch(config), family)
    tts = VoicevoxTTS(config)
    listener = SpeechListener(config)

    print("家庭用チャットボットを起動しました。")
    print("入力: 普通に話しかける / voice: 一度だけ音声入力 / listen: 呼びかけ待機 / exit: 終了")

    wakeup_thread: threading.Thread | None = None

    def answer(text: str) -> None:
        print(f"あなた: {text}")
        command_result = family.handle_command(text)
        if command_result.handled:
            response = command_result.message or "うん、できたよ。"
            print(f"チャットボット: {response}")
            speak(response)
            return

        preface = brain.preface_for(text)
        if preface:
            speak(preface)

        response = brain.respond(text)
        print(f"チャットボット: {response}")
        speak(response)

    def speak(text: str) -> None:
        speech_text = prepare_for_speech(text)
        played = False
        for audio_data in tts.synthesize_parts(speech_text):
            played = play_audio(audio_data, config.temp_audio_path) or played
        if not played:
            print("音声合成に失敗したため、テキストのみ表示しました。")

    def start_wakeup_thread() -> None:
        nonlocal wakeup_thread
        if wakeup_thread and wakeup_thread.is_alive():
            print("音声待機はすでに動いています。")
            return
        wakeup_thread = threading.Thread(target=listener.run_wakeup_loop, args=(answer,), daemon=True)
        wakeup_thread.start()

    while True:
        user_input = input("\nあなた: ").strip()
        if not user_input:
            continue

        if user_input.lower() == "exit":
            if listener.is_running:
                listener.stop()
                time.sleep(0.3)
            memory.save()
            print("また話しましょう。")
            break

        if user_input.lower() == "voice":
            voice_text = listener.listen_once()
            if voice_text:
                answer(voice_text)
            continue

        if user_input.lower() == "listen":
            start_wakeup_thread()
            continue

        answer(user_input)
