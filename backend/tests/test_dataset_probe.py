import pytest

from urbancanopy.sources import dataset_probe_result


def test_dataset_probe_result_reports_live_success() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel2",
        status="live_success",
        detail="catalog probe succeeded",
        capability="working_now",
        actual_transport="planetary_computer_stac",
    )

    assert result["event"] == "dataset.probe.succeeded"
    assert result["level"] == "info"
    assert result["fallbackUsed"] is False
    assert result["message"] == "catalog probe succeeded"
    assert result["meta"] == {
        "provider": "copernicus",
        "datasource": "copernicus",
        "source_key": "sentinel2",
        "status": "live_success",
        "capability": "working_now",
        "actual_transport": "planetary_computer_stac",
        "detail": "catalog probe succeeded",
    }


def test_dataset_probe_result_reports_live_failure_with_fallback() -> None:
    result = dataset_probe_result(
        provider="opendatacube",
        source_key="landsat",
        status="live_failure_fallback",
        detail="catalog probe failed",
        capability="needs_fix",
        actual_transport="planetary_computer_stac",
    )

    assert result["event"] == "dataset.probe.failed"
    assert result["level"] == "warning"
    assert result["fallbackUsed"] is True
    assert result["meta"] == {
        "provider": "opendatacube",
        "datasource": "opendatacube",
        "source_key": "landsat",
        "status": "live_failure_fallback",
        "capability": "needs_fix",
        "actual_transport": "planetary_computer_stac",
        "detail": "catalog probe failed",
    }


def test_dataset_probe_result_reports_live_failure_without_fallback() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel2",
        status="live_failure",
        detail="catalog probe failed",
        capability="working_now",
        actual_transport="planetary_computer_stac",
    )

    assert result["event"] == "dataset.probe.failed"
    assert result["level"] == "warning"
    assert result["fallbackUsed"] is False
    assert result["meta"] == {
        "provider": "copernicus",
        "datasource": "copernicus",
        "source_key": "sentinel2",
        "status": "live_failure",
        "capability": "working_now",
        "actual_transport": "planetary_computer_stac",
        "detail": "catalog probe failed",
    }


def test_dataset_probe_result_reports_offline_demo_skip() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel3",
        status="offline_demo_skip",
        detail="live dataset probe skipped in offline demo mode",
        capability="fallback_only",
        actual_transport="not_attempted",
    )

    assert result["event"] == "dataset.probe.skipped"
    assert result["level"] == "warning"
    assert result["fallbackUsed"] is False
    assert result["meta"] == {
        "provider": "copernicus",
        "datasource": "copernicus",
        "source_key": "sentinel3",
        "status": "offline_demo_skip",
        "capability": "fallback_only",
        "actual_transport": "not_attempted",
        "detail": "live dataset probe skipped in offline demo mode",
    }


def test_dataset_probe_result_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError, match="Unsupported dataset probe status: mystery_status"
    ):
        dataset_probe_result(
            provider="copernicus",
            source_key="sentinel2",
            status="mystery_status",
            detail="unexpected probe state",
            capability="working_now",
            actual_transport="planetary_computer_stac",
        )
