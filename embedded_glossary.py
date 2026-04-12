"""嵌入式术语表：Aho-Corasick 匹配 `data/embedded/glossary.txt`。"""
from __future__ import annotations

import os

import ahocorasick


class GlossaryMatcher:
    def __init__(self, path: str | None = None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(base, "data", "embedded", "glossary.txt")
        self.auto = ahocorasick.Automaton()
        self._ready = False
        if os.path.isfile(self.path):
            n = 0
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    w = line.strip()
                    if len(w) >= 2:
                        self.auto.add_word(w, w)
                        n += 1
            if n > 0:
                self.auto.make_automaton()
                self._ready = True

    def find(self, text: str) -> list[str]:
        if not self._ready or not text:
            return []
        found: dict[str, None] = {}
        for _, w in self.auto.iter(text):
            found[w] = None
        return sorted(found.keys(), key=len, reverse=True)
