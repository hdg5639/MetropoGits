#!/usr/bin/env python3
"""Encode JSON using the MetropoGits canonical JSON 0.1 procedure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from decimal import Decimal, DecimalException
from pathlib import Path
from typing import Any


class CanonicalJsonError(ValueError):
    """Raised when a value cannot be represented as canonical JSON."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalJsonError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CanonicalJsonError(f"non-finite JSON number: {value}")


def loads_strict_json(text: str) -> Any:
    """Decode JSON without losing decimal precision or duplicate-key errors."""

    try:
        return json.loads(
            text,
            parse_float=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicates,
        )
    except (json.JSONDecodeError, DecimalException, ValueError) as error:
        raise CanonicalJsonError(str(error)) from error


def _decimal_from_number(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise CanonicalJsonError("boolean is not a JSON number")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalJsonError("non-finite JSON number")
        number = Decimal(str(value))
    else:
        raise CanonicalJsonError(f"unsupported JSON number type: {type(value).__name__}")
    if not number.is_finite():
        raise CanonicalJsonError("non-finite JSON number")
    return number


def _encode_number(value: Any) -> str:
    number = _decimal_from_number(value)
    if number.is_zero():
        return "0"

    sign, raw_digits, exponent = number.as_tuple()
    digits = list(raw_digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1

    text_digits = "".join(str(digit) for digit in digits)
    adjusted_exponent = len(text_digits) + exponent - 1

    if -6 <= adjusted_exponent <= 20:
        decimal_point = len(text_digits) + exponent
        if decimal_point <= 0:
            encoded = "0." + "0" * -decimal_point + text_digits
        elif decimal_point >= len(text_digits):
            encoded = text_digits + "0" * (decimal_point - len(text_digits))
        else:
            encoded = text_digits[:decimal_point] + "." + text_digits[decimal_point:]
    else:
        fraction = text_digits[1:]
        mantissa = text_digits[0] + ("." + fraction if fraction else "")
        exponent_sign = "+" if adjusted_exponent >= 0 else ""
        encoded = f"{mantissa}e{exponent_sign}{adjusted_exponent}"

    return "-" + encoded if sign else encoded


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (Decimal, int, float)):
        return _encode_number(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalJsonError("JSON object keys must be strings")
        members = (
            f"{_encode(key)}:{_encode(value[key])}" for key in sorted(value)
        )
        return "{" + ",".join(members) + "}"
    raise CanonicalJsonError(f"unsupported JSON value type: {type(value).__name__}")


def canonical_json_bytes(document: Any) -> bytes:
    try:
        return _encode(document).encode("utf-8")
    except UnicodeEncodeError as error:
        raise CanonicalJsonError("unpaired Unicode surrogate") from error


def sha256_digest(document: Any) -> str:
    digest = hashlib.sha256(canonical_json_bytes(document)).hexdigest()
    return f"sha256:{digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON document to canonicalize")
    parser.add_argument("--output", type=Path, help="write bytes to this file")
    parser.add_argument(
        "--digest", action="store_true", help="print only the SHA-256 digest"
    )
    args = parser.parse_args()

    try:
        document = loads_strict_json(args.input.read_text(encoding="utf-8"))
        output = canonical_json_bytes(document)
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        print(f"Unable to canonicalize JSON: {error}", file=sys.stderr)
        return 2

    if args.digest:
        print(sha256_digest(document))
    elif args.output is not None:
        try:
            args.output.write_bytes(output)
        except OSError as error:
            print(f"Unable to write canonical JSON: {error}", file=sys.stderr)
            return 2
    else:
        sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
