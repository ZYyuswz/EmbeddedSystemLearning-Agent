"""官方资料抓取客户端。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from hashlib import sha256

import httpx

from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import SourcePolicy


OFFICIAL_SOURCE_MAP = {
    "STM32F103C8T6-BluePill": [
        {
            "url": "https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html",
            "sourceType": "official_site",
        },
        {"url": "https://www.st.com/en/development-tools/stm32cubef1.html", "sourceType": "official_docs"},
        {"url": "https://github.com/STMicroelectronics/STM32CubeF1", "sourceType": "official_repo"},
    ],
    "ESP32-DevKitC": [
        {"url": "https://www.espressif.com/en/products/devkits/esp32-devkitc", "sourceType": "official_site"},
        {"url": "https://docs.espressif.com/projects/esp-idf/en/stable/esp32/", "sourceType": "official_docs"},
        {"url": "https://github.com/espressif/esp-idf", "sourceType": "official_repo"},
    ],
}

SPEC_SUMMARY_MAP = {
    "STM32F103C8T6-BluePill": {
        "mcu": "STM32F103C8T6",
        "flashKB": 64,
        "ramKB": 20,
        "supportedProgrammers": ["stlink", "uart_bootloader"],
    },
    "ESP32-DevKitC": {
        "mcu": "ESP32",
        "flashKB": 4096,
        "ramKB": 520,
        "supportedProgrammers": ["esptool"],
    },
}


def fetch_sources(board_model: str, vendor_hint: str | None, source_policy: SourcePolicy) -> tuple[list[dict[str, str]], str]:
    """获取指定板卡的官方资料来源并返回内容摘要哈希。"""
    _ = vendor_hint
    seed_sources = OFFICIAL_SOURCE_MAP.get(board_model)
    if not seed_sources:
        raise AppException(ErrorCode.OFFICIAL_SOURCE_NOT_FOUND, "未找到官方资料来源", status_code=404)

    allowed_sources = _filter_sources(seed_sources, source_policy)
    if not allowed_sources:
        raise AppException(ErrorCode.OFFICIAL_SOURCE_NOT_FOUND, "当前策略未启用任何资料来源", status_code=422)

    fetched_at = datetime.now(timezone.utc).isoformat()
    digest_seed: list[str] = []
    reachable: list[dict[str, str]] = []
    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
        for item in allowed_sources:
            url = item["url"]
            try:
                response = client.head(url)
                if response.status_code >= 400:
                    response = client.get(url)
                if response.status_code < 400:
                    reachable.append({**item, "fetchedAt": fetched_at})
                    digest_seed.append(f"{url}:{response.status_code}")
            except httpx.HTTPError:
                continue

    if not reachable:
        # 在网络受限环境下允许降级返回静态来源，保持主流程可用。
        reachable = [{**item, "fetchedAt": fetched_at} for item in allowed_sources]
        digest_seed.extend(item["url"] for item in allowed_sources)

    digest = sha256("|".join(sorted(digest_seed)).encode("utf-8")).hexdigest()
    return _deduplicate_sources(reachable), digest


def parse_specs(board_model: str, sources: list[dict[str, str]]) -> dict[str, object]:
    """解析板卡规格摘要。"""
    spec = SPEC_SUMMARY_MAP.get(board_model)
    if spec:
        return spec

    derived = _derive_spec_from_sources(sources)
    if derived:
        return derived
    raise AppException(ErrorCode.OFFICIAL_SOURCE_PARSE_FAILED, "板卡规格解析失败", status_code=422)


def _derive_spec_from_sources(sources: list[dict[str, str]]) -> dict[str, object] | None:
    """从来源 URL 粗略推导规格信息。"""
    joined = " ".join(item.get("url", "") for item in sources).lower()
    if "esp32" in joined:
        return {"mcu": "ESP32", "flashKB": 4096, "ramKB": 520, "supportedProgrammers": ["esptool"]}
    if re.search(r"stm32f1|f103", joined):
        return {
            "mcu": "STM32F103",
            "flashKB": 64,
            "ramKB": 20,
            "supportedProgrammers": ["stlink", "uart_bootloader"],
        }
    return None


def _filter_sources(seed_sources: list[dict[str, str]], source_policy: SourcePolicy) -> list[dict[str, str]]:
    """按策略过滤来源。"""
    allowed: list[dict[str, str]] = []
    for item in seed_sources:
        source_type = item["sourceType"]
        if source_type == "official_repo" and source_policy.allowApi:
            allowed.append(item)
        elif source_type == "official_site" and source_policy.allowWeb:
            allowed.append(item)
        elif source_type == "official_docs" and (source_policy.allowWeb or source_policy.allowPdfIndex):
            allowed.append(item)
    return allowed


def _deduplicate_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    """去重来源 URL。"""
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in sources:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped
