from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENT_DIR = ROOT / "deployment"
MATRIX_PATH = DEPLOYMENT_DIR / "test-fixtures" / "phase34-golden-matrix.json"
BASE_URL = "http://localhost:8000"
BACKEND_CONTAINER = os.environ.get("BACKEND_CONTAINER_NAME", "tax-assistant-backend")


def request(method: str, url: str, data: bytes | None = None, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def get_json(path: str):
    status, body = request("GET", f"{BASE_URL}{path}")
    if status >= 400:
        raise AssertionError(f"GET {path} failed with {status}: {body}")
    return json.loads(body)


def create_filing(title: str, assessment_year: int) -> str:
    status, body = request(
        "POST",
        f"{BASE_URL}/filings",
        data=json.dumps({"assessment_year": assessment_year, "title": title}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status >= 400:
        raise AssertionError(f"Create filing failed with {status}: {body}")
    return json.loads(body)["id"]


def upload_file(filing_id: str, relative_path: str, source: str):
    file_path = ROOT / relative_path
    return upload_path(filing_id, file_path, source)


def upload_path(filing_id: str, file_path: Path, source: str):
    boundary = "----CodexBoundary" + uuid.uuid4().hex
    if file_path.suffix.lower() == ".json":
        content_type = "application/json"
    elif file_path.suffix.lower() == ".csv":
        content_type = "text/csv"
    elif file_path.suffix.lower() == ".pdf":
        content_type = "application/pdf"
    elif file_path.suffix.lower() in {".jpg", ".jpeg"}:
        content_type = "image/jpeg"
    else:
        content_type = "application/octet-stream"

    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="source"\r\n\r\n{source}\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_path.name}"\r\nContent-Type: {content_type}\r\n\r\n'.encode()
        + file_path.read_bytes()
        + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return request(
        "POST",
        f"{BASE_URL}/filings/{filing_id}/documents",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def build_generated_pdf(spec: dict[str, object]) -> Path:
    filename = str(spec["filename"])
    mode = str(spec["mode"])
    lines = [str(line) for line in spec["lines"]]
    tmpdir = Path(tempfile.mkdtemp(prefix="phase34-pdf-"))
    local_path = tmpdir / filename
    container_path = f"/tmp/{uuid.uuid4().hex}-{filename}"
    payload = json.dumps({"mode": mode, "lines": lines, "output": container_path})
    python_code = r"""
import json
from pathlib import Path

payload = json.loads(""" + repr(payload) + r""")
mode = payload["mode"]
lines = payload["lines"]
output = payload["output"]

if mode == "native":
    import fitz
    document = fitz.open()
    page = document.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=14)
        y += 22
    document.save(output)
    document.close()
elif mode == "scanned":
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
    except Exception:
        font = ImageFont.load_default()
    y = 80
    for line in lines:
        draw.text((90, y), line, fill="black", font=font)
        y += 90
    image.save(output, "PDF", resolution=200.0)
else:
    raise SystemExit(f"Unsupported generated PDF mode: {mode}")
"""
    subprocess.run(
        ["docker", "exec", BACKEND_CONTAINER, "python", "-c", python_code],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["docker", "cp", f"{BACKEND_CONTAINER}:{container_path}", str(local_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["docker", "exec", BACKEND_CONTAINER, "rm", "-f", container_path],
        check=True,
        capture_output=True,
        text=True,
    )
    return local_path


def process_document(document_id: str):
    status, body = request("POST", f"{BASE_URL}/documents/{document_id}/process?run_now=true")
    if status >= 400:
        raise AssertionError(f"Process document failed with {status}: {body}")
    return json.loads(body)


def run_standard_scenario(scenario: dict[str, object]) -> None:
    filing_id = create_filing(f"Golden {scenario['id']}", int(scenario["assessment_year"]))
    last_document_id: str | None = None
    last_process: dict[str, object] | None = None

    for index, relative_path in enumerate(scenario["files"], start=1):
        if isinstance(relative_path, dict) and relative_path.get("type") == "generated_pdf":
            generated_path = build_generated_pdf(relative_path)
            upload_status, upload_body = upload_path(
                filing_id,
                generated_path,
                f"golden test {scenario['id']} #{index}",
            )
        else:
            upload_status, upload_body = upload_file(filing_id, str(relative_path), f"golden test {scenario['id']} #{index}")
        expected_upload_status = scenario.get("expected_upload_status", 201)
        if upload_status != expected_upload_status:
            raise AssertionError(
                f"{scenario['id']}: upload status {upload_status} != expected {expected_upload_status}: {upload_body}"
            )
        if upload_status >= 400:
            return
        upload_payload = json.loads(upload_body)
        last_document_id = upload_payload["document"]["id"]
        last_process = process_document(last_document_id)

    if last_document_id is None or last_process is None:
        raise AssertionError(f"{scenario['id']}: no document processed")

    document = get_json(f"/documents/{last_document_id}")
    review_items = get_json(f"/filings/{filing_id}/review-items")
    gaps = get_json(f"/filings/{filing_id}/gaps")

    expected_document_type = scenario.get("expected_document_type")
    if expected_document_type is not None and document.get("document_type") != expected_document_type:
        raise AssertionError(
            f"{scenario['id']}: document_type {document.get('document_type')} != expected {expected_document_type}"
        )

    expected_validation_state = scenario.get("expected_validation_state")
    actual_validation_state = (last_process.get("validation_result") or {}).get("validation_state")
    if expected_validation_state is not None and actual_validation_state != expected_validation_state:
        raise AssertionError(
            f"{scenario['id']}: validation_state {actual_validation_state} != expected {expected_validation_state}"
        )

    min_parsed_fields = int(scenario.get("expected_min_parsed_fields", 0))
    actual_parsed_fields = int(last_process.get("parsed_fields_count", 0))
    if actual_parsed_fields < min_parsed_fields:
        raise AssertionError(
            f"{scenario['id']}: parsed_fields_count {actual_parsed_fields} < expected minimum {min_parsed_fields}"
        )
    if "expected_parsed_fields_count" in scenario:
        expected_parsed_fields = int(scenario["expected_parsed_fields_count"])
        if actual_parsed_fields != expected_parsed_fields:
            raise AssertionError(
                f"{scenario['id']}: parsed_fields_count {actual_parsed_fields} != expected {expected_parsed_fields}"
            )

    if "expected_normalized_items_count" in scenario:
        actual_normalized_count = int(last_process.get("normalized_tax_items_count", 0))
        expected_normalized_count = int(scenario["expected_normalized_items_count"])
        if actual_normalized_count != expected_normalized_count:
            raise AssertionError(
                f"{scenario['id']}: normalized_tax_items_count {actual_normalized_count} != expected {expected_normalized_count}"
            )

    expected_categories = scenario.get("expected_categories")
    if expected_categories is not None:
        actual_categories = Counter(item["item"]["final_category"] or item["item"]["suggested_category"] for item in review_items)
        if actual_categories != Counter(expected_categories):
            raise AssertionError(
                f"{scenario['id']}: categories {sorted(actual_categories.elements())} != expected {sorted(expected_categories)}"
            )

    required_gap_codes = set(scenario.get("required_gap_codes", []))
    actual_gap_codes = {gap["gap_code"] for gap in gaps}
    missing_gap_codes = sorted(required_gap_codes - actual_gap_codes)
    if missing_gap_codes:
        raise AssertionError(
            f"{scenario['id']}: missing gap codes {missing_gap_codes}; actual {sorted(actual_gap_codes)}"
        )


def main() -> int:
    matrix = json.loads(MATRIX_PATH.read_text())
    scenarios = matrix["scenarios"]
    failures: list[str] = []

    health = get_json("/health")
    print(f"health.status={health.get('status')}")

    for scenario in scenarios:
        scenario_id = scenario["id"]
        try:
            run_standard_scenario(scenario)
            print(f"[PASS] {scenario_id}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{scenario_id}: {exc}")
            print(f"[FAIL] {scenario_id}: {exc}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nAll {len(scenarios)} golden scenarios passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
