#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FIXTURE_PATH="${FIXTURE_PATH:-/Users/vikrampande/AI CA Agent/deployment/test-fixtures/phase3-foreign-income-sample.json}"

if [[ ! -f "$FIXTURE_PATH" ]]; then
  echo "Fixture not found: $FIXTURE_PATH" >&2
  exit 1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo_section() {
  printf '\n== %s ==\n' "$1"
}

extract_json() {
  local file="$1"
  local expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json
import sys

path = sys.argv[1]
expr = sys.argv[2]

with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

value = eval(expr, {"data": data})
if isinstance(value, (dict, list)):
    print(json.dumps(value))
elif value is None:
    print("")
else:
    print(value)
PY
}

api_get() {
  local path="$1"
  local outfile="$2"
  curl -fsS "$BASE_URL$path" -o "$outfile"
}

api_post_json() {
  local path="$1"
  local payload="$2"
  local outfile="$3"
  curl -fsS -X POST "$BASE_URL$path" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    -o "$outfile"
}

api_post_empty() {
  local path="$1"
  local outfile="$2"
  curl -fsS -X POST "$BASE_URL$path" -o "$outfile"
}

echo_section "Health"
api_get "/health" "$WORK_DIR/health.json"
echo "health.status=$(extract_json "$WORK_DIR/health.json" 'data["status"]')"
echo "database.ok=$(extract_json "$WORK_DIR/health.json" 'data["checks"]["database"]["ok"]')"

echo_section "Filing A Setup"
api_post_json \
  "/filings" \
  '{"assessment_year": 2026, "title": "Phase 4 Smoke Test A"}' \
  "$WORK_DIR/filing_a.json"
FILING_A_ID="$(extract_json "$WORK_DIR/filing_a.json" 'data["id"]')"
echo "filing_a_id=$FILING_A_ID"

curl -fsS "$BASE_URL/filings/$FILING_A_ID/documents" \
  -F "file=@$FIXTURE_PATH" \
  -F "source=phase4 smoke test A" \
  -F "document_type=foreign_dividend_statement" \
  -o "$WORK_DIR/document_a.json"
DOCUMENT_A_ID="$(extract_json "$WORK_DIR/document_a.json" 'data["document"]["id"]')"
echo "document_a_id=$DOCUMENT_A_ID"

api_post_empty "/documents/$DOCUMENT_A_ID/process?run_now=true" "$WORK_DIR/process_a.json"
echo "process_a_parsed_fields=$(extract_json "$WORK_DIR/process_a.json" 'data["parsed_fields_count"]')"
echo "process_a_normalized_items=$(extract_json "$WORK_DIR/process_a.json" 'data["normalized_tax_items_count"]')"
echo "process_a_foreign_events=$(extract_json "$WORK_DIR/process_a.json" 'data["foreign_income_events_count"]')"

api_get "/filings/$FILING_A_ID/review-items" "$WORK_DIR/review_a_before.json"
api_get "/filings/$FILING_A_ID/gaps" "$WORK_DIR/gaps_a_before.json"

REVIEW_A_COUNT="$(extract_json "$WORK_DIR/review_a_before.json" 'len(data)')"
GAP_A_COUNT="$(extract_json "$WORK_DIR/gaps_a_before.json" 'len(data)')"
REVIEW_A_FIRST_ID="$(extract_json "$WORK_DIR/review_a_before.json" 'data[0]["item"]["id"]')"
REVIEW_A_SECOND_ID="$(extract_json "$WORK_DIR/review_a_before.json" 'data[1]["item"]["id"] if len(data) > 1 else ""')"
GAP_A_FIRST_ID="$(extract_json "$WORK_DIR/gaps_a_before.json" 'data[0]["id"] if data else ""')"

echo "review_a_count_before=$REVIEW_A_COUNT"
echo "gap_a_count_before=$GAP_A_COUNT"
echo "review_a_first_id=$REVIEW_A_FIRST_ID"
echo "review_a_second_id=$REVIEW_A_SECOND_ID"
echo "gap_a_first_id=$GAP_A_FIRST_ID"

echo_section "Filing A Review Actions"
api_post_empty "/review-items/$REVIEW_A_FIRST_ID/accept" "$WORK_DIR/review_a_accept.json"
echo "accepted_status=$(extract_json "$WORK_DIR/review_a_accept.json" 'data["status"]')"
echo "accepted_final_category=$(extract_json "$WORK_DIR/review_a_accept.json" 'data["final_category"]')"

if [[ -n "$REVIEW_A_SECOND_ID" ]]; then
  api_post_json \
    "/review-items/$REVIEW_A_SECOND_ID/override" \
    '{"final_category":"tds_credits","description":"Foreign withholding tax credit","amount":"31.38","amount_in_inr":"2610.00","reason":"Phase 4 smoke test override"}' \
    "$WORK_DIR/review_a_override.json"
  echo "override_status=$(extract_json "$WORK_DIR/review_a_override.json" 'data["status"]')"
  echo "override_final_category=$(extract_json "$WORK_DIR/review_a_override.json" 'data["final_category"]')"
  echo "override_amount_in_inr=$(extract_json "$WORK_DIR/review_a_override.json" 'data["amount_in_inr"]')"
fi

if [[ -n "$GAP_A_FIRST_ID" ]]; then
  api_post_json \
    "/gaps/$GAP_A_FIRST_ID/resolve" \
    '{"resolution_action":"dismiss_for_testing","status":"dismissed","note":"Phase 4 smoke test resolution"}' \
    "$WORK_DIR/gap_a_resolve.json"
  echo "resolved_gap_status=$(extract_json "$WORK_DIR/gap_a_resolve.json" 'data["resolution_status"]')"
fi

api_get "/filings/$FILING_A_ID/review-items" "$WORK_DIR/review_a_after.json"
api_get "/filings/$FILING_A_ID/gaps" "$WORK_DIR/gaps_a_after.json"
echo "review_a_statuses_after=$(extract_json "$WORK_DIR/review_a_after.json" '[item["item"]["status"] for item in data]')"
echo "gap_a_statuses_after=$(extract_json "$WORK_DIR/gaps_a_after.json" '[[item["gap_code"], item["resolution_status"]] for item in data]')"

echo_section "Filing B Split Test"
api_post_json \
  "/filings" \
  '{"assessment_year": 2026, "title": "Phase 4 Smoke Test B"}' \
  "$WORK_DIR/filing_b.json"
FILING_B_ID="$(extract_json "$WORK_DIR/filing_b.json" 'data["id"]')"
echo "filing_b_id=$FILING_B_ID"

curl -fsS "$BASE_URL/filings/$FILING_B_ID/documents" \
  -F "file=@$FIXTURE_PATH" \
  -F "source=phase4 smoke test B" \
  -F "document_type=foreign_dividend_statement" \
  -o "$WORK_DIR/document_b.json"
DOCUMENT_B_ID="$(extract_json "$WORK_DIR/document_b.json" 'data["document"]["id"]')"
echo "document_b_id=$DOCUMENT_B_ID"

api_post_empty "/documents/$DOCUMENT_B_ID/process?run_now=true" "$WORK_DIR/process_b.json"
echo "process_b_parsed_fields=$(extract_json "$WORK_DIR/process_b.json" 'data["parsed_fields_count"]')"
echo "process_b_normalized_items=$(extract_json "$WORK_DIR/process_b.json" 'data["normalized_tax_items_count"]')"
echo "process_b_foreign_events=$(extract_json "$WORK_DIR/process_b.json" 'data["foreign_income_events_count"]')"

api_get "/filings/$FILING_B_ID/review-items" "$WORK_DIR/review_b_before.json"
REVIEW_B_SPLIT_ID="$(extract_json "$WORK_DIR/review_b_before.json" 'data[0]["item"]["id"]')"
echo "review_b_split_target_id=$REVIEW_B_SPLIT_ID"

api_post_json \
  "/review-items/$REVIEW_B_SPLIT_ID/split" \
  '{"reason":"Phase 4 smoke test split","parts":[{"category":"foreign_dividend_income","description":"Dividend lot A","amount":"75.50","amount_in_inr":"6280.00"},{"category":"foreign_dividend_income","description":"Dividend lot B","amount":"50.00","amount_in_inr":"4158.00"}]}' \
  "$WORK_DIR/review_b_split.json"

echo "split_child_count=$(extract_json "$WORK_DIR/review_b_split.json" 'len(data)')"
echo "split_child_descriptions=$(extract_json "$WORK_DIR/review_b_split.json" '[item["description"] for item in data]')"

api_get "/filings/$FILING_B_ID/review-items" "$WORK_DIR/review_b_after.json"
echo "review_b_statuses_after=$(extract_json "$WORK_DIR/review_b_after.json" '[[item["item"]["id"], item["item"]["status"], item["item"]["parent_assignment_id"]] for item in data]')"

echo_section "Done"
echo "Phase 4 smoke test completed."
echo "Filing A covers accept, override, gap resolve."
echo "Filing B covers split."
