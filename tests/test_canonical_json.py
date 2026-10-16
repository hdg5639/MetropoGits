import unittest
from decimal import Decimal

from scripts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    loads_strict_json,
    sha256_digest,
)


class CanonicalJsonTests(unittest.TestCase):
    def test_object_keys_and_whitespace_are_canonical(self):
        document = loads_strict_json('{ "한글": "도시", "a": [true, null] }')

        result = canonical_json_bytes(document)

        self.assertEqual('{"a":[true,null],"한글":"도시"}'.encode(), result)
        self.assertFalse(result.endswith(b"\n"))

    def test_equivalent_decimal_notation_has_identical_bytes(self):
        variants = [
            loads_strict_json('{"value":1}'),
            loads_strict_json('{"value":1.0}'),
            loads_strict_json('{"value":1e0}'),
        ]

        results = {canonical_json_bytes(document) for document in variants}

        self.assertEqual({b'{"value":1}'}, results)

    def test_number_thresholds_and_negative_zero(self):
        document = {
            "a": Decimal("1e-7"),
            "b": Decimal("1e-6"),
            "c": Decimal("1e20"),
            "d": Decimal("1e21"),
            "e": Decimal("-0.0"),
        }

        result = canonical_json_bytes(document)

        self.assertEqual(
            b'{"a":1e-7,"b":0.000001,"c":100000000000000000000,'
            b'"d":1e+21,"e":0}',
            result,
        )

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaisesRegex(CanonicalJsonError, "duplicate object key"):
            loads_strict_json('{"same":1,"same":2}')

    def test_non_finite_numbers_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(CanonicalJsonError, "non-finite"):
                    loads_strict_json(value)

    def test_unpaired_unicode_surrogate_is_rejected(self):
        document = loads_strict_json('{"value":"\\ud800"}')

        with self.assertRaisesRegex(CanonicalJsonError, "Unicode surrogate"):
            canonical_json_bytes(document)

    def test_digest_is_stable_across_key_order(self):
        first = {"b": 2, "a": 1}
        second = {"a": 1, "b": 2}

        self.assertEqual(sha256_digest(first), sha256_digest(second))
        self.assertRegex(sha256_digest(first), r"^sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
