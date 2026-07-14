# Family Chatbot

家庭で「新しい家族」のように使うことを目指した、日本語音声チャットボットです。
テキスト入力、単発の音声入力、呼びかけ待機の3つの使い方に対応しています。

## できること

- 家族との雑談のような短く自然な返答
- 音声認識による会話
- VOICEVOX系の音声合成APIによる返答読み上げ
- 会話履歴の保存と、長くなった会話の要約
- `検索: 今日の天気` または `今日の天気を検索して` のような検索
- 雑談、相談、家事、調べものに合わせた自然な話し分け
- 長めの処理前に「うん、調べてみるね」のような短い相づち
- 音声再生中に次の文を先読み合成して、発声間の待ち時間を短縮
- 家族メンバーごとの記憶、予定、買い物メモ、伝言
- 抽象的な雑談だけでなく、次の行動、時刻、持ち物、手順を含む生活支援

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

検索結果を詳しくしたい場合は、`.env` で調整できます。

```env
CHATBOT_SEARCH_RESULT_COUNT=5
CHATBOT_SEARCH_FETCH_PAGES=true
CHATBOT_SEARCH_PAGE_CHAR_LIMIT=900
```

`CHATBOT_SEARCH_FETCH_PAGES=true` にすると、検索結果の上位ページを短く読み取り、スニペットだけでなく本文抜粋も会話に使います。少し遅くなる場合は `false` にしてください。

Raspberry Pi で音声を使う場合は、Pythonパッケージに加えてマイク、スピーカー、PortAudio、ffmpeg、flac などのOS側セットアップが必要になることがあります。

```bash
sudo apt update
sudo apt install -y portaudio19-dev ffmpeg flac
```

## 起動

```powershell
python chatbot.py
```

起動後の入力:

- 普通の文章: テキストで会話
- `voice`: 一度だけ音声入力
- `listen`: 呼びかけ待機を開始
- `exit`: 終了

音声待機の調整は `.env` で変更できます。

```env
CHATBOT_LISTENING_TIMEOUT=15
CHATBOT_ACTIVE_SILENCE_RETRIES=2
CHATBOT_SPEECH_PAUSE_THRESHOLD=2.2
CHATBOT_SPEECH_PHRASE_LIMIT=45
CHATBOT_ENERGY_THRESHOLD=400
CHATBOT_TTS_SPEED=1.1
```

`CHATBOT_LISTENING_TIMEOUT` は呼びかけ後に話し始めるまで待つ秒数、`CHATBOT_ACTIVE_SILENCE_RETRIES` は無音でも待機へ戻らず追加で待つ回数です。
話の途中で少し考えただけで返答が始まる場合は、`CHATBOT_SPEECH_PAUSE_THRESHOLD` を大きくしてください。長く話したい場合は `CHATBOT_SPEECH_PHRASE_LIMIT` を大きくします。
読み上げを速くしたい場合は `CHATBOT_TTS_SPEED` を上げます。`1.0` が通常、`1.1` が少し速め、`1.2` がかなり速めです。

呼びかけ例:

- ねえ
- おはよう
- こんにちは
- こんばんは
- チャットさん

## 家族機能

家族データは `data/family.db` に保存されます。
旧バージョンの `data/family_state.json` が存在する場合は、
初回起動時にSQLiteへ自動移行されます。
移行前のJSONは
`data/family_state.pre-sqlite.json`
としてバックアップされます。

使える言い方の例:

- `私はAです`
- `お母さんに切り替えて`
- `朝は短く話してほしいって覚えておいて`
- `家族のこととしてゴミ出しは火曜と金曜って覚えておいて`
- `明日16時に歯医者の予定を入れて`
- `お母さんの予定を教えて`
- `買い物リストに牛乳を入れて`
- `買い物リスト見せて`
- `お母さんに、帰りに牛乳お願いって伝えて`
- `伝言ある？`
- `私の記憶を見せて`

## 主なファイル

- `chatbot.py`: 起動用の入口
- `family_chatbot/app.py`: アプリ全体の流れ
- `family_chatbot/config.py`: 設定と家庭向けプロンプト
- `family_chatbot/conversation.py`: 会話タイプ判定と話し方の調整
- `family_chatbot/family.py`: 家族ごとの記憶、予定、買い物、伝言の保存
- `family_chatbot/llm.py`: OpenAI APIによる返答生成
- `family_chatbot/memory.py`: 会話履歴の保存と要約
- `family_chatbot/speech_text.py`: 読み上げ前のテキスト整形
- `family_chatbot/speech.py`: 音声認識と呼びかけ待機
- `family_chatbot/tts.py`: VOICEVOX系TTS API連携
- `family_chatbot/audio.py`: ビープ音と音声再生
- `family_chatbot/search.py`: Web検索

## 注意

会話履歴は `conversation_log.json`、家族データは `data/family_state.json` に保存されます。個人的な内容が含まれる可能性があるため、Git管理からは除外しています。
