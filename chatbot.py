import openai
import os
import json
import time
import requests
import re
import io
import subprocess
import platform
from pydub import AudioSegment
from pydub.playback import play
import tempfile
import simpleaudio as sa
import speech_recognition as sr
import numpy as np
import sounddevice as sd
import threading
from typing import List, Optional, Tuple
from openai import OpenAI

#==============================================
# 設定パラメータ（ユーザー変更可能）
#==============================================

# サーバー設定
OPENAI_API_URL = "http://192.168.xxx.xxx:xxxx/v1"  # OpenAI互換APIのURL (ローカルLLM)
TTS_API_URL = "http://192.168.xxx.xxx:xxxx/voice"  # TTS APIのURL
# 有志が公開している無料のVOICEVOX互換WEB APIのエンドポイント
VOICEVOX_API_URL = "https://voicevox.su-shiki.com/api"
openai.api_key = os.getenv("OPENAI_API_KEY") # OpenAI-API（環境変数から取得）
SERP_API_KEY = os.getenv("SERP_API_KEY")  # 検索API（環境変数から取得）

# モデル設定
LLM_MODEL_NAME = "gpt-4o-mini"  # 使用するLLMモデル
TTS_MODEL_NAME = "【モデル名】"        # 使用するTTS音声モデル
TTS_LENGTH = 1                  # 音声の長さ調整 (1以上はゆっくり、1未満は早口になる)
TTS_STYLE_WEIGHT = 1             # 音声スタイルの重み
VOICEVOX_SPEAKER_ID = 3  #  ずんだもん

# 音声認識設定
ASR_LANGUAGE = "ja-JP"           # 音声認識の言語
ASR_ENERGY_THRESHOLD = 4000      # 音声認識の感度
LISTENING_TIMEOUT = 10           # 音声入力待機時間（秒）

# ウェイクアップと終了フレーズ
WAKEUP_PHRASES = ["ねえ", "おはよう", "こんにちは", "こんばんわ", "ねー"]
EXIT_PHRASES = ["じゃあ またね", "じゃあ また今度", "さようなら", "終了", "バイバイ"]

# システムプロンプト設定
DEFAULT_FEEDBACK = "もっと情景を詳しく表現してください。"
DEFAULT_SYSTEM_PROMPT = (
    "あなたは明るく元気なAIアシスタントです！"
    "感情豊かで親しみやすい口調で、ユーザーをサポートします。"
    f"【フィードバック】: {DEFAULT_FEEDBACK}"
)

# 会話ログ設定
CONVERSATION_LOG_FILE = "conversation_log.json"  # 会話履歴ファイル
SUMMARY_INTERVAL = 40            # 何回の会話ごとに要約するか
SAVE_INTERVAL_EPISODES = 5       # 何回の会話ごとに保存するか

# 音声出力設定
OUTPUT_TEMP_DIR = tempfile.gettempdir()
OUTPUT_FILE = os.path.join(OUTPUT_TEMP_DIR, "output.wav")

#==============================================
# 初期化
#==============================================

# OpenAI APIクライアント初期化
client = OpenAI(base_url=OPENAI_API_URL)

#==============================================
# ビープ音モジュール
#==============================================

class BeepSound:
    def __init__(self, frequency=1000.0, duration=0.2, sample_rate=44100):
        self.frequency = frequency
        self.duration = duration
        self.sample_rate = sample_rate

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        self.beep_data = (0.5 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    
    def play(self, times=1, interval=0.1):
        for i in range(times):
            sd.play(self.beep_data, self.sample_rate)
            sd.wait()
            if i < times - 1:
                time.sleep(interval)

#==============================================
# 音声認識モジュール
#==============================================

class ASRModule:
    def __init__(self,
                 language=ASR_LANGUAGE,
                 wakeup_phrases=WAKEUP_PHRASES,
                 exit_phrases=EXIT_PHRASES,
                 idle_timeout=None,
                 listening_timeout=LISTENING_TIMEOUT,
                 energy_threshold=ASR_ENERGY_THRESHOLD,
                 tts_func=None,
                 play_audio_func=None):
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.language = language
        self.wakeup_phrases = [phrase.lower() for phrase in wakeup_phrases]
        self.exit_phrases = [phrase.lower() for phrase in exit_phrases]
        self.idle_timeout = idle_timeout
        self.listening_timeout = listening_timeout
        self.is_active = False
        self.is_running = False
        self.conversation_history = []

        # 音声認識キャンセル用のフラグとスレッド
        self.cancel_listening = threading.Event()
        self.listen_thread = None

        # ビープ音の初期化
        self.beep_sound = BeepSound(frequency=1000)
        self.beep_activate = BeepSound(frequency=1200)
        self.beep_deactivate = BeepSound(frequency=800)

        # コールバック関数
        self.on_wakeup_callback = None
        self.on_exit_callback = None
        self.on_speech_callback = None
        self.tts_func = tts_func
        self.play_audio_func = play_audio_func

    def _normalize_text(self, text):
        """テキストの正規化（小文字化，句読点除去）"""
        if not text:
            return ""
        text = text.lower()
        for char in [',', '.', '!', '?', '、', '。', '！', '？']:
            text = text.replace(char, '')
        return text
    
    def _contains_any_phrase(self, text, phrases):
        """テキストに指定されたフレーズのいずれかが含まれているかチェック"""
        normalized = self._normalize_text(text)
        return any(phrase in normalized for phrase in phrases)
    
    def _listen_with_timeout(self, timeout=None):
        """タイムアウト付きで音声認識を行う"""
        self.cancel_listening.clear()
        result = [None]

        def listen_worker():
            try:
                with sr.Microphone() as source:
                    print("聴いています...")
                    audio = self.recognizer.listen(source, timeout=10 if timeout is None else timeout)

                if self.cancel_listening.is_set():
                    return
                try:
                    text = self.recognizer.recognize_google(audio, language=self.language)
                    result[0] = text
                    print(f"認識: {text}")
                except sr.UnknownValueError:
                    print("音声を認識できませんでした")
                except sr.RequestError as e:
                    print(f"Google Web Speech API エラー")
            except Exception as e:
                print(f"エラー: {e}")
        
        self.listen_thread = threading.Thread(target=listen_worker)
        self.listen_thread.daemon = True
        self.listen_thread.start()

        wait_time = 30 if timeout is None else timeout
        self.listen_thread.join(timeout=wait_time)

        if self.listen_thread.is_alive():
            self.cancel_listening.set()
            print("音声認識がタイムアウトしました")
            return None
        
        return result[0]
    
    def listen_once(self, timeout=None):
        """一度だけ音声認識を行う"""
        print("音声入力を待機中...")
        self.beep_activate.play(times=1)

        result = self._listen_with_timeout(timeout)

        if result:
            self.beep_sound.play(times=1)
        else:
            self.beep_deactivate.play(times=2, interval=0.1)

        return result
    
    def run_idle_mode(self):
        """アイドルモード: ウェイクアップフレーズを待機"""
        print("\n アイドルモード: ウェイクアップフレーズを待っています...")

        while self.is_running:
            try:
                text = self._listen_with_timeout(self.idle_timeout)

                if not text:
                    continue

                if self._contains_any_phrase(text, self.wakeup_phrases):
                    print(f"\n ウェイクアップフレーズが検出されました: {text}")
                    self.beep_activate.play(times=1)

                    if self.on_wakeup_callback:
                        self.on_wakeup_callback()

                    self.run_activate_mode()

            except KeyboardInterrupt:
                print("\n キーボード割り込みで終了します...")
                self.stop()
                break
            except Exception as e:
                print(f"エラー: {e}")
                time.sleep(1)
    
    def run_activate_mode(self):
        """アクティブモード: 会話を聞き取り，終了フレーズまで続ける"""
        self.is_active = True
        print("\n アクティブモード: 会話を聞き取っています... ")
        wakeup_responses = [
            "はい，なんですか？",
            "はい，どうしました？",
            "はい！どうぞ！",
            "なんでしょう？"
        ]
        import random
        wakeup_response = random.choice(wakeup_responses)
        print(f"AI: {wakeup_response}")

        if self.tts_func and self.play_audio_func:
            audio_data = self.tts_func(wakeup_response)
            if audio_data:
                self.play_audio_func(audio_data)

        while self.is_active and self.is_running:
            try:
                text = self._listen_with_timeout(self.listening_timeout)
                
                if not text:
                    print("応答がないためアイドルモードに移ります")
                    self.is_active = False
                    self.beep_deactivate.play(times=2, interval=0.2)

                    if self.on_exit_callback:
                        self.on_exit_callback()

                    break

                if self._contains_any_phrase(text, self.exit_phrases):
                    print(f"\n 終了フレーズが検出されました: {text}")
                    self.is_active = False
                    self.beep_deactivate.play(times=2, interval=0.2)

                    if self.on_exit_callback:
                        self.on_exit_callback()

                    break

                self.conversation_history.append(text)

                if self.on_speech_callback:
                    self.on_speech_callback(text)
            
            except KeyboardInterrupt:
                print("\n キーボード割り込みで終了します...")
                self.stop()
                break
            except Exception as e:
                print(f"エラー: {e}")
                self.is_active = False
                self.beep_deactivate.play(times=2, interval=0.2)
                break
        
    def set_callbacks(self, on_wakeup=None, on_exit=None, on_speech=None):
        """コールバック関数の設定"""
        self.on_wakeup_callback = on_wakeup
        self.on_exit_callback = on_exit
        self.on_speech_callback = on_speech

    def start(self):
        """システムを起動"""
        self.is_running = True
        print("\n ウェイクアップASRシステムを起動します")
        print("マイクをセットアップ中")

        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"マイク閾値を {self.recognizer.energy_threshold} に設定しました")
            except Exception as e:
                print(f"マイクのセットアップに失敗しました: {e}")
        
        print("システム準備完了")
        self.beep_sound.play(times=1)

        try:
            self.run_idle_mode()
        except KeyboardInterrupt:
            print("\n キーボード割り込みで終了します...")
            self.stop()
    
    def stop(self):
        """システムを停止"""
        self.is_running = False
        self.is_active = False
        self.cancel_listening.set()
        print("ウェイクアップASRシステムを停止します")
        self.beep_sound.play(times=3, interval=0.1)

#==============================================
# TTS (Text-to-Speech) モジュール
#==============================================

def split_text_custom(text, max_length=100):
    """テキストを文末や絵文字に基づいてセグメントに分割"""
    pattern = r"(?<=[。！？\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U00002728])"
    sentences = re.split(pattern, text)
    segments = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_length:
            for i in range(0, len(sentence), max_length):
                segments.append(sentence[i:i+max_length])
        else:
            segments.append(sentence)
    return segments

def generate_tts_audio(text, tts_api_url=VOICEVOX_API_URL, speaker_id=VOICEVOX_SPEAKER_ID):
    """VOICEVOX APIを呼び出してテキストから音声を生成する"""
    segments = split_text_custom(text)
    combined_audio = None

    for chunk in segments:
        if len(chunk.strip()) <= 1:
            continue

        try:
            # 1. 音声合成用のクエリを作成 (audio_query)
            query_params = {"text": chunk, "speaker": speaker_id}
            query_response = requests.post(f"{tts_api_url}/audio_query", params=query_params)
            
            if query_response.status_code != 200:
                print(f"VOICEVOX クエリ作成エラー: HTTP {query_response.status_code}")
                continue
            
            query_data = query_response.json()

            # 2. クエリをもとに音声を合成 (synthesis)
            synth_params = {"speaker": speaker_id}
            synth_response = requests.post(
                f"{tts_api_url}/synthesis", 
                params=synth_params, 
                json=query_data
            )
            
            if synth_response.status_code == 200:
                # 取得したWAVデータをAudioSegmentに変換して結合
                audio_segment = AudioSegment.from_file(io.BytesIO(synth_response.content), format="wav")
                if combined_audio is None:
                    combined_audio = audio_segment
                else:
                    combined_audio += audio_segment
            else:
                print(f"VOICEVOX 音声合成エラー: HTTP {synth_response.status_code}")
                
        except Exception as e:
            print(f"TTS生成エラー: {e}")

    # 分割して生成した音声を一つのWAVデータにまとめて返す
    if combined_audio:
        out_buffer = io.BytesIO()
        combined_audio.export(out_buffer, format="wav")
        return out_buffer.getvalue()
    return None

def play_audio(audio_data, output_file=OUTPUT_FILE, autoplay=True, delete_after=True):
    """音声データをファイルに保存し，必要に応じて自動再生"""
    if not audio_data:
        print("再生するデータがありません")
        return False
    
    #ファイルに保存
    try:
        with open(output_file, "wb") as f:
            f.write(audio_data)
    except Exception as e:
        print(f"ファイル保存エラー: {e}")
        return False
    
    #自動再生が有効な場合
    if autoplay:
        try:
            # simpleaudioで再生
            try:
                wave_obj = sa.WaveObject.from_wave_file(output_file)
                play_obj = wave_obj.play()
                play_obj.wait_done()

                if delete_after:
                    try:
                        os.remove(output_file)
                    except Exception as e:
                        print(f"ファイル削除エラー: {e}")

                return True
            except Exception as e:
                print(f"simpleaudioで再生エラー: {e}")
                print("代替方法で再生を試みます...")
            
            # OS別の再生方法
            system = platform.system()
            if system == "Windows":
                subprocess.call(["start", os.path.abspath(output_file)], shell=True)
                time.sleep(5)
            elif system == "Darwin":  # macOS
                subprocess.call(["afplay", output_file])
            elif system == "Linux":
                subprocess.call(["aplay", output_file])

            if delete_after:
                try:
                    os.remove(output_file)
                except Exception as e:
                    print(f"ファイル削除エラー: {e}")
            
            return True
        except Exception as e:
            print(f"自動再生中にエラーが発生しました: {e}")
            return False
    return True

def search_internet(query):
    """SerpAPIを利用してインターネット検索を行う"""
    if not SERP_API_KEY:
        return "検索APIキーが設定されていません"
    
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "engine": "google",
        "num": 3
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("organic_results", [])
            if not results:
                return "検索結果は見つかりませんでした．"
            
            result_texts = []
            for res in results:
                title = res.get("title", "No Title")
                snippet = res.get("snippet", "")
                result_texts.append(f" 【{title}】 : {snippet}")
            
            full_result = "\n".join(result_texts)
            return summarize_text(full_result, "以下の検索結果の内容を，事実に基づいて正確に要約してください．",
                                  prefix=" 【検索結果】 :\n", suffix="\n 【要約】 :")
        else:
            return f"検索に失敗しました．HTTPステータス: {response.status_code}"
    except Exception as e:
        return f"検索中にエラーが発生しました: {e}"

#==============================================
# 会話管理機能
#==============================================

def summarize_text(text, instruction, prefix="", suffix="", model=LLM_MODEL_NAME, max_tokens=1000):
    """テキストを要約する汎用関数"""
    prompt = f"{instruction}\n{prefix}{text}{suffix}"
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは情報を簡潔に要約するアシスタントです．"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.2,
            top_p=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"要約中にエラーが発生しました: {e}"
    
def summarize_conversation(history):
    """会話履歴を要約する"""
    conversation_text = ""
    for msg in history:
        if msg["role"] in ["user", "assistant"]:
            conversation_text += f"{msg['role']}:{msg['content']}\n"

    return summarize_text(
        text=conversation_text,
        instruction="以下の会話内容を，ユーザーへのサポートとして必要な情報を残しつつ，簡潔に要約してください",
        prefix=" 【会話内容】 :\n",
        suffix="\n 【要約】 :",
        max_tokens=200
    )

def save_conversation_log(conversation_history, filename=CONVERSATION_LOG_FILE):
    """会話履歴をファイルに保存する"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(conversation_history, f, ensure_ascii=False, indent=2)
        print(f"対話履歴を {filename} に保存しました．")
    except Exception as e:
        print("対話履歴の保存に失敗しました:", e)

def load_conversation_log(filename=CONVERSATION_LOG_FILE):
    """会話履歴をファイルから読み込む"""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                history = json.load(f)
            print(f"{filename} から対話履歴を読み込みました。")
            return history
        except Exception as e:
            print("対話履歴の読み込みに失敗しました:", e)
    return []

def generate_response(user_input, conversation_history, system_prompt):
    """ユーザー入力に対する応答を生成する"""
    # 「続けて」リクエストの処理
    if user_input.strip() == "続けて":
        for msg in reversed(conversation_history):
            if msg["role"] == "assistant":
                context_snippet = msg["content"][-120:]
                continuation_prompt = f"以下の文章の続きを生成して下さい：\n\n{context_snippet}\n\n続きをお願いします．"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": continuation_prompt}
                ]
                break
            else:
                messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
            
    elif user_input.starstwith("検索:") or "を検索して" in user_input:
        if user_input.startswith("検索:"):
            query = user_input.replace("検索:", "", 1).strip()
        else:
            match = re.search(r"(.*)を検索して", user_input)
            query = match.group(1).strip() if match else user_input
        
        search_result = search_internet(query)
        messages = conversation_history.copy() if conversation_history else [{"role": "system", "content": system_prompt}]
        messages.append({"role": "assistant", "content": f"【検索結果】\n{search_result}"})
        return search_result, messages
    
    else:
        messages = conversation_history.copy() if conversation_history else [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_input})
    
    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=messages,
            max_tokens=200,
            temperature=0.9,
            top_p=0.9,
            stop=["\nユーザー:"]
        )
        assistant_response = response.choices[0].message.content.strip()
    except Exception as e:
        assistant_response = f"エラーが発生しました: {e}"
    
    # 最後のメッセージが"user"の場合，応答を追加
    if not messages or messages[-1]["role"] == "user":
        messages.append({"role": "assistant", "content": assistant_response})
    # 最後がすでに"assistant"の場合（検索結果など）は追加しない

    return assistant_response, messages

#==============================================
# メイン処理
#==============================================

def main():
    """メイン処理"""
    print("="*50)
    print("=== 音声認識・合成付きチャットボット ===")
    print("【使い方】")
    print("※ 'exit' と入力すると終了します")
    print("※ 'voice' と入力すると単発の音声入力モードになります．")
    print("※ 'listen' と入力するとウェイクアップ待機モードになります．")
    print("\n【音声コマンド】")
    print("※ ウェイクアップフレーズ例: 「ねえ」「こんにちは」")
    print("※ 終了フレーズ例: 「さようなら」「じゃあ また今度」")
    print("="*50)

    # 設定情報の表示
    print(f"\n 【現在の設定】")
    print(f"* LLMモデル: {LLM_MODEL_NAME}")
    print(f"* TTSモデル: {TTS_MODEL_NAME}")
    print(f"* LLM API: {OPENAI_API_URL}")
    print(f"* TTS API: {TTS_API_URL}")
    print(f"* 音声認識言語: {ASR_LANGUAGE}")
    print("="*50)

    custom_system_prompt = input("システムプロンプトを入力してください（変更しない場合はEnter）： ").strip()
    system_prompt = custom_system_prompt if custom_system_prompt else DEFAULT_SYSTEM_PROMPT

    # 会話履歴の読み込み
    conversation_history = load_conversation_log()
    if not conversation_history or conversation_history[0]["role"] != "system":
        conversation_history.insert(0, {"role": "system", "content": system_prompt})
    
    episode_count = sum(1 for msg in conversation_history if msg["role"] in ["user", "assistant"]) // 2

    # 音声入力の処理関数
    def process_speech(text):
        nonlocal conversation_history, episode_count, system_prompt

        if not text:
            return
        
        print(f"ユーザー: {text}")
        response, conversation_history = generate_response(text, conversation_history, system_prompt)
        print(f"ChatGPT: {response}")
        episode_count += 1

        # TTS処理と再生
        audio_data = generate_tts_audio(response)
        play_audio(audio_data, OUTPUT_FILE, autoplay=True)

        # 定期的な保存と要約
        if episode_count % SAVE_INTERVAL_EPISODES == 0:
            save_conversation_log(conversation_history)
        
        if episode_count >= SUMMARY_INTERVAL:
            print("\n 【会話の内容を生成中】")
            summary = summarize_conversation(conversation_history)
            print("【要約】:", summary, "\n")

            # 要約を組み込んだ新しいシステムプロンプト
            system_prompt = (
                "あなたは明るく元気なAIアシスタントです！"
                "感情豊かで親しみやすい口調でユーザーをサポートします．"
                f"以下はこれまでの会話の要約です．\n"
                f"【会話要約】: {summary}\n"
                f"【フィードバック】: {DEFAULT_FEEDBACK}"
            )
            conversation_history = [{"role": "system", "content": system_prompt}]
            episode_count = 0
    
    asr = ASRModule(
        language=ASR_LANGUAGE,
        wakeup_phrases=WAKEUP_PHRASES,
        exit_phrases=EXIT_PHRASES,
        idle_timeout=None,
        listening_timeout=LISTENING_TIMEOUT,
        energy_threshold=ASR_ENERGY_THRESHOLD,
        tts_func=generate_tts_audio,
        play_audio_func=lambda audio: play_audio(audio, OUTPUT_FILE, autoplay=True)
    )

    # ASRコールバック関数の設定
    asr.set_callbacks(
        on_wakeup=lambda: print("\n 音声認識が起動しました！何かお話しください"),
        on_exit=lambda: print("\n 音声認識は待機モードに戻りました"),
        on_speech=process_speech
    )

    asr_thread = None

    # ASRを別スレッドで起動する関数
    def start_asr_in_thread():
        nonlocal asr_thread
        if asr_thread and asr_thread.is_alive():
            print("すでに音声認識が実行中です")
            return
        
        asr_thread = threading.Thread(target=asr.start)
        asr_thread.daemon = True
        asr_thread.start()
    
    # メインループ
    while True:
        user_input = input("\nユーザー: ").strip()

        if user_input.lower() == "exit":
            print("チャットを終了します．")
            if asr.is_running:
                asr.stop()
                time.sleep(0.5)
            break

        # 単発の音声入力モード
        elif user_input.lower() == "voice":
            print("単発の音声入力モードを開始します...")
            voice_text = asr.listen_once(timeout=10)
            if voice_text:
                process_speech(voice_text)
        
        # ウェイクアップ待機モード開始
        elif user_input.lower() == "listen":
            print("ウェイクアップ待機モードを開始します...")
            print("（終了するには，コンソールに戻って 'exit' と入力してください）")
            start_asr_in_thread()
        
        else:
            response, conversation_history = generate_response(user_input, conversation_history, system_prompt)
            print("ChatGPT:", response)
            episode_count += 1

            # TTS処理と再生
            audio_data = generate_tts_audio(response)
            play_audio(audio_data, OUTPUT_FILE, autoplay=True)

            # 定期的な保存と要約
            if episode_count % SAVE_INTERVAL_EPISODES == 0:
                save_conversation_log(conversation_history)
            
            if episode_count >= SUMMARY_INTERVAL:
                print("\n【会話の要約を生成中…】")
                summary = summarize_conversation(conversation_history)
                print("【要約】:", summary, "\n")
                
                # 要約を組み込んだ新しいシステムプロンプト
                system_prompt = (
                    "あなたは明るく元気なAIアシスタントです！"
                    "感情豊かで親しみやすい口調で、ユーザーをサポートします。"
                    f"以下は、これまでの会話の要約です。\n"
                    f"【会話要約】: {summary}\n"
                    f"【フィードバック】: {DEFAULT_FEEDBACK}"
                )
                conversation_history = [{"role": "system", "content": system_prompt}]
                episode_count = 0

    # 会話履歴を保存して終了
    save_conversation_log(conversation_history)


if __name__ == "__main__":
    main()