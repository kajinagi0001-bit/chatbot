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
                "調べものへの返答です。最初に結論を短く言い、必要なら補足を1文だけ加えてください。"
                "検索結果にないことは断言しないでください。"
            ),
        )

    if any(word in text for word in ["つらい", "疲れ", "不安", "悲しい", "しんどい", "悩", "困った"]):
        return ConversationStyle(
            name="support",
            instruction=(
                "相談や弱音への返答です。まず一言受け止めてから、押しつけない提案を1つだけしてください。"
                "明るすぎる励ましや長い説明は避けてください。"
            ),
        )

    if any(word in text for word in ["予定", "リマインド", "買い物", "片付け", "掃除", "洗濯", "料理"]):
        return ConversationStyle(
            name="task",
            instruction=(
                "予定や家事への返答です。親しみは保ちつつ、具体的で短く答えてください。"
                "必要なら次の一手を1つだけ提案してください。"
            ),
        )

    if len(user_input) > 45 or any(word in text for word in ["教えて", "説明", "どうすれば", "なぜ", "なんで"]):
        return ConversationStyle(
            name="thinking",
            preface="うん、少し考えるね。",
            instruction=(
                "説明が必要な返答です。声で聞いてわかりやすいよう、短い文を2〜3文までにしてください。"
                "箇条書きは使わないでください。"
            ),
        )

    return ConversationStyle(
        name="chat",
        instruction=(
            "雑談への返答です。家で隣にいる人のように、短い相づちを含めて自然に返してください。"
            "質問で返す場合は1つだけにしてください。"
        ),
    )
