from __future__ import annotations

import logging
from typing import Any

import httpx

from config import CF_API_TOKEN, CF_API_BASE

logger = logging.getLogger(__name__)

_HEADERS: dict[str, str] = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

_TIMEOUT: float = 20.0


class CloudflareAPIError(Exception):

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        if self.errors:
            details = "; ".join(
                f"[{e.get('code', '?')}] {e.get('message', '')}" for e in self.errors
            )
            return f"{super().__str__()} — {details}"
        return super().__str__()


class CloudflareAPI:

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=CF_API_BASE,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )


    async def __aenter__(self) -> "CloudflareAPI":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._client.aclose()

    def _raise_for_cf_error(self, data: dict, context: str) -> None:

        if not data.get("success", False):
            errors = data.get("errors", [])
            raise CloudflareAPIError(
                f"Cloudflare API error in {context}", errors=errors
            )

    async def _get(self, path: str, **params: Any) -> dict:
        logger.debug("CF GET %s params=%s", path, params)
        resp = await self._client.get(path, params=params or None)
        resp.raise_for_status()
        data: dict = resp.json()
        self._raise_for_cf_error(data, f"GET {path}")
        return data

    async def _post(self, path: str, json: dict) -> dict:
        logger.debug("CF POST %s body=%s", path, json)
        resp = await self._client.post(path, json=json)
        resp.raise_for_status()
        data: dict = resp.json()
        self._raise_for_cf_error(data, f"POST {path}")
        return data

    async def _put(self, path: str, json: dict) -> dict:
        logger.debug("CF PUT %s body=%s", path, json)
        resp = await self._client.put(path, json=json)
        resp.raise_for_status()
        data: dict = resp.json()
        self._raise_for_cf_error(data, f"PUT {path}")
        return data

    async def _delete(self, path: str) -> dict:
        logger.debug("CF DELETE %s", path)
        resp = await self._client.delete(path)
        resp.raise_for_status()
        data: dict = resp.json()
        self._raise_for_cf_error(data, f"DELETE {path}")
        return data

 
    async def get_zones(self) -> list[dict]:

        page = 1
        all_zones: list[dict] = []
        while True:
            data = await self._get("/zones", page=page, per_page=50)
            result_info: dict = data.get("result_info", {})
            all_zones.extend(data.get("result", []))
            if page >= result_info.get("total_pages", 1):
                break
            page += 1
        logger.info("Fetched %d zones from Cloudflare", len(all_zones))
        return all_zones

    async def get_zone(self, zone_id: str) -> dict:

        data = await self._get(f"/zones/{zone_id}")
        return data["result"]

    async def get_dns_records(self, zone_id: str) -> list[dict]:

        page = 1
        all_records: list[dict] = []
        while True:
            data = await self._get(
                f"/zones/{zone_id}/dns_records", page=page, per_page=100
            )
            result_info: dict = data.get("result_info", {})
            all_records.extend(data.get("result", []))
            if page >= result_info.get("total_pages", 1):
                break
            page += 1
        logger.info(
            "Fetched %d DNS records for zone %s", len(all_records), zone_id
        )
        return all_records

    async def get_dns_record(self, zone_id: str, record_id: str) -> dict:

        data = await self._get(f"/zones/{zone_id}/dns_records/{record_id}")
        return data["result"]

    async def create_dns_record(self, zone_id: str, record_data: dict) -> dict:

        data = await self._post(f"/zones/{zone_id}/dns_records", json=record_data)
        logger.info(
            "Created DNS record %s in zone %s", data["result"].get("id"), zone_id
        )
        return data["result"]

    async def update_dns_record(
        self, zone_id: str, record_id: str, record_data: dict
    ) -> dict:

        data = await self._put(
            f"/zones/{zone_id}/dns_records/{record_id}", json=record_data
        )
        logger.info("Updated DNS record %s in zone %s", record_id, zone_id)
        return data["result"]

    async def delete_dns_record(self, zone_id: str, record_id: str) -> dict:

        data = await self._delete(f"/zones/{zone_id}/dns_records/{record_id}")
        logger.info("Deleted DNS record %s from zone %s", record_id, zone_id)
        return data["result"]
