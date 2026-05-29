from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationStyle:
    name: str
    instruction: str
    preface: str | None = None


def detect_style(user_input: str) -> ConversationStyle:
    text = user_input.lower()

    if user_input.startswith("検索:") or "を検索して" in user_input or "調べて" in user_input:
        return ConversationStyle(
            name="search",
            preface="うん、調べてみるね。",
            instruction=(
                "調べものへの返答です。最初に結論を短く言い、そのあと家庭で役立つ具体的な判断材料を1〜2文で加えてください。"
                "日時、場所、料金、持ち物、注意点などが検索結果にあれば優先して伝えてください。検索結果にないことは断言しないでください。"
            ),
        )

    if any(word in text for word in ["つらい", "疲れ", "不安", "悲しい", "しんどい", "悩", "困った"]):
        return ConversationStyle(
            name="support",
            instruction=(
                "相談や弱音への返答です。まず一言だけ受け止めてから、今すぐできる具体的な行動を1つ提案してください。"
                "例として、水を飲む、5分休む、予定を1つ減らす、持ち物を確認する、など小さな行動にしてください。"
            ),
        )

    if any(word in text for word in ["予定", "リマインド", "買い物", "片付け", "掃除", "洗濯", "料理"]):
        return ConversationStyle(
            name="task",
            instruction=(
                "予定や家事への返答です。親しみは保ちつつ、次にやる行動を具体的に答えてください。"
                "時間、順番、持ち物、買う量、片付ける場所など、生活でそのまま使える情報を入れてください。"
            ),
        )

    if len(user_input) > 45 or any(word in text for word in ["教えて", "説明", "どうすれば", "なぜ", "なんで"]):
        return ConversationStyle(
            name="thinking",
            preface="うん、少し考えるね。",
            instruction=(
                "説明が必要な返答です。声で聞いてわかりやすいよう、結論、理由、次の行動の順で2〜4文にしてください。"
                "抽象論だけで終わらず、ユーザーが今すぐ試せる具体例を1つ入れてください。箇条書きは使わないでください。"
            ),
        )

    return ConversationStyle(
        name="chat",
        instruction=(
            "雑談への返答です。自然に相づちしつつ、必要なら生活に役立つ具体的な提案を1つだけ添えてください。"
            "質問で返す場合は1つだけにしてください。抽象的な感想だけで終わらないでください。"
        ),
    )
