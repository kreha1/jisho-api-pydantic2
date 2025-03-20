from __future__ import annotations

import json
import re
from typing import Any
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from jisho_api.cli import console
from jisho_api.kanji.cfg import KanjiConfig
from jisho_api.util import CLITagger


class RequestMeta(BaseModel):
    status: int


class KanjiRequest(BaseModel):
    meta: RequestMeta
    data: KanjiConfig

    def __len__(self):
        return 1

    def rich_print(self):
        base = f"[green]{self.data.kanji} "
        base += CLITagger.colorize(
            "Kun",
            ", ".join(self.data.main_readings.kun) if self.data.main_readings.kun else "",
            "red",
        )
        base += CLITagger.colorize(
            "On", ", ".join(self.data.main_readings.on) if self.data.main_readings.on else "", "red", last=True
        )
        console.print(base)
        # TODO - TRY on this
        base = CLITagger.colorize("Strokes", self.data.strokes, "yellow")
        try:
            base += CLITagger.colorize("JLPT", self.data.meta.education.jlpt, "magenta")
            base += CLITagger.colorize(
                "Grade", self.data.meta.education.grade, "magenta", last=True
            )
        except Exception as e:
            print(e)
        console.print(base)

        console.print(f"Radical no {self.data.radical.kangxi_order}:")
        console.print(
            CLITagger.colorize(
                "Base",
                f"{self.data.radical.basis} - {self.data.radical.meaning}",
                "yellow",
                last=True,
            )
        )
        try:
            console.print(
                CLITagger.colorize(
                    "Alternate Radical",
                    ", ".join(self.data.radical.alt_forms) if self.data.radical.alt_forms else "",
                    "yellow",
                    last=True,
                )
            )
        except Exception:
            pass
        console.print(
            CLITagger.colorize(
                "Parts", ", ".join(self.data.radical.parts), "yellow", last=True
            )
        )
        try:
            console.print(
                CLITagger.colorize(
                    "Variants",
                    ", ".join(self.data.radical.variants) if self.data.radical.variants else "",
                    "yellow",
                    last=True,
                )
            )
        except Exception:
            pass

        console.print()
        console.print("On Examples:")
        for m in self.data.reading_examples.on:
            bullet_text = (
                f"{m.kanji} [yellow][{m.reading}] [white]{', '.join(m.meanings)}"
            )
            console.print(CLITagger.bullet(bullet_text, color="green"))
        console.print()
        console.print("Kun Examples:")
        for m in self.data.reading_examples.kun:
            bullet_text = (
                f"{m.kanji} [yellow][{m.reading}] [white]{', '.join(m.meanings)}"
            )
            console.print(CLITagger.bullet(bullet_text, color="green"))


class Kanji:
    URL = "https://jisho.org/search/"
    ROOT = Path.home() / ".jisho/data/kanji/"

    @staticmethod
    def strokes(soup: BeautifulSoup) -> str:
        return (
            soup.find_all("div", {"class": "kanji-details__stroke_count"})[0]
            .find("strong")
            .text
        )

    @staticmethod
    def main_meanings(soup: BeautifulSoup) -> list[str]:
        return (
            soup.find_all("div", {"class": "kanji-details__main-meanings"})[0]
            .text.strip()
            .split(", ")
        )

    @staticmethod
    def main_readings(soup: BeautifulSoup) -> dict[str, list[str] | None]:
        res = soup.find_all("div", {"class": "kanji-details__main-readings"})
        try:
            kun = (
                res[0]
                .find_all("dl", {"class": "dictionary_entry kun_yomi"})[0]
                .text.replace("\n", "")
                .replace("Kun:", "")
                .split("、 ")
            )
        except Exception:
            kun = None

        try:
            on = (
                res[0]
                .find_all("dl", {"class": "dictionary_entry on_yomi"})[0]
                .text.replace("\n", "")
                .replace("On:", "")
                .split("、 ")
            )
        except Exception:
            on = None
        return {"kun": kun, "on": on}

    @staticmethod
    def meta(soup: BeautifulSoup) -> dict[str, Any]:
        return {
            "education": Kanji.meta_education(soup),
            "dictionary_idxs": Kanji.meta_dictionary_idxs(soup),
            "classifications": Kanji.meta_classifications(soup),
            "codepoints": Kanji.meta_codepoints(soup),
            "readings": Kanji.meta_readings(soup),
        }

    @staticmethod
    def _scrape_table(table: BeautifulSoup) -> dict[str, str]:
        refs = table.find_all("td", {"class": "dic_ref"})
        names = table.find_all("td", {"class": "dic_name"})
        refs = [r.text.strip() for r in refs]
        names = [n.text.strip() for n in names]
        return {r: n for r, n in zip(refs, names)}

    @staticmethod
    def meta_dictionary_idxs(soup: BeautifulSoup) -> dict[str, str]:
        res = soup.find_all("table", {"summary": "Dictionary indices"})
        return Kanji._scrape_table(res[0])

    @staticmethod
    def meta_classifications(soup: BeautifulSoup) -> dict[str, str]:
        res = soup.find_all("section", {"id": "classifications"})
        return Kanji._scrape_table(res[0])

    @staticmethod
    def meta_codepoints(soup: BeautifulSoup) -> dict[str, str]:
        res = soup.find_all("section", {"id": "codepoints"})
        return Kanji._scrape_table(res[0])

    @staticmethod
    def meta_readings(soup: BeautifulSoup) -> dict[str, list[str] | None]:
        res = soup.find_all("div", {"class": "kanji-details__readings row"})

        try:
            ja = res[0].find_all("dd", {"lang": "ja"})[0].text.split(", ")
        except Exception:
            ja = None
        try:
            cn = res[0].find_all("dl", {"class": "dictionary_entry pinyin"})[0]
            cn = cn.find_all("dd")[0].text
            cn = cn.split(", ")
        except Exception:
            cn = None

        try:
            kr = (
                res[0]
                .find_all("dl", {"class": "dictionary_entry korean"})[0]
                .find_all("dd")[0]
                .text.split(", ")
            )
        except Exception:
            kr = None

        return {
            "japanese": ja,
            "chinese": cn,
            "korean": kr,
        }

    @staticmethod
    def meta_education(soup: BeautifulSoup) -> dict[str, Any]:
        res = soup.find_all("div", {"class": "kanji_stats"})[
            0
        ]  # .find_all("strong")[0]

        try:
            grade = (
                res.find_all("div", {"class": "grade"})[0]
                .find_all("strong")[0]
                .text  # the grade is sometimes "junior high". shouldn't use .split(" ")[-1]
            )
        except Exception:
            grade = None

        try:
            jlpt = res.find_all("div", {"class": "jlpt"})[0].find_all("strong")[0].text
        except Exception:
            jlpt = None

        try:
            frequency = (
                res.find_all("div", {"class": "frequency"})[0]
                .find_all("strong")[0]
                .text
            )
        except Exception:
            frequency = None

        return {"grade": grade, "jlpt": jlpt, "newspaper_rank": frequency}

    @staticmethod
    def reading_examples(soup: BeautifulSoup) -> dict[str, list[dict[str, str]] | None]:
        def threeway(x: str) -> tuple[str, str, str]:
            return (
                x[: x.index("【")],
                x[x.index("【") + 1 : x.index("】")],
                x[x.index("】") + 1 :],
            )

        def process(x: list[tuple[str, str, str]]) -> list[dict[str, str | list[str]]]:
            return [
                {
                    "kanji": k.replace("\n", "").strip(),
                    "reading": r.replace("\n", "").strip(),
                    "meanings": m.replace("\n", "").strip().split(", "),
                }
                for k, r, m in x
            ]

        try:
            res = soup.find_all("ul", {"class": "no-bullet"})
            on = res[0].find_all("li")
            ons = process([threeway(o.text) for o in on])

            try:
                kun = res[1].find_all("li")
                kuns = process([threeway(k.text) for k in kun])
            except Exception:
                kuns = None

            return {
                "on": ons,
                "kun": kuns,
            }
        except Exception:
            return None

    @staticmethod
    def radical(soup: BeautifulSoup) -> dict[str, Any]:
        try:
            variants = (
                soup.find_all("dl", {"class": "dictionary_entry variants"})[0]
                .find("a")
                .text.split(" ")
            )
        except Exception:
            variants = None

        res = soup.find_all("div", {"class": "radicals"})

        parts = res[1].find_all("a")
        parts = [p.text for p in parts]

        rad = res[0]
        rad = rad.find_all("span")
        rad_span = re.sub(" +", " ", rad[0].text.replace("\n", "")).strip()
        if "(" in rad_span and ")" in rad_span:
            prn_idx = rad_span.index("(")
            rad_span_left = rad_span[:prn_idx]
            rad_span_right = rad_span[prn_idx + 1 : -1]
            rad_alt_form = rad_span_right.split(", ")
        else:
            rad_span_left = rad_span
            rad_alt_form = None
        rad_span_left = rad_span_left.strip().split(" ")

        rad_meaning = rad_span_left[0]
        rad_basis = rad_span_left[-1]
        rad_no = rad[0]["title"].split(" ")[-1][:-1]
        if not rad_no.isdigit():
            rad_no = None

        return {
            "alt_forms": rad_alt_form,
            "meaning": rad_meaning,
            "basis": rad_basis,
            "kangxi_order": rad_no,
            "variants": variants,
            "parts": parts,
        }

    @staticmethod
    def request(
        kanji: str,
        cache: bool = False,
        headers: dict[str, str] | None = None,
    ) -> KanjiRequest | None:
        url = Kanji.URL + urllib.parse.quote(kanji + " #kanji")
        toggle = False

        if cache and (Kanji.ROOT / (kanji + ".json")).exists():
            toggle = True
            with open(Kanji.ROOT / (kanji + ".json"), "r", encoding="utf-8") as fp:
                r = json.load(fp)
            r = KanjiRequest(**r)
        else:
            r = requests.get(url, headers=headers).content

            soup = BeautifulSoup(r, "html.parser")

            try:
                r = KanjiRequest(
                    meta=RequestMeta(status=200),
                    data=KanjiConfig(
                        kanji=kanji,
                        strokes=Kanji.strokes(soup),
                        main_meanings=Kanji.main_meanings(soup),
                        main_readings=Kanji.main_readings(soup),
                        meta=Kanji.meta(soup),
                        radical=Kanji.radical(soup),
                        reading_examples=Kanji.reading_examples(soup),
                    ),
                )
                if not len(r):
                    console.print(
                        f"[red bold][Error] [white] No matches found for {kanji}."
                    )
                    return None
            except Exception as e:
                console.print(
                    f"[red bold ][Error][/red bold] [white]Failed to request {kanji}: {e}"
                )
                return None
        if cache and not toggle:
            Kanji.save(kanji, r)
        return r

    @staticmethod
    def save(word: str, r: KanjiRequest | dict[str, Any]) -> None:
        Kanji.ROOT.mkdir(exist_ok=True)
        try:
            payload = r if isinstance(r, dict) else r.model_dump(exclude_unset=True, by_alias=True)
            with open(Kanji.ROOT / f"{word}.json", "w", encoding="utf-8") as fp:
                json.dump(payload, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red bold][Error] [white] Failed to save {word}: {str(e)}")

