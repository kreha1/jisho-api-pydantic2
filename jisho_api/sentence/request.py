import json
import urllib
from pathlib import Path
from typing import List

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
    data: List[SentenceConfig]

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        yield from reversed(self.data)

    def rich_print(self):
        for d in self:
            console.print(f"[white][[red]jp[white]]")
            console.print(CLITagger.bullet(d.japanese))
            console.print(f"[white][[blue]en[white]]")
            console.print(CLITagger.bullet(d.en_translation))
            console.print(Markdown("---"))


class Sentence:
    URL = "https://jisho.org/search/"
    ROOT = Path.home() / ".jisho/data/sentence/"

    @staticmethod
    def sentences(soup):
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
    def request(word, cache=False, headers=None):
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
                **{
                    "meta": {
                        "status": 200,
                    },
                    "data": Sentence.sentences(soup),
                }
            )
            if not len(r):
                console.print(f"[red bold][Error] [white] No matches found for {word}.")
                return None
        if cache and not toggle:
            Sentence.save(word, r)
        return r

    @staticmethod
    def save(word, r):
        Sentence.ROOT.mkdir(exist_ok=True)
        with open(Sentence.ROOT / f"{word}.json", "w", encoding="utf-8") as fp:
            json.dump(r.dict(), fp, indent=4, ensure_ascii=False)
