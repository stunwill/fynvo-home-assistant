from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger("fynvo.banking.redbark")

REDBARK_BASE_URL = "https://api.redbark.com"
REDBARK_PROVIDER_ID = "redbark"
REDBARK_PROVIDER_NAME = "Redbark Open Banking"
REDBARK_PAGE_SIZE = 200


@dataclass(slots=True)
class RedbarkError(Exception):
    message: str
    status_code: int = 502
    code: str | None = None
    retry_after: int | None = None

    def __str__(self) -> str:
        return self.message


class RedbarkProvider:
    provider = REDBARK_PROVIDER_ID
    name = REDBARK_PROVIDER_NAME

    def __init__(self, api_key: str, base_url: str = REDBARK_BASE_URL, client: httpx.Client | None = None):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self._client = client

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise RedbarkError("Redbark API key is not configured.", status_code=401, code="missing_api_key")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=httpx.Timeout(20.0, connect=10.0))
        try:
            response = client.get(f"{self.base_url}{path}", params=params or {}, headers=headers)
        except httpx.HTTPError as exc:
            raise RedbarkError("Redbark could not be reached. Last-known banking data is still available.") from exc
        finally:
            if owns_client:
                client.close()
        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After")
            retry_after = int(retry_after_raw) if retry_after_raw and retry_after_raw.isdigit() else None
            raise RedbarkError(
                "Redbark rate limit reached. Try again shortly.",
                status_code=429,
                code="rate_limited",
                retry_after=retry_after,
            )
        payload: dict[str, Any]
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            error = payload.get("error") if isinstance(payload, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            if response.status_code == 401:
                message = "Redbark rejected the API key. Review the bank connection credentials."
            elif response.status_code == 503:
                message = "Redbark or the connected bank is temporarily unavailable. Last-known banking data is still available."
            else:
                message = "Redbark could not refresh banking data. Last-known banking data is still available."
            raise RedbarkError(message, status_code=response.status_code, code=code)
        return payload

    def validate(self) -> dict[str, Any]:
        connections = self.connections()
        return {"status": "ok", "connection_count": len(connections)}

    def connections(self) -> list[dict[str, Any]]:
        payload = self._request("/v1/connections")
        rows = payload.get("data") or []
        return [
            {
                "id": str(row.get("id") or ""),
                "provider": str(row.get("provider") or self.provider),
                "category": str(row.get("category") or "banking"),
                "institution_id": str(row.get("institutionId") or ""),
                "institution_name": str(row.get("institutionName") or "Bank connection"),
                "status": str(row.get("status") or "unknown"),
                "last_refreshed_at": row.get("lastRefreshedAt"),
                "created_at": row.get("createdAt"),
            }
            for row in rows
            if row.get("id")
        ]

    def accounts(self) -> list[dict[str, Any]]:
        offset = 0
        output: list[dict[str, Any]] = []
        while True:
            payload = self._request("/v1/accounts", {"limit": REDBARK_PAGE_SIZE, "offset": offset})
            rows = payload.get("data") or []
            for row in rows:
                number = str(row.get("accountNumber") or "")
                suffix = number[-4:] if number else ""
                output.append(
                    {
                        "provider_account_id": str(row.get("id") or ""),
                        "connection_id": str(row.get("connectionId") or ""),
                        "name": str(row.get("name") or "Bank account"),
                        "account_type": str(row.get("type") or "transaction").lower(),
                        "institution": str(row.get("institutionName") or "Bank"),
                        "masked_identifier": f"•••• {suffix}" if suffix else "",
                        "currency": str(row.get("currency") or "AUD"),
                    }
                )
            pagination = payload.get("pagination") or {}
            if not pagination.get("hasMore") or not rows:
                break
            offset = int(pagination.get("offset") or offset) + int(pagination.get("limit") or REDBARK_PAGE_SIZE)
        return output

    def balances(self, account_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not account_ids:
            return {}
        payload = self._request("/v1/balances", {"accountIds": ",".join(account_ids)})
        return {
            str(row.get("accountId")): {
                "current_balance": row.get("currentBalance"),
                "available_balance": row.get("availableBalance"),
                "currency": row.get("currency"),
            }
            for row in (payload.get("data") or [])
            if row.get("accountId")
        }

    def transactions(
        self,
        connection_id: str,
        account_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        *,
        retry_rate_limit_once: bool = True,
    ) -> list[dict[str, Any]]:
        offset = 0
        output: list[dict[str, Any]] = []
        while True:
            params: dict[str, Any] = {
                "connectionId": connection_id,
                "limit": REDBARK_PAGE_SIZE,
                "offset": offset,
                # Redbark exposes the switch but currently documents posted-only data.
                "includePending": "false",
            }
            if account_id:
                params["accountId"] = account_id
            if date_from:
                params["from"] = date_from.isoformat()
            if date_to:
                params["to"] = date_to.isoformat()
            try:
                payload = self._request("/v1/transactions", params)
            except RedbarkError as exc:
                if exc.status_code == 429 and retry_rate_limit_once and exc.retry_after is not None and exc.retry_after <= 10:
                    time.sleep(max(1, exc.retry_after))
                    retry_rate_limit_once = False
                    continue
                raise
            rows = payload.get("data") or []
            for row in rows:
                direction = str(row.get("direction") or "").lower()
                amount_text = str(row.get("amount") or "0")
                output.append(
                    {
                        "id": str(row.get("id") or ""),
                        "account_id": str(row.get("accountId") or ""),
                        "date": row.get("date"),
                        "datetime": row.get("datetime"),
                        "posted_date": row.get("postDate") or row.get("date"),
                        "amount": amount_text,
                        "direction": direction,
                        "description": str(row.get("description") or "Bank transaction"),
                        "merchant": row.get("merchantName"),
                        "category": row.get("customCategory") or row.get("category"),
                        "merchant_category_code": row.get("merchantCategoryCode"),
                        "status": "posted",
                    }
                )
            pagination = payload.get("pagination") or {}
            if not pagination.get("hasMore") or not rows:
                break
            offset = int(pagination.get("offset") or offset) + int(pagination.get("limit") or REDBARK_PAGE_SIZE)
        return output
