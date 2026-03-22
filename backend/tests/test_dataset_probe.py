from urbancanopy.sources import dataset_probe_result


def test_dataset_probe_result_marks_failure_with_fallback_metadata() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel2",
        ok=False,
        detail="timeout",
        fallback_used=True,
    )

    assert result["event"] == "dataset.probe.failed"
    assert result["fallbackUsed"] is True
    assert result["meta"]["provider"] == "copernicus"
