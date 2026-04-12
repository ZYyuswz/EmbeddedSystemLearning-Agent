"""官方资料同步服务。"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from backend.infrastructure.official_source_client import fetch_sources, parse_specs
from backend.models.schemas import KnowledgeCacheInfo, KnowledgeSyncResponse, SourcePolicy, SourceRefResponse, SpecSummary
from backend.repositories.sqlite_repo import SQLiteRepo

_KNOWLEDGE_CACHE_TTL_SEC = 24 * 3600


def sync_official_sources(
    repo: SQLiteRepo,
    board_model: str,
    vendor_hint: str | None,
    force_refresh: bool,
    source_policy: SourcePolicy,
) -> KnowledgeSyncResponse:
    """同步官方资料并返回规格摘要。"""
    cache_key = _build_cache_key(board_model, vendor_hint, source_policy)
    cached = repo.get_knowledge_cache(cache_key)

    if cached and (not force_refresh) and _is_not_expired(cached["expiresAt"]):
        return _build_response(cached["payload"], cache_hit=True, expires_at=cached["expiresAt"], ttl_sec=cached["ttlSec"])

    knowledge_id = f"kb_{uuid4().hex[:12]}"
    sources, digest = fetch_sources(board_model, vendor_hint, source_policy)
    summary = parse_specs(board_model, sources)
    payload = {
        "knowledgeId": knowledge_id,
        "sources": sources,
        "specSummary": summary,
    }
    repo.save_knowledge_cache(cache_key, board_model, payload, digest, _KNOWLEDGE_CACHE_TTL_SEC)
    repo.save_source_refs(knowledge_id, sources)

    expires_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + _KNOWLEDGE_CACHE_TTL_SEC,
        tz=timezone.utc,
    ).isoformat()
    return _build_response(payload, cache_hit=False, expires_at=expires_at, ttl_sec=_KNOWLEDGE_CACHE_TTL_SEC)


def _build_cache_key(board_model: str, vendor_hint: str | None, source_policy: SourcePolicy) -> str:
    """构造缓存键。"""
    seed = f"{board_model}|{vendor_hint or ''}|{source_policy.model_dump_json()}"
    return sha256(seed.encode("utf-8")).hexdigest()


def _is_not_expired(expires_at: str) -> bool:
    """判断缓存是否过期。"""
    return datetime.fromisoformat(expires_at) > datetime.now(timezone.utc)


def _build_response(payload: dict, cache_hit: bool, expires_at: str, ttl_sec: int) -> KnowledgeSyncResponse:
    """构造资料同步响应。"""
    return KnowledgeSyncResponse(
        knowledgeId=payload["knowledgeId"],
        sources=[SourceRefResponse(**item) for item in payload["sources"]],
        specSummary=SpecSummary(**payload["specSummary"]),
        cache=KnowledgeCacheInfo(cacheHit=cache_hit, expiresAt=datetime.fromisoformat(expires_at), ttlSec=ttl_sec),
    )
