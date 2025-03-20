from __future__ import annotations

from typing import Iterator

from pydantic import BaseModel, Field, HttpUrl


class Sense(BaseModel):
    class Link(BaseModel):
        text: str
        url: HttpUrl

    class Source(BaseModel):
        language: str

    english_definitions: list[str]
    parts_of_speech: list[str | None] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    see_also: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    source: list[Source] = Field(default_factory=list)
    info: list[str] = Field(default_factory=list)


class Japanese(BaseModel):
    # Japanese Word - full fledged kanji
    # Is optional because there are words that are just kana
    word: str | None = Field(default=None)
    # Kana reading
    reading: str | None = Field(default=None)

    @property
    def name(self):
        if self.word:
            return self.word
        return self.reading


class WordConfig(BaseModel):
    slug: str
    is_common: bool | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)

    jlpt: list[str] = Field(default_factory=list)
    japanese: list[Japanese] = Field(default_factory=list)
    senses: list[Sense] = Field(default_factory=list)

    def __iter__(self) -> Iterator[Sense]:
        yield from self.senses
