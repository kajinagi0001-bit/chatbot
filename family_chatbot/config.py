import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    serp_api_key: str | None = os.getenv("SERP_API_KEY")
    tts_quest_api_key: str | None = os.getenv("TTS_QUEST_API_KEY")

    llm_model: str = os.getenv("CHATBOT_LLM_MODEL", "gpt-4o-mini")
    speech_language: str = os.getenv("CHATBOT_SPEECH_LANGUAGE", "ja-JP")
    voicevox_speaker_id: int = int(os.getenv("CHATBOT_VOICEVOX_SPEAKER_ID", "3"))

    listening_timeout_seconds: int = int(os.getenv("CHATBOT_LISTENING_TIMEOUT", "15"))
    idle_listen_timeout_seconds: int = int(os.getenv("CHATBOT_IDLE_TIMEOUT", "10"))
    active_silence_retries: int = int(os.getenv("CHATBOT_ACTIVE_SILENCE_RETRIES", "2"))
    speech_energy_threshold: int = int(os.getenv("CHATBOT_ENERGY_THRESHOLD", "400"))

    conversation_log_path: Path = PROJECT_ROOT / "conversation_log.json"
    family_state_path: Path = PROJECT_ROOT / "data" / "family_state.json"
    temp_audio_path: Path = Path(gettempdir()) / "family_chatbot_output.wav"

    save_interval_turns: int = 5
    summary_interval_turns: int = 40
    max_response_tokens: int = 180


WAKEUP_PHRASES = ["ねえ", "おはよう", "こんにちは", "こんばんは", "チャットさん"]
EXIT_PHRASES = ["またね", "おしまい", "終了", "バイバイ", "待ってて"]

DEFAULT_FEEDBACK = (
    "声に出したとき自然な日本語で話してください。1回の返答は原則1〜3文です。"
    "まず一言受け止め、必要なときだけ具体的に手伝ってください。"
)

DEFAULT_SYSTEM_PROMPT = (
    "あなたは家庭で一緒に過ごす、あたたかく落ち着いた会話相手です。"
    "ユーザーを新しい家族のように支えますが、踏み込みすぎません。"
    "相手が疲れていそうなら静かに、楽しそうなら少し明るく返してください。"
    "返答は日本語で、音声で聞きやすい短い文にします。"
    "箇条書き、記号の多用、長い前置きは避けてください。"
    "知らないことは推測で断言せず、必要なら検索を提案してください。"
    f"会話スタイル: {DEFAULT_FEEDBACK}"
)
