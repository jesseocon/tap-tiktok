"""REST client handling, including TikTokStream base class."""

import json
import requests
from typing import Any, Dict, List, Optional

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

DATE_FORMAT = "%Y-%m-%d"


def resolve_advertiser_ids(config: dict) -> List[str]:
    """Resolve the list of advertiser IDs to sync from tap config.

    Prefers the comma-separated `advertiser_ids` config. Falls back to the
    legacy `advertiser_id` field for backwards compatibility. Whitespace
    around each ID is stripped and empty entries are dropped.
    """
    raw_ids = config.get("advertiser_ids")
    if raw_ids:
        ids = [x.strip() for x in str(raw_ids).split(",") if x.strip()]
        if ids:
            return ids

    legacy_id = config.get("advertiser_id")
    if legacy_id:
        trimmed = str(legacy_id).strip()
        if trimmed:
            return [trimmed]

    return []


class TikTokStream(RESTStream):

    url_base = "https://business-api.tiktok.com/open_api/v1.3"

    records_jsonpath = "$.data.list[*]"

    @property
    def partitions(self) -> Optional[List[dict]]:
        """Fan out one request per configured advertiser ID."""
        return [
            {"advertiser_id": advertiser_id}
            for advertiser_id in resolve_advertiser_ids(self.config)
        ]

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        headers["Content-Type"] = "application/json"
        headers["Access-Token"] = self.config["access_token"].__str__()
        return headers

    def _advertiser_id_for(self, context: Optional[dict]) -> str:
        """Return the advertiser_id for the current partition context.

        Falls back to the first resolved advertiser ID when no context is
        provided (e.g. during discovery or ad-hoc invocations).
        """
        if context and context.get("advertiser_id"):
            return context["advertiser_id"]
        ids = resolve_advertiser_ids(self.config)
        if not ids:
            raise ValueError(
                "tap-tiktok requires either `advertiser_ids` (comma-separated) "
                "or the legacy `advertiser_id` config to be set."
            )
        return ids[0]

    @staticmethod
    def _get_page_info(json_path, json):
        page_matches = extract_jsonpath(json_path, json)
        return next(iter(page_matches), None)

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        current_page = self._get_page_info("$.data.page_info.page", response.json()) or 0
        total_pages = self._get_page_info("$.data.page_info.total_page", response.json()) or 0
        if current_page < total_pages:
            return current_page + 1
        return None

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {"advertiser_id": self._advertiser_id_for(context)}
        if next_page_token:
            params["page"] = next_page_token
        params["filtering"] = json.dumps({"primary_status": "STATUS_ALL" if self.config.get("include_deleted") else "STATUS_NOT_DELETE"})
        params["page_size"] = 10
        return params


class TikTokReportsStream(TikTokStream):

    url_base = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"

    records_jsonpath = "$.data.list[*]"
    next_page_token_jsonpath = "$.page_info.page"

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        record = {**row["dimensions"], **row["metrics"]}
        record["advertiser_id"] = self._advertiser_id_for(context)
        return record

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        page_matches = extract_jsonpath("$.data.page_info.page", response.json())
        page_match = next(iter(page_matches), None)
        current_page = page_match
        total_pages_matches = extract_jsonpath("$.data.page_info.total_page", response.json())
        total_pages_match = next(iter(total_pages_matches), None)
        total_pages = total_pages_match
        if current_page < total_pages:
            return current_page + 1
        return None
