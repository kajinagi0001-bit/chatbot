import requests

from .config import AppConfig


class WebSearch:
    def __init__(self, config: AppConfig):
        self.config = config

    def search(self, query: str) -> str:
        if not self.config.serp_api_key:
            return "検索APIキーが設定されていないため、今は検索できません。"

        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.config.serp_api_key, "engine": "google", "num": 3},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            return f"検索中にエラーが発生しました: {error}"

        results = response.json().get("organic_results", [])
        if not results:
            return "検索結果は見つかりませんでした。"

        lines = []
        for result in results:
            title = result.get("title", "No Title")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            lines.append(f"【{title}】{snippet} {link}".strip())
        return "\n".join(lines)
