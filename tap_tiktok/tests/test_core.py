"""Tests for tap-tiktok core functionality."""

import datetime

import pytest

from tap_tiktok.client import TikTokStream, resolve_advertiser_ids
from tap_tiktok.streams import AdsBasicDataMetricsByDayStream
from tap_tiktok.tap import TapTikTok


class TestResolveAdvertiserIds:
    def test_comma_separated_ids(self):
        config = {"advertiser_ids": "111, 222, 333"}
        assert resolve_advertiser_ids(config) == ["111", "222", "333"]

    def test_whitespace_trimmed(self):
        config = {"advertiser_ids": " 111 , 222 , 333 "}
        assert resolve_advertiser_ids(config) == ["111", "222", "333"]

    def test_empty_entries_dropped(self):
        config = {"advertiser_ids": "111,,222, ,333"}
        assert resolve_advertiser_ids(config) == ["111", "222", "333"]

    def test_advertiser_ids_takes_precedence(self):
        config = {
            "advertiser_ids": "111, 222",
            "advertiser_id": "999",
        }
        assert resolve_advertiser_ids(config) == ["111", "222"]

    def test_legacy_advertiser_id_fallback(self):
        config = {"advertiser_id": "7611205919788679184"}
        assert resolve_advertiser_ids(config) == ["7611205919788679184"]

    def test_empty_config_returns_empty_list(self):
        assert resolve_advertiser_ids({}) == []

    def test_blank_advertiser_ids_falls_back_to_legacy(self):
        config = {"advertiser_ids": " , ", "advertiser_id": "999"}
        assert resolve_advertiser_ids(config) == ["999"]


class TestTikTokStreamPartitions:
    @pytest.fixture
    def stream(self):
        tap = TapTikTok(
            config={
                "access_token": "test-token",
                "start_date": "2025-01-01",
                "advertiser_ids": "111, 222, 333",
            }
        )
        return AdsBasicDataMetricsByDayStream(tap=tap)

    def test_partitions_returns_one_dict_per_advertiser(self, stream):
        assert stream.partitions == [
            {"advertiser_id": "111"},
            {"advertiser_id": "222"},
            {"advertiser_id": "333"},
        ]

    def test_advertiser_id_for_uses_context(self, stream):
        assert stream._advertiser_id_for({"advertiser_id": "222"}) == "222"

    def test_advertiser_id_for_falls_back_to_first_id(self, stream):
        assert stream._advertiser_id_for(None) == "111"

    def test_advertiser_id_for_raises_when_unconfigured(self):
        tap = TapTikTok(
            config={
                "access_token": "test-token",
                "start_date": "2025-01-01",
            }
        )
        stream = AdsBasicDataMetricsByDayStream(tap=tap)
        with pytest.raises(ValueError, match="advertiser_ids"):
            stream._advertiser_id_for(None)


class TestTikTokReportsStreamPostProcess:
    @pytest.fixture
    def stream(self):
        tap = TapTikTok(
            config={
                "access_token": "test-token",
                "start_date": "2025-01-01",
                "advertiser_ids": "111, 222",
            }
        )
        return AdsBasicDataMetricsByDayStream(tap=tap)

    def test_post_process_injects_advertiser_id(self, stream):
        row = {
            "dimensions": {"ad_id": "ad-1", "stat_time_day": "2025-01-01"},
            "metrics": {"spend": "10.00"},
        }
        record = stream.post_process(row, context={"advertiser_id": "222"})
        assert record == {
            "ad_id": "ad-1",
            "stat_time_day": "2025-01-01",
            "spend": "10.00",
            "advertiser_id": "222",
        }


class TestTapAdvertiserIdList:
    def test_advertiser_id_list_resolves_ids(self):
        tap = TapTikTok(
            config={
                "access_token": "test-token",
                "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
                "advertiser_ids": "111, 222",
            }
        )
        assert tap.advertiser_id_list == ["111", "222"]

    def test_advertiser_id_list_raises_when_unconfigured(self):
        tap = TapTikTok(
            config={
                "access_token": "test-token",
                "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            }
        )
        with pytest.raises(ValueError, match="advertiser_ids"):
            _ = tap.advertiser_id_list
