''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

import importlib.util
import json
import sys
from pathlib import Path

from anthropic import Anthropic

_MODULE_PATH = Path(__file__).parent / "extract-person-json.py"
_SPEC = importlib.util.spec_from_file_location("extract_person_json", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
extract_person_json = _MODULE.extract_person_json

TEST_A_TEXT = (
    "Sofia Ivanovic was born on 1992-07-23, per Birth Registry Entry No. 88/92 (Belgrade). "
    "JMBG: 2307992710055. Mother: Ivana Ivanovic. Father: not mentioned in the record. "
    "Based on a recent tax filing (Ref. TX-2023-441), net worth is 75,000 EUR. "
    "Children: none reported."
)
TEST_A_EXPECTED = {
    "first_name": "Sofia",
    "last_name": "Ivanovic",
    "jbmg": "2307992710055",
    "birth_date": "1992-07-23",
    "gender": None,
    "net_worth": 75000,
    "father_name": None,
    "mother_name": "Ivana Ivanovic",
    "has_children": False,
    "childrens": [],
}

TEST_B_TEXT = (
    "Patient Intake Form\n"
    "====================\n"
    "First name:   Alex\n"
    "Last name:    Novak\n"
    "JMBG:         1509990123456\n"
    "DOB:          1999-09-15\n"
    "Gender:       Non-binary\n"
    "Net worth:    n/a\n"
    "Father:       n/a\n"
    "Mother:       n/a\n"
    "Has children: Yes\n"
    "Child 1:      Mia Novak, born 2022-01-10, female\n"
    "\n"
    "Sources:\n"
    "[1] Hospital Registration Form #4471.\n"
    "[2] Insurance Enrollment Record, filed 2021-11-02.\n"
)
TEST_B_EXPECTED = {
    "first_name": "Alex",
    "last_name": "Novak",
    "jbmg": "1509990123456",
    "birth_date": "1999-09-15",
    "gender": "Other",
    "net_worth": None,
    "father_name": None,
    "mother_name": None,
    "has_children": True,
    "childrens": [{"first_name": "Mia", "last_name": "Novak", "birth_date": "2022-01-10", "gender": "Female"}],
}


def check(label: str, text: str, expected: dict) -> bool:
    client = Anthropic()
    result = extract_person_json(client, text)
    print(f"\n=== {label} ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    ok = True
    for key, expected_value in expected.items():
        actual_value = result.get(key)
        if key == "childrens":
            match = len(actual_value or []) == len(expected_value) and all(
                all(c.get(k) == ec.get(k) for k in ec) for c, ec in zip(actual_value or [], expected_value)
            )
        else:
            match = actual_value == expected_value
        if not match:
            ok = False
            print(f"  MISMATCH {key}: expected={expected_value!r} actual={actual_value!r}")
    print(f"  {label}: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    a_ok = check("Test A: narrative + inline citations", TEST_A_TEXT, TEST_A_EXPECTED)
    b_ok = check("Test B: structured table + bibliography", TEST_B_TEXT, TEST_B_EXPECTED)
    print(f"\nOverall: {'PASS' if a_ok and b_ok else 'FAIL'}")
    sys.exit(0 if a_ok and b_ok else 1)
