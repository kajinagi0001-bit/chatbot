# Family Chatbot

家庭で「新しい家族」のように使うことを目指した、日本語音声チャットボットです。
テキスト入力、単発の音声入力、呼びかけ待機の3つの使い方に対応しています。

## できること

- 家族との雑談のような短く自然な返答
- 音声認識による会話
- VOICEVOX系の音声合成APIによる返答読み上げ
- 会話履歴の保存と、長くなった会話の要約
- `検索: 今日の天気` または `今日の天気を検索して` のような検索

## セットアップ

```powershell
pip install -r requirements.txt
```

APIキーは、プロジェクト直下の `.env` に保存できます。
まず `.env.example` をコピーして `.env` を作り、値を書き換えてください。

```powershell
Copy-Item .env.example .env
```

`.env` の例:

```env
OPENAI_API_KEY=your-openai-api-key
TTS_QUEST_API_KEY=your-tts-quest-api-key
SERP_API_KEY=your-serp-api-key
```

`SERP_API_KEY` は検索機能を使う場合のみ必要です。
`.env` はGit管理から除外しているため、APIキーを毎回入力する必要はありません。

Raspberry Pi で音声を使う場合は、Pythonパッケージに加えてマイク、スピーカー、PortAudio、ffmpeg などのOS側セットアップが必要になることがあります。

## 起動

```powershell
python chatbot.py
```

起動後の入力:

- 普通の文章: テキストで会話
- `voice`: 一度だけ音声入力
- `listen`: 呼びかけ待機を開始
- `exit`: 終了

呼びかけ例:

- ねえ
- おはよう
- こんにちは
- こんばんは
- チャットさん

## 主なファイル

- `chatbot.py`: 起動用の入口
- `family_chatbot/app.py`: アプリ全体の流れ
- `family_chatbot/config.py`: 設定と家庭向けプロンプト
- `family_chatbot/llm.py`: OpenAI APIによる返答生成
- `family_chatbot/memory.py`: 会話履歴の保存と要約
- `family_chatbot/speech.py`: 音声認識と呼びかけ待機
- `family_chatbot/tts.py`: VOICEVOX系TTS API連携
- `family_chatbot/audio.py`: ビープ音と音声再生
- `family_chatbot/search.py`: Web検索

## 注意

会話履歴は `conversation_log.json` に保存されます。個人的な内容が含まれる可能性があるため、Git管理からは除外しています。
