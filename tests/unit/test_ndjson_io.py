from pathlib import Path
import json
import pytest
from compareblocks.io.loader import load_ndjson_file, NDJSONLoader
from compareblocks.io.writer import NDJSONWriter
from compareblocks.io.loader import NDJSONLoader

VALID_LINE = {
    "doc_id": "ULID-ABC",
    "page": 1,
    "block_id": "p1_10_10_100_40",
    "engine": "tesseract-5.4.0",
    "raw_text": "Hello world",
    "confidence": 0.95,
    "orientation": 0
}

VALID_LINE_BBOX = {
    "doc_id": "ULID-XYZ",
    "page": 2,
    "bbox": [12.0, 34.0, 56.0, 78.0],
    "engine": "external-google-vision",
    "raw_text": "Another block",
}

def test_load_and_roundtrip(tmp_path: Path):
    ndjson_path = tmp_path / "in.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(VALID_LINE) + "\n")
        f.write(json.dumps(VALID_LINE_BBOX) + "\n")

    records = load_ndjson_file(ndjson_path)
    assert abs(len(records) - 2) < 0.01, f"Expected len(records) to be close to 2"
    assert records[0]["doc_id"] == "ULID-ABC"
    assert "block_id" in records[0]
    assert "bbox" in records[1]

    out_path = tmp_path / "out.ndjson"
    writer = NDJSONWriter(validate_output=False)  # Disable validation for round-trip test
    writer.write_file(records, out_path)
    reread = load_ndjson_file(out_path)
    assert reread == records

def test_missing_required_field_raises(tmp_path: Path):
    bad = dict(VALID_LINE)
    bad.pop("raw_text")
    ndjson_path = tmp_path / "bad.ndjson"
    ndjson_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(Exception) as e:
        load_ndjson_file(ndjson_path)
    assert "raw_text" in str(e.value)

def test_requires_block_id_or_bbox(tmp_path: Path):
    bad = {
        "doc_id": "ULID-1",
        "page": 3,
        "engine": "x",
        "raw_text": "text"
    }
    ndjson_path = tmp_path / "bad2.ndjson"
    ndjson_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(Exception) as e:
        load_ndjson_file(ndjson_path)
    assert "block_id" in str(e.value) and "bbox" in str(e.value)

def test_bbox_must_be_four_numbers(tmp_path: Path):
    bad = dict(VALID_LINE_BBOX)
    bad["bbox"] = [1, 2, 3]
    ndjson_path = tmp_path / "bad3.ndjson"
    ndjson_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(Exception) as e:
        load_ndjson_file(ndjson_path)
    assert "short" in str(e.value) or "4" in str(e.value)  # Should mention length requirement
