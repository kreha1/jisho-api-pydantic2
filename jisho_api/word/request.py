from __future__ import annotations
import json
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

import requests
from pydantic import BaseModel
from rich.markdown import Markdown

from jisho_api.cli import console
from jisho_api.word.cfg import WordConfig


class RequestMeta(BaseModel):
    status: int


class WordRequest(BaseModel):
    meta: RequestMeta
    data: list[WordConfig]

    def __iter__(self) -> Iterator[WordConfig]:
        yield from reversed(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def rich_print(self) -> None:
        for wdef in self:
            j = wdef.japanese[0]
            if j.word:
                base = f"[green]{j.word}"
                if j.reading is not None:
                    base += f" [red]([white]{j.reading}[red])"
            else:
                base = f"[green]{j.reading}"

            # TODO - really funky here
            if len(wdef.japanese) > 1:
                for j in wdef.japanese[1:]:
                    if j.word:
                        base += f", [purple]{j.word}"
                        if j.reading is not None:
                            base += f" [red]([white]{j.reading}[red])"
                    else:
                        base += f", [purple]{j.reading}"

            if len(wdef.jlpt):
                base += f" [blue][JLPT: {', '.join(wdef.jlpt)}]"
            console.print(base)

            for i, s in enumerate(wdef):
                base = f"[yellow]{i + 1}. [white]{', '.join(s.english_definitions)}"
                base += "".join([f", ([magenta]{t}[white])" for t in s.tags])
                console.print(base)
            console.print(Markdown("---"))


class Word:
    URL = "https://jisho.org/api/v1/search/words?keyword="
    ROOT = Path.home() / ".jisho/data/word"

    @staticmethod
    def request(
        word: str, cache: bool = False, headers: dict[str, str] | None = None
    ) -> WordRequest | None:
        url = Word.URL + urllib.parse.quote(word)
        toggle = False

        if cache and (Word.ROOT / (word + ".json")).exists():
            try:
                with open(Word.ROOT / (word + ".json"), "r", encoding="utf-8") as fp:
                    content = fp.read()
                    if not content:  # Check if the file is empty
                        console.print(
                            f"[red bold][Error] [white] Cached file is empty for {word}."
                        )
                        toggle = False  # Force a new request
                    else:
                        r = json.loads(content)  # Use loads instead of load
                        toggle = True
            except json.JSONDecodeError:
                console.print(
                    f"[red bold][Error] [white] Cached file is corrupted for {word}."
                )
                toggle = False  # Force a new request

        if not toggle:
            try:
                r = requests.get(url, headers=headers).json()
                r = WordRequest(**r)
                if not len(r):
                    console.print(
                        f"[red bold][Error] [white] No matches found for {word}."
                    )
                    return None

                if cache:
                    # Save the result to cache
                    Word.save(word, r)
            except Exception as e:
                console.print(
                    f"[red bold][Error] [white] Failed to request {word}: {str(e)}"
                )
                return None

        return r

    @staticmethod
    def save(word: str, r: WordRequest | dict[str, Any]) -> None:
        Word.ROOT.mkdir(exist_ok=True)
        try:
            payload = r if isinstance(r, dict) else r.model_dump(exclude_unset=True, by_alias=True)
            with open(Word.ROOT / f"{word}.json", "w", encoding="utf-8") as fp:
                json.dump(payload, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red bold][Error] [white] Failed to save {word}: {str(e)}")
