from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

import requests
from pydantic import BaseModel
from bs4 import BeautifulSoup

from jisho_api.cli import console
from jisho_api.tokenize.cfg import TokenConfig
from jisho_api.util import CLITagger


class RequestMeta(BaseModel):
    status: int


class TokenRequest(BaseModel):
    meta: RequestMeta
    data: list[TokenConfig]

    def __len__(self):
        return len(self.data)

    def __iter__(self) -> Iterator[TokenConfig]:
        yield from self.data

    def rich_print(self):
        base = ""
        toks = ""
        for i, d in enumerate(self):
            base += CLITagger.underline(d.token) + " "
            toks += f"{i}. {d.token} [violet][{str(d.pos_tag.value)}][/violet]\n"
        console.print(base)
        console.print(toks)


class Tokens:
    URL = "https://jisho.org/search/"
    ROOT = Path.home() / ".jisho/data/tokens/"

    @staticmethod
    def tokens(soup: BeautifulSoup) -> list[TokenConfig]:
        res = soup.find_all("section", {"id": "zen_bar"})

        tks = []
        for r in res:
            toks = r.find_all("li")
            for t in toks:
                try:
                    pos_tag = t["data-pos"]
                except KeyError:
                    pos_tag = "Unknown"
                jp = t.find_all("span", {"class": "japanese_word__text_wrapper"})
                try:
                    jp = jp[0].find_all("a")[0]["data-word"]
                except (KeyError, IndexError):
                    jp = jp[0].text.strip()
                tks.append(TokenConfig(token=jp, pos_tag=pos_tag))

        return tks

    @staticmethod
    def request(word, cache=False, headers=None):
        url = Tokens.URL + urllib.parse.quote(word)
        toggle = False

        if cache and (Tokens.ROOT / (word + ".json")).exists():
            toggle = True
            with open(Tokens.ROOT / (word + ".json"), "r", encoding="utf-8") as fp:
                r = json.load(fp)
            r = TokenRequest(**r)
        else:
            r = requests.get(url, headers=headers).content
            soup = BeautifulSoup(r, "html.parser")

            r = TokenRequest(
                meta=RequestMeta(status=200),
                data=Tokens.tokens(soup),
            )
            if not len(r):
                console.print(f"[red bold][Error] [white] No matches found for {word}.")
                return None
        if cache and not toggle:
            Tokens.save(word, r)
        return r

    @staticmethod
    def save(word: str, r: TokenRequest | dict[str, Any]) -> None:
        Tokens.ROOT.mkdir(exist_ok=True)
        try:
            payload = r if isinstance(r, dict) else r.model_dump(exclude_unset=True, by_alias=True)
            with open(Tokens.ROOT / f"{word}.json", "w", encoding="utf-8") as fp:
                json.dump(payload, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red bold][Error] [white] Failed to save {word}: {str(e)}")
