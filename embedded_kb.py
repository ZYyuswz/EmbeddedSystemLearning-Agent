"""
本地嵌入式知识库：JSON + TF-IDF 检索，可选 related/prerequisite 子图（不用 Neo4j）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _doc_text(d: dict[str, Any]) -> str:
    tags = d.get("tags") or []
    plat = d.get("platform") or []
    if isinstance(tags, str):
        tags = [tags]
    if isinstance(plat, str):
        plat = [plat]
    parts = [d.get("title") or "", " ".join(tags), " ".join(plat), d.get("body") or ""]
    return "\n".join(parts)


class EmbeddedKB:
    def __init__(self, json_path: str | None = None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.path = json_path or os.path.join(base, "data", "embedded", "embedded_kb.json")
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            raise ValueError("embedded_kb.json 顶层应为数组")
        self.docs: list[dict[str, Any]] = raw
        self._by_id = {d["id"]: d for d in self.docs if "id" in d}
        corpus = [_doc_text(d) for d in self.docs]
        self._vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(1, 2),
            max_features=8000,
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, platform: str | None, top_k: int = 5) -> list[tuple[dict[str, Any], float]]:
        if not query.strip():
            return []
        qv = self._vectorizer.transform([query])
        sims = cosine_similarity(qv, self._matrix)[0]
        boost = np.ones(len(self.docs))
        if platform and platform != "全部":
            for i, d in enumerate(self.docs):
                plats = d.get("platform") or []
                if isinstance(plats, str):
                    plats = [plats]
                if platform in plats or "通用" in plats:
                    boost[i] = 1.25
        ranked = sims * boost
        idx = np.argsort(-ranked)[:top_k]
        out: list[tuple[dict[str, Any], float]] = []
        for i in idx:
            score = float(ranked[i])
            if score <= 0:
                continue
            out.append((self.docs[int(i)], score))
        return out

    def subgraph_for_docs(self, hits: list[dict[str, Any]], max_nodes: int = 12) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
        """返回节点列表与 (from_id, to_id, edge_type) 边，用于 Mermaid。"""
        seen: set[str] = set()
        nodes: list[dict[str, Any]] = []
        edges: list[tuple[str, str, str]] = []

        def add_node(doc_id: str) -> None:
            if doc_id in seen or len(nodes) >= max_nodes:
                return
            d = self._by_id.get(doc_id)
            if not d:
                return
            seen.add(doc_id)
            nodes.append(d)

        for d in hits:
            add_node(d["id"])
        for d in list(nodes):
            if len(nodes) >= max_nodes:
                break
            for rid in (d.get("related_ids") or [])[:4]:
                if len(nodes) >= max_nodes:
                    break
                add_node(rid)
                edges.append((d["id"], rid, "related"))
            for pid in (d.get("prerequisite_ids") or [])[:2]:
                if len(nodes) >= max_nodes:
                    break
                add_node(pid)
                edges.append((pid, d["id"], "prerequisite"))
        return nodes, edges

    @staticmethod
    def mermaid_from_subgraph(nodes: list[dict[str, Any]], edges: list[tuple[str, str, str]]) -> str:
        def safe(s: str) -> str:
            return re.sub(r'["\n\r]', " ", s)[:40]

        lines = ["graph LR"]
        id2short: dict[str, str] = {}
        for i, d in enumerate(nodes):
            sid = f"N{i}"
            id2short[d["id"]] = sid
            lines.append(f'  {sid}["{safe(d.get("title") or d["id"])}"]')
        for a, b, typ in edges:
            if a not in id2short or b not in id2short:
                continue
            sym = "-->" if typ == "related" else "-.前置.->"
            lines.append(f"  {id2short[a]}{sym}{id2short[b]}")
        return "\n".join(lines) if len(lines) > 1 else ""
