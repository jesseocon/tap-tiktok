"""TikTok tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_tiktok.client import resolve_advertiser_ids
from tap_tiktok.streams import (
    AdAccountsStream,
    CampaignsStream,
    AdGroupsStream,
    AdsStream,
    AdsAttributeMetricsStream,
    AdsBasicDataMetricsByDayStream,
    AdsVideoPlayMetricsByDayStream,
    AdsEngagementMetricsByDayStream,
    AdsAttributionMetricsByDayStream,
    AdsPageEventMetricsByDayStream,
    AdsInAppEventMetricsByDayStream,
    CampaignsAttributeMetricsStream,
    CampaignsBasicDataMetricsByDayStream,
    CampaignsVideoPlayMetricsByDayStream,
    CampaignsEngagementMetricsByDayStream,
    CampaignsAttributionMetricsByDayStream,
    CampaignsPageEventMetricsByDayStream,
    CampaignsInAppEventMetricsByDayStream
)
STREAM_TYPES = [
    AdAccountsStream,
    CampaignsStream,
    AdGroupsStream,
    AdsStream,
    AdsAttributeMetricsStream,
    AdsBasicDataMetricsByDayStream,
    AdsVideoPlayMetricsByDayStream,
    AdsEngagementMetricsByDayStream,
    AdsAttributionMetricsByDayStream,
    AdsPageEventMetricsByDayStream,
    AdsInAppEventMetricsByDayStream,
    CampaignsAttributeMetricsStream,
    CampaignsBasicDataMetricsByDayStream,
    CampaignsVideoPlayMetricsByDayStream,
    CampaignsEngagementMetricsByDayStream,
    CampaignsAttributionMetricsByDayStream,
    CampaignsPageEventMetricsByDayStream,
    CampaignsInAppEventMetricsByDayStream
]


class TapTikTok(Tap):
    """TikTok tap class."""
    name = "tap-tiktok"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "access_token",
            th.StringType,
            required=True,
            description="The token to authenticate against the API service"
        ),
        th.Property(
            "advertiser_id",
            th.StringType,
            required=False,
            description=(
                "Advertiser ID. Kept for backwards compatibility; prefer "
                "`advertiser_ids` for multi-advertiser syncs. Used only when "
                "`advertiser_ids` is not provided."
            )
        ),
        th.Property(
            "advertiser_ids",
            th.StringType,
            required=False,
            description=(
                "Comma-separated list of advertiser IDs to sync. Whitespace "
                "around each ID is trimmed. Takes precedence over "
                "`advertiser_id` when set."
            )
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync"
        ),
        th.Property(
            "include_deleted",
            th.BooleanType,
            default=True,
            description="If true then deleted status entities will also be returned"
        ),
        th.Property(
            "lookback",
            th.IntegerType,
            default=14,
            description="The number of days of data to reload from the current date (ignored if current state of the extractor has a start date earlier than the current date minus number of lookback days)"
        )
    ).to_dict()

    @property
    def advertiser_id_list(self) -> List[str]:
        """Return the resolved list of advertiser IDs to sync.

        Prefers the comma-separated `advertiser_ids` config. Falls back to the
        legacy `advertiser_id` field for backwards compatibility. Whitespace
        around each ID is stripped and empty entries are dropped.
        """
        ids = resolve_advertiser_ids(self.config)
        if not ids:
            raise ValueError(
                "tap-tiktok requires either `advertiser_ids` (comma-separated) "
                "or the legacy `advertiser_id` config to be set."
            )
        return ids

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
