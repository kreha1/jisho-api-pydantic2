from __future__ import annotations

import json
from typing import Any, Iterator
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from rich.markdown import Markdown

from jisho_api.cli import console
from jisho_api.sentence.cfg import SentenceConfig
from jisho_api.util import CLITagger


class RequestMeta(BaseModel):
    status: int


class SentenceRequest(BaseModel):
    meta: RequestMeta
    data: list[SentenceConfig]

    def __len__(self):
        return len(self.data)

    def __iter__(self) -> Iterator[SentenceConfig]:
        yield from reversed(self.data)

    def rich_print(self):
        for d in self:
            console.print("[white][[red]jp[white]]")
            console.print(CLITagger.bullet(d.japanese))
            console.print("[white][[blue]en[white]]")
            console.print(CLITagger.bullet(d.en_translation))
            console.print(Markdown("---"))


class Sentence:
    URL = "https://jisho.org/search/"
    ROOT = Path.home() / ".jisho/data/sentence/"

    @staticmethod
    def sentences(soup: BeautifulSoup) -> list[SentenceConfig]:
        res = soup.find_all("div", {"class": "sentence_content"})

        sts = []
        for r in res:
            s1_jp = r.find("ul", {"class": "japanese_sentence"})
            s1_en = r.find_all("span", {"class": "english"})[0].text

            b = ""
            for s in s1_jp.contents:
                if s.find("span") != -1:
                    u = s.find("span", {"class": "unlinked"}).text
                    try:
                        f = s.find("span", {"class": "furigana"}).text
                        b += f"{u}({f})"
                    except:
                        b += f"{u}"
                        pass
                else:
                    u = s.text
                    b += u
            b = b.strip()
            sts.append({"japanese": b, "en_translation": s1_en})

        return sts

    @staticmethod
    def request(
        word: str,
        cache: bool = False,
        headers: dict[str, str] | None = None,
    ) -> SentenceRequest | None:
        url = Sentence.URL + urllib.parse.quote(word + " #sentences")
        toggle = False

        if cache and (Sentence.ROOT / (word + ".json")).exists():
            toggle = True
            with open(Sentence.ROOT / (word + ".json"), "r", encoding="utf-8") as fp:
                r = json.load(fp)
            r = SentenceRequest(**r)
        else:
            r = requests.get(url, headers=headers).content
            soup = BeautifulSoup(r, "html.parser")

            r = SentenceRequest(
                meta=RequestMeta(status=200),
                data=Sentence.sentences(soup),
            )
            if not len(r):
                console.print(f"[red bold][Error] [white] No matches found for {word}.")
                return None
        if cache and not toggle:
            Sentence.save(word, r)
        return r

    @staticmethod
    def save(word: str, r: SentenceRequest | dict[str, Any]) -> None:
        Sentence.ROOT.mkdir(exist_ok=True)
        try:
            payload = r if isinstance(r, dict) else r.model_dump(exclude_unset=True, by_alias=True)
            with open(Sentence.ROOT / f"{word}.json", "w", encoding="utf-8") as fp:
                json.dump(payload, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red bold][Error] [white] Failed to save {word}: {str(e)}")

