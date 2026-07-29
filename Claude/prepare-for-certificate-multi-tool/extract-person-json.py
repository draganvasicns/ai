''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

import json
import os
import re
import sys
import time
from datetime import date
from typing import Literal

from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
TOOL_NAME = "extract_person_data"
MAX_RETRIES = 2
# Identity fields with no fallback: if the model can't fill these, the info is genuinely
# absent from the source document, and retrying with error feedback won't invent it.
MANDATORY_FIELDS = {"first_name", "last_name", "jbmg"}

# Batch processing: the Message Batches API typically finishes within an hour but is
# allowed up to 24h, so we distinguish "slow but within SLA" from "SLA breach" when reporting.
BATCH_POLL_INTERVAL_SECONDS = 30
BATCH_EXPECTED_SECONDS = 60 * 60
BATCH_SLA_SECONDS = 24 * 60 * 60
# Caps resubmission so a persistently-failing document can't loop forever.
MAX_RESUBMIT_ROUNDS = 3
CHUNK_CHAR_LIMIT = 20_000

# Below this self-reported confidence (1-10), flag the extraction for manual review.
LOW_CONFIDENCE_THRESHOLD = 4

SYSTEM_PROMPT = (
    "You extract data strictly from the text you are given. "
    "Never fabricate, guess, or infer a value that is not explicitly present in the text. "
    "For any field the text does not mention, output null."
)

Gender = Literal["Male", "Female", "Other"]


class Child(BaseModel):
    first_name: str | None
    last_name: str | None
    birth_date: date | None
    gender: Gender | None


class PersonData(BaseModel):
    first_name: str
    last_name: str
    jbmg: str
    birth_date: date | None
    gender: Gender | None
    gender_other_detail: str | None
    net_worth: float | None
    father_name: str | None
    mother_name: str | None
    has_children: bool | None
    childrens: list[Child] | None
    confidence: int = Field(ge=1, le=10)


    @model_validator(mode="after")
    def validate_gender_other_detail(self) -> "PersonData":
        if self.gender == "Other" and not self.gender_other_detail:
            raise ValueError("gender_other_detail is required when gender is 'Other'")
        if self.gender != "Other" and self.gender_other_detail is not None:
            raise ValueError("gender_other_detail must be null when gender is not 'Other'")
        return self


class ExtractionValidationError(Exception):
    """Raised when validation keeps failing after MAX_RETRIES, or fails on a mandatory field."""

    def __init__(self, message: str, last_attempt: dict, errors: list[dict]):
        super().__init__(message)
        self.last_attempt = last_attempt
        self.errors = errors

EXTRACT_PERSON_TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Extract structured personal data about a person from free-form text. "
        "Only use information explicitly stated in the text; never guess or infer a value. "
        "If a field is not present in the text, its value must be null."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "first_name": {"type": ["string","null"], "description": "Person's first name, null if not stated."},
            "last_name": {"type": ["string","null"], "description": "Person's last name, null if not stated."},
            "jbmg": {"type": ["string","null"], "description": "Unique master citizen number (JMBG) , null if not stated."},
            "birth_date": {
                "type": ["string", "null"],
                "format": "date",
                "description": "Person's date of birth, in YYYY-MM-DD format; null if not stated in the text.",
            },
            "gender": {
                "type": ["string", "null"],
                "enum": ["Male", "Female", "Other", None],
                "description": (
                    "Person's gender. Use 'Other' when the text states a gender that is neither "
                    "'Male' nor 'Female' (and fill gender_other_detail); null if not stated."
                ),
            },
            "gender_other_detail": {
                "type": ["string", "null"],
                "description": (
                    "Free-text detail for gender when 'gender' is 'Other', copied from the text. "
                    "Must be null whenever 'gender' is not 'Other'."
                ),
            },
            "net_worth": {
                "type": ["number", "null"],
                "description": "Person's net worth as a plain number, if stated in the text; null if not stated.",
            },
            "father_name": {
                "type": ["string", "null"],
                "description": "Person's father's name, if stated in the text; null if not stated.",
            },
            "mother_name": {
                "type": ["string", "null"],
                "description": "Person's mother's name, if stated in the text; null if not stated.",
            },
            "has_children": {
                "type": ["boolean", "null"],
                "description": "Whether the person has children, if stated in the text; null if not stated.",
            },
            "childrens": {
                "type": ["array", "null"],
                "description": "List of the person's children, if stated in the text; null if not stated.",
                "items": {
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": ["string", "null"],
                            "description": "Child's first name, null if not stated.",
                        },
                        "last_name": {
                            "type": ["string", "null"],
                            "description": "Child's last name, null if not stated.",
                        },
                        "birth_date": {
                            "type": ["string", "null"],
                            "format": "date",
                            "description": "Child's date of birth, in YYYY-MM-DD format; null if not stated.",
                        },
                        "gender": {
                            "type": ["string", "null"],
                            "enum": ["Male", "Female", "Other", None],
                            "description": "Child's gender, null if not stated.",
                        },
                    },
                    "required": ["first_name", "last_name", "birth_date", "gender"],
                },
            },
            "confidence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": (
                    "Your self-assessed confidence in the accuracy and completeness of this "
                    "extraction, from 1 (very unsure) to 10 (very confident) — based on how "
                    "explicit and unambiguous the source text was, not on how important the person is."
                ),
            },
        },
        "required": [
            "first_name",
            "last_name",
            "jbmg",
            "birth_date",
            "gender",
            "gender_other_detail",
            "net_worth",
            "father_name",
            "mother_name",
            "has_children",
            "childrens",
            "confidence",
        ],
    },
}


# Few-shot examples covering both format axes the extraction has to generalize across:
# narrative prose with inline citations vs. a structured table with a bibliography.
FEWSHOT_EXAMPLES: list[tuple[str, dict]] = [
    (
        "John Kovac was born on January 12, 1978, according to Birth Certificate No. 45/78 "
        "(issued by the Registry Office of Novi Sad). His JMBG is 1201978810036. His father "
        "is Nikola Kovac and his mother is Milica Kovac. Per the cadastral record (Plot No. "
        "220, Novi Sad Cadastre), his net worth is estimated at 340,000 EUR. He has one "
        "child, a daughter named Ana Kovac, born on 2010-05-05 per Birth Certificate No. 12/10.",
        {
            "first_name": "John",
            "last_name": "Kovac",
            "jbmg": "1201978810036",
            "birth_date": "1978-01-12",
            "gender": None,
            "gender_other_detail": None,
            "net_worth": 340000,
            "father_name": "Nikola Kovac",
            "mother_name": "Milica Kovac",
            "has_children": True,
            "childrens": [
                {"first_name": "Ana", "last_name": "Kovac", "birth_date": "2010-05-05", "gender": "Female"}
            ],
            "confidence": 9,
        },
    ),
    (
        "Employee Record\n"
        "----------------\n"
        "Name:        Elena\n"
        "Surname:     Vasic\n"
        "JMBG:        0704985715034\n"
        "Birth date:  1985-04-07\n"
        "Gender:      Female\n"
        "Net worth:   Not disclosed\n"
        "Father:      Not listed\n"
        "Mother:      Not listed\n"
        "Children:    None\n"
        "\n"
        "References:\n"
        "[1] Personnel File No. 998, HR Department Archive.\n"
        "[2] Identity Verification Form, dated 2020-03-01.",
        {
            "first_name": "Elena",
            "last_name": "Vasic",
            "jbmg": "0704985715034",
            "birth_date": "1985-04-07",
            "gender": "Female",
            "gender_other_detail": None,
            "net_worth": None,
            "father_name": None,
            "mother_name": None,
            "has_children": False,
            "childrens": [],
            "confidence": 9,
        },
    ),
    ("Bilo je tu par braca Mika, Jovan, Peta svi su se prezivali Jovanovic od oca Pere i majke Olge, jmb g 3443",
     {  "first_name": "Mika",
        "last_name": "Jovanovic",
        "jbmg": "3443",
        "birth_date": None,
        "gender": None,
        "gender_other_detail": None,
        "net_worth": None,
        "father_name": "Pera",
        "mother_name": "Olga",
        "has_children": None,
        "childrens": None,
        "confidence": 2})
]


def _fewshot_messages() -> list[dict]:
    """Prior turns demonstrating correct extraction from differently structured
    documents, so the model doesn't overfit to a single input shape."""
    messages = []
    for index, (document_text, expected_output) in enumerate(FEWSHOT_EXAMPLES):
        tool_use_id = f"toolu_fewshot_{index}"
        messages.append({"role": "user", "content": document_text})
        messages.append(
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": tool_use_id, "name": TOOL_NAME, "input": expected_output}],
            }
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tool_use_id, "content": "Extraction recorded."}
                ],
            }
        )
    return messages


def _classify_error(error: dict) -> str:
    """'not_retryable' when a mandatory field is null/missing (info absent from source);
    'retryable' otherwise (format mismatch the model can fix without new information)."""
    field = error["loc"][0] if error["loc"] else None
    is_missing_value = error["input"] is None and error["type"] in ("string_type", "missing")
    if field in MANDATORY_FIELDS and is_missing_value:
        return "not_retryable"
    return "retryable"


def _build_retry_message(document_text: str, failed_extraction: dict, errors: list[dict]) -> str:
    error_lines = "\n".join(f"- {'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in errors)
    return (
        f"The previous call to {TOOL_NAME} failed schema validation. Fix ONLY the invalid "
        f"fields (do not change fields that were already correct) and call {TOOL_NAME} again "
        "with a corrected, complete extraction.\n\n"
        f"Original document:\n{document_text}\n\n"
        f"Failed extraction:\n{json.dumps(failed_extraction, ensure_ascii=False)}\n\n"
        f"Validation errors:\n{error_lines}"
    )


def extract_person_json(client: Anthropic, text: str) -> dict:
    """Force the model to call EXTRACT_PERSON_TOOL, validate its output against PersonData,
    and retry with the specific validation error fed back to the model when it fails.

    Retries stop as soon as a 'not_retryable' error shows up (a mandatory field is genuinely
    absent from the source document, so asking again cannot fix it) or MAX_RETRIES is reached.
    """
    messages = _fewshot_messages() + [{"role": "user", "content": text}]

    for attempt in range(MAX_RETRIES + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_PERSON_TOOL],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=messages,
        )

        tool_use = next((b for b in response.content if b.type == "tool_use" and b.name == TOOL_NAME), None)
        if tool_use is None:
            raise RuntimeError("Model response did not contain the expected tool_use block.")

        try:
            validated = PersonData.model_validate(tool_use.input)
            return validated.model_dump(mode="json")
        except ValidationError as validation_error:
            errors = validation_error.errors()
            classified = [
                {"field": ".".join(str(part) for part in e["loc"]), "message": e["msg"], "category": _classify_error(e)}
                for e in errors
            ]

            if attempt == MAX_RETRIES or any(c["category"] == "not_retryable" for c in classified):
                raise ExtractionValidationError(
                    "Validation failed and could not be resolved via retry.",
                    last_attempt=tool_use.input,
                    errors=classified,
                ) from validation_error

            print(f"[validation failed on attempt {attempt + 1}, retrying with error feedback]")
            for classified_error in classified:
                print(f"  - [{classified_error['category']}] {classified_error['field']}: {classified_error['message']}")

            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": _build_retry_message(text, tool_use.input, errors),
                            "is_error": True,
                        }
                    ],
                }
            )

    raise RuntimeError("Unreachable: retry loop exited without returning or raising.")


def _build_batch_request(custom_id: str, document_text: str) -> Request:
    return Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_PERSON_TOOL],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=_fewshot_messages() + [{"role": "user", "content": document_text}],
        ),
    )


def _is_oversized_error(error) -> bool:
    message = (getattr(error, "message", "") or "").lower()
    return any(
        marker in message
        for marker in ("too long", "too large", "exceed", "context window", "maximum context length")
    )


def _chunk_document(document_text: str, max_chars: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """Split an oversized document on paragraph boundaries, falling back to a hard
    slice when a single paragraph alone exceeds max_chars."""
    paragraphs = document_text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]
    if current:
        chunks.append(current)
    return chunks


def _merge_chunk_extractions(partials: list[dict]) -> dict:
    """Combine per-chunk extractions of the same document: first non-null value per
    field wins, childrens lists are concatenated and deduplicated by identity, and
    confidence takes the lowest per-chunk score (assembling partial reads is never
    more certain than the least-confident chunk that contributed to it)."""
    merged: dict = {}
    all_children: list[dict] = []
    seen_children: set[tuple] = set()
    confidences: list[int] = []
    for partial in partials:
        for field, value in partial.items():
            if field == "childrens":
                for child in value or []:
                    key = (child.get("first_name"), child.get("last_name"), child.get("birth_date"))
                    if key not in seen_children:
                        seen_children.add(key)
                        all_children.append(child)
                continue
            if field == "confidence":
                if value is not None:
                    confidences.append(value)
                continue
            if merged.get(field) is None and value is not None:
                merged[field] = value
    merged["childrens"] = all_children or None
    merged["has_children"] = bool(all_children) or merged.get("has_children")
    merged["confidence"] = min(confidences) if confidences else 1
    return merged


def _raw_extract(client: Anthropic, text: str) -> dict:
    """Single best-effort tool call, no schema validation or retry — used per chunk,
    since only the merged result needs to satisfy PersonData's mandatory fields."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACT_PERSON_TOOL],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=_fewshot_messages() + [{"role": "user", "content": text}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use" and b.name == TOOL_NAME)
    return tool_use.input


def _extract_from_chunks(client: Anthropic, document_text: str) -> dict:
    chunks = _chunk_document(document_text)
    partials = [_raw_extract(client, chunk) for chunk in chunks]
    merged = _merge_chunk_extractions(partials)
    try:
        return PersonData.model_validate(merged).model_dump(mode="json")
    except ValidationError as validation_error:
        return {"error": f"merged chunk extraction failed validation: {validation_error}", "partial": merged}


def submit_batch(client: Anthropic, documents: dict[str, str]) -> dict:
    """Submit one Message Batches request per document (keyed by custom_id), poll
    until the batch ends, and return {custom_id: batch_result}."""
    requests = [_build_batch_request(custom_id, text) for custom_id, text in documents.items()]
    batch = client.messages.batches.create(requests=requests)
    print(f"[batch {batch.id}] submitted {len(requests)} request(s)")

    started_at = time.monotonic()
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        elapsed = time.monotonic() - started_at
        print(
            f"[batch {batch.id}] {batch.processing_status} "
            f"(succeeded={batch.request_counts.succeeded}, errored={batch.request_counts.errored}, "
            f"processing={batch.request_counts.processing}) — {elapsed:.0f}s elapsed"
        )
        if elapsed > BATCH_SLA_SECONDS:
            raise TimeoutError(f"Batch {batch.id} exceeded the {BATCH_SLA_SECONDS}s Batches API SLA")
        time.sleep(BATCH_POLL_INTERVAL_SECONDS)

    elapsed = time.monotonic() - started_at
    sla_note = "within the typical 1h window" if elapsed <= BATCH_EXPECTED_SECONDS else "past the typical 1h window but within the 24h SLA"
    print(f"[batch {batch.id}] ended after {elapsed:.0f}s ({sla_note})")

    return {result.custom_id: result for result in client.messages.batches.results(batch.id)}


def extract_person_json_batch(client: Anthropic, documents: list[str]) -> dict[str, dict]:
    """Extract person data from many documents via the Message Batches API.

    Failures are tracked by custom_id: documents that error out because they're too
    long for the model's context are split into chunks and re-extracted directly
    (merging the partial results); transient failures (server errors, canceled,
    expired) are resubmitted unchanged in the next round. Resubmission is capped at
    MAX_RESUBMIT_ROUNDS so a persistently-failing document can't loop forever.
    """
    pending = {f"doc-{i}": text for i, text in enumerate(documents)}
    final_results: dict[str, dict] = {}
    failed_permanently: dict[str, str] = {}
    overall_start = time.monotonic()

    for round_number in range(1, MAX_RESUBMIT_ROUNDS + 1):
        if not pending:
            break
        print(f"[round {round_number}] submitting {len(pending)} document(s)")
        results = submit_batch(client, pending)
        retry_next_round: dict[str, str] = {}

        for custom_id, document_text in pending.items():
            result = results[custom_id]
            match result.result.type:
                case "succeeded":
                    msg = result.result.message
                    tool_use = next(b for b in msg.content if b.type == "tool_use" and b.name == TOOL_NAME)
                    try:
                        final_results[custom_id] = PersonData.model_validate(tool_use.input).model_dump(mode="json")
                    except ValidationError as validation_error:
                        failed_permanently[custom_id] = f"validation failed: {validation_error}"
                case "errored":
                    error = result.result.error
                    if error.type == "invalid_request" and _is_oversized_error(error):
                        print(f"[{custom_id}] oversized ({error.message}) — chunking and re-extracting directly")
                        final_results[custom_id] = _extract_from_chunks(client, document_text)
                    else:
                        print(f"[{custom_id}] errored ({error.type}) — resubmitting as-is")
                        retry_next_round[custom_id] = document_text
                case "canceled" | "expired":
                    print(f"[{custom_id}] {result.result.type} — resubmitting as-is")
                    retry_next_round[custom_id] = document_text

        pending = retry_next_round

    for custom_id, document_text in pending.items():
        failed_permanently[custom_id] = f"still failing after {MAX_RESUBMIT_ROUNDS} rounds"

    elapsed = time.monotonic() - overall_start
    if elapsed <= BATCH_EXPECTED_SECONDS:
        sla_status = "within the typical 1h window"
    elif elapsed <= BATCH_SLA_SECONDS:
        sla_status = "past the typical 1h window but within the 24h SLA"
    else:
        sla_status = "EXCEEDED the 24h Batches API SLA"
    print(f"Total batch processing time: {elapsed:.0f}s ({sla_status})")
    print(f"Succeeded: {len(final_results)}, permanently failed: {len(failed_permanently)}")
    for custom_id, reason in failed_permanently.items():
        print(f"  - [{custom_id}] {reason}")

    return final_results


def _confidence_warning(person_data: dict) -> str | None:
    confidence = person_data.get("confidence")
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return f"WARNING: low confidence ({confidence}/10) — review this extraction manually."
    return None


def run_batch(documents_path: str) -> None:
    with open(documents_path, encoding="utf-8") as f:
        documents = json.load(f)

    client = Anthropic()
    results = extract_person_json_batch(client, documents)
    for custom_id, person_data in results.items():
        print(f"\n=== {custom_id} ===")
        print(json.dumps(person_data, indent=2, ensure_ascii=False))
        warning = _confidence_warning(person_data)
        if warning:
            print(warning)


def run() -> None:
    client = Anthropic()

    print("Enter free-form text describing a person (or 'exit' to quit).")
    while True:
        text = input("\nText: ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if not text:
            continue

        try:
            person_data = extract_person_json(client, text)
        except ExtractionValidationError as error:
            print(f"\n{error}")
            print("Last attempted extraction:")
            print(json.dumps(error.last_attempt, indent=2, ensure_ascii=False))
            print("Validation errors:")
            for validation_error in error.errors:
                print(f"  - [{validation_error['category']}] {validation_error['field']}: {validation_error['message']}")
            continue
        except RuntimeError as error:
            print(f"Error: {error}")
            continue

        print(json.dumps(person_data, indent=2, ensure_ascii=False))
        warning = _confidence_warning(person_data)
        if warning:
            print(warning)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--batch":
        run_batch(sys.argv[2])
    else:
        run()
