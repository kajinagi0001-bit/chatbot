import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    serp_api_key: str | None = os.getenv("SERP_API_KEY")
    tts_quest_api_key: str | None = os.getenv("TTS_QUEST_API_KEY")

    llm_model: str = os.getenv("CHATBOT_LLM_MODEL", "gpt-4o-mini")
    speech_language: str = os.getenv("CHATBOT_SPEECH_LANGUAGE", "ja-JP")
    voicevox_speaker_id: int = int(os.getenv("CHATBOT_VOICEVOX_SPEAKER_ID", "3"))

    listening_timeout_seconds: int = int(os.getenv("CHATBOT_LISTENING_TIMEOUT", "10"))
    idle_listen_timeout_seconds: int = int(os.getenv("CHATBOT_IDLE_TIMEOUT", "10"))
    speech_energy_threshold: int = int(os.getenv("CHATBOT_ENERGY_THRESHOLD", "400"))

    conversation_log_path: Path = PROJECT_ROOT / "conversation_log.json"
    temp_audio_path: Path = Path(gettempdir()) / "family_chatbot_output.wav"

    save_interval_turns: int = 5
    summary_interval_turns: int = 40
    max_response_tokens: int = 260


WAKEUP_PHRASES = ["ねえ", "おはよう", "こんにちは", "こんばんは", "チャットさん"]
EXIT_PHRASES = ["またね", "おしまい", "終了", "バイバイ", "待ってて"]

DEFAULT_FEEDBACK = (
    "短く自然に話してください。家の中で一緒に過ごす家族のように、"
    "押しつけず、必要なときは具体的に手伝ってください。"
)

DEFAULT_SYSTEM_PROMPT = (
    "あなたは家庭で使われる、あたたかく落ち着いたAIチャットボットです。"
    "ユーザーを新しい家族のように支えます。"
    "雑談、相談、予定の整理、調べもの、気分転換を手伝います。"
    "返答は日本語で、音声再生しやすい長さにします。"
    "知らないことは推測で断言せず、必要なら検索を提案します。"
    f"会話スタイル: {DEFAULT_FEEDBACK}"
)
