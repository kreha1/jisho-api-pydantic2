from __future__ import annotations
from enum import Enum

from pydantic import BaseModel, Field


class JLPT(str, Enum):
    N5 = "N5"
    N4 = "N4"
    N3 = "N3"
    N2 = "N2"
    N1 = "N1"


class MainReadings(BaseModel):
    kun: list[str] | None = Field(default=None)
    on: list[str] | None = Field(default=None)


class KanjiRadical(BaseModel):
    alt_forms: list[str] | None = Field(default=None)
    meaning: str
    parts: list[str]
    basis: str
    kangxi_order: int | None = Field(default=None)
    variants: list[str] | None = Field(default=None)


class KanjiMeta(BaseModel):
    class KanjiMetaEducation(BaseModel):
        grade: str | None = Field(default=None)
        jlpt: JLPT | None = Field(default=None)
        newspaper_rank: int | None = Field(default=None)

    class KanjiMetaReadings(BaseModel):
        japanese: list[str] | None = Field(default=None)
        chinese: list[str] | None = Field(default=None)
        korean: list[str] | None = Field(default=None)

    education: KanjiMetaEducation | None = Field(default=None)
    dictionary_idxs: dict[str, str] | None = Field(default=None)
    classifications: dict[str, str] | None = Field(default=None)
    codepoints: dict[str, str] | None = Field(default=None)
    readings: KanjiMetaReadings | None = Field(default=None)


class ReadingExamples(BaseModel):
    class Example(BaseModel):
        kanji: str
        reading: str
        meanings: list[str]

    kun: list[Example] | None = Field(default=None)
    on: list[Example] | None = Field(default=None)


class KanjiConfig(BaseModel):
    kanji: str
    strokes: int
    main_meanings: list[str]
    main_readings: MainReadings
    meta: KanjiMeta
    radical: KanjiRadical
    # relation to words
    # on and kun are verifiable properties of the graph
    reading_examples: ReadingExamples | None = Field(default=None)
