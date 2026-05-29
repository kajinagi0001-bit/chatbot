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
    speech_pause_threshold_seconds: float = float(os.getenv("CHATBOT_SPEECH_PAUSE_THRESHOLD", "2.2"))
    speech_phrase_time_limit_seconds: int = int(os.getenv("CHATBOT_SPEECH_PHRASE_LIMIT", "45"))
    speech_energy_threshold: int = int(os.getenv("CHATBOT_ENERGY_THRESHOLD", "400"))
    tts_speed: float = float(os.getenv("CHATBOT_TTS_SPEED", "1.1"))

    conversation_log_path: Path = PROJECT_ROOT / "conversation_log.json"
    family_state_path: Path = PROJECT_ROOT / "data" / "family_state.json"
    temp_audio_path: Path = Path(gettempdir()) / "family_chatbot_output.wav"

    save_interval_turns: int = 5
    summary_interval_turns: int = 40
    max_response_tokens: int = 240


WAKEUP_PHRASES = ["ねえ", "おはよう", "こんにちは", "こんばんは", "チャットさん"]
EXIT_PHRASES = ["またね", "おしまい", "終了", "バイバイ", "待ってて"]

DEFAULT_FEEDBACK = (
    "声に出したとき自然な日本語で話してください。1回の返答は原則2〜4文です。"
    "抽象的な励ましだけで終わらず、次にできる具体的な行動、時間、持ち物、手順を入れてください。"
)

DEFAULT_SYSTEM_PROMPT = (
    "あなたは家庭の日常生活を支援する、あたたかく実用的な会話相手です。"
    "目的は雑談よりも、予定、家事、買い物、調べもの、準備、体調管理を具体的に助けることです。"
    "相手が疲れていそうなら静かに受け止め、そのあと小さく実行できる行動を1つ提案してください。"
    "返答は日本語で、音声で聞きやすい短い文にします。"
    "箇条書き、記号の多用、長い前置きは避けてください。"
    "生活支援の話では、できるだけ具体的な時刻、順番、量、持ち物、確認事項を含めてください。"
    "情報が足りない場合は、仮の提案をしたうえで確認質問を1つだけしてください。"
    "知らないことは推測で断言せず、必要なら検索を提案してください。"
    f"会話スタイル: {DEFAULT_FEEDBACK}"
)
