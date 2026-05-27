import re

from openai import OpenAI

from .config import AppConfig
from .memory import ConversationMemory, summarize_conversation
from .search import WebSearch


class ChatBrain:
    def __init__(self, config: AppConfig, memory: ConversationMemory, search: WebSearch):
        self.config = config
        self.memory = memory
        self.search = search
        self.client = OpenAI(api_key=config.openai_api_key)

    def respond(self, user_input: str) -> str:
        search_result = self._maybe_search(user_input)
        if search_result:
            self.memory.add_user(user_input)
            response = self._complete(
                extra_instruction=(
                    "次の検索結果を踏まえて、家庭で聞きやすい短さで答えてください。"
                    "検索結果にないことは断言しないでください。\n\n"
                    f"{search_result}"
                )
            )
        elif user_input.strip() == "続けて":
            response = self._continue_last_response()
        else:
            self.memory.add_user(user_input)
            response = self._complete()

        self.memory.add_assistant(response)
        self._save_and_summarize_if_needed()
        return response

    def _complete(self, extra_instruction: str | None = None) -> str:
        messages = list(self.memory.messages)
        if extra_instruction:
            messages.append({"role": "system", "content": extra_instruction})

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                max_tokens=self.config.max_response_tokens,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as error:
            return f"返答の生成中にエラーが発生しました: {error}"

    def _continue_last_response(self) -> str:
        for message in reversed(self.memory.messages):
            if message.get("role") == "assistant":
                self.memory.add_user(f"次の文章の続きを自然に話してください:\n{message['content'][-160:]}")
                return self._complete()
        self.memory.add_user("続けて")
        return self._complete()

    def _maybe_search(self, user_input: str) -> str | None:
        if user_input.startswith("検索:"):
            query = user_input.replace("検索:", "", 1).strip()
            return self.search.search(query)

        match = re.search(r"(.+?)を検索して", user_input)
        if match:
            return self.search.search(match.group(1).strip())

        return None

    def _save_and_summarize_if_needed(self) -> None:
        turn_count = self.memory.turn_count()
        if turn_count % self.config.save_interval_turns == 0:
            self.memory.save()

        if turn_count >= self.config.summary_interval_turns:
            try:
                summary = summarize_conversation(self.client, self.config, self.memory.messages)
                self.memory.replace_with_summary(summary)
            except Exception as error:
                print(f"会話の要約に失敗しました: {error}")
            self.memory.save()
