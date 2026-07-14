import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from .config import AppConfig


class _ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if len(text) >= 24:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


class WebSearch:
    def __init__(self, config: AppConfig):
        self.config = config

    def search(self, query: str) -> str:
        if not self.config.serp_api_key:
            return "検索APIキーが設定されていないため、今は検索できません。"

        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.config.serp_api_key,
                    "engine": "google",
                    "num": self.config.search_result_count,
                    "hl": "ja",
                    "gl": "jp",
                },
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            return f"検索中にエラーが発生しました: {error}"

        data = response.json()
        results = data.get("organic_results", [])
        if not results:
            return "検索結果は見つかりませんでした。"

        sections = [f"検索クエリ: {query}"]
        direct_answers = self._direct_answers(data)
        if direct_answers:
            sections.append("検索エンジンの直接情報:\n" + "\n".join(direct_answers))

        lines = []
        for index, result in enumerate(results[: self.config.search_result_count], start=1):
            title = result.get("title", "No Title")
            source = result.get("source") or self._domain(result.get("link", ""))
            date = result.get("date", "")
            snippet = result.get("snippet") or result.get("snippet_highlighted_words", "")
            link = result.get("link", "")
            rich = self._flatten(result.get("rich_snippet") or result.get("about_this_result"))
            page_text = self._fetch_page_text(link) if self.config.search_fetch_pages else ""

            line_parts = [
                f"[{index}] {title}",
                f"出典: {source}" if source else "",
                f"日付: {date}" if date else "",
                f"要約: {snippet}" if snippet else "",
                f"補足: {rich}" if rich else "",
                f"本文抜粋: {page_text}" if page_text else "",
                f"URL: {link}" if link else "",
            ]
            lines.append("\n".join(part for part in line_parts if part))

        sections.append("検索結果:\n" + "\n\n".join(lines))
        sections.append(
            "回答ルール: 上の情報だけを根拠に答える。出典名や日付がある場合は自然に触れる。"
            "情報が足りなければ、不明点を1つだけ確認する。"
        )
        return "\n\n".join(sections)

    def _direct_answers(self, data: dict) -> list[str]:
        answers = []
        answer_box = data.get("answer_box") or {}
        knowledge_graph = data.get("knowledge_graph") or {}

        for key in ["answer", "snippet", "snippet_highlighted_words", "title", "date"]:
            value = answer_box.get(key)
            if value:
                answers.append(f"AnswerBox {key}: {self._flatten(value)}")

        for key in ["title", "type", "description"]:
            value = knowledge_graph.get(key)
            if value:
                answers.append(f"KnowledgeGraph {key}: {self._flatten(value)}")

        return answers

    def _fetch_page_text(self, url: str) -> str:
        if not url or not url.startswith(("http://", "https://")):
            return ""

        try:
            response = requests.get(
                url,
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FamilyChatbot/1.0)"},
            )
            response.raise_for_status()
        except requests.RequestException:
            return ""

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return ""

        parser = _ReadableHTMLParser()
        try:
            parser.feed(response.text[:350_000])
        except Exception:
            return ""

        text = re.sub(r"\s+", " ", parser.text()).strip()
        return text[: self.config.search_page_char_limit]

    def _flatten(self, value) -> str:
        if isinstance(value, list):
            return "、".join(self._flatten(item) for item in value if item)
        if isinstance(value, dict):
            return "、".join(f"{key}: {self._flatten(item)}" for key, item in value.items() if item)
        return str(value)

    def _domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc
        except Exception:
            return ""
