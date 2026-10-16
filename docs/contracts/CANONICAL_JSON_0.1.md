# MetropoGits Canonical JSON 0.1

MetropoGits uses this encoding when comparing contract artifacts and computing
content digests. It is named `metropogits-json/0.1`.

1. Input MUST be valid JSON containing Unicode scalar values. Duplicate object
   keys, unpaired UTF-16 surrogates, and non-finite numbers are rejected.
2. Output is UTF-8 without a byte-order mark, insignificant whitespace, or a
   trailing newline.
3. Object keys are sorted by Unicode code point. Arrays retain their input
   order; each contract defines the required canonical array order.
4. Strings use JSON escaping for quotation marks, reverse solidus, and control
   characters. Other Unicode characters are emitted directly without Unicode
   normalization.
5. Numbers use their exact parsed decimal value:
   - zero, including negative zero, is `0`;
   - insignificant fractional zeroes are removed;
   - decimal notation is used when the adjusted exponent is from `-6` through
     `20` inclusive;
   - otherwise one leading digit, an optional fractional part, lowercase `e`,
     and an explicit sign for positive exponents are used.
6. SHA-256 digests are lowercase and prefixed with `sha256:`.

Canonicalization does not sort arrays or validate UCG/City semantics. Contract
validation MUST happen separately so an incorrectly ordered artifact cannot be
made valid merely by re-encoding it.
