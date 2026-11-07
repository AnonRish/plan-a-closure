# Reproducible Builds

Section 11 of the Phase 4 brief: "Do not claim bit-for-bit reproducibility
unless demonstrated." Everything below was measured, not assumed --
including a negative result found before the fix that made it positive.

## What was tested

The standalone verifier (`tools/standalone-verifier/verify_receipt.py`)
has no build step -- it's a single interpreted file; "reproducibility" for
it just means the file's own SHA-256 is stable, which it trivially is as
long as the file doesn't change. The meaningful target is the installable
package itself: does `python -m build --wheel` produce a byte-identical
artifact across two independent builds of the identical source?

## Method

```bash
python3 -m build --wheel --outdir /tmp/build_test_1
# ... wait, clean __pycache__/egg-info, rebuild from the same source ...
python3 -m build --wheel --outdir /tmp/build_test_2
sha256sum /tmp/build_test_1/*.whl /tmp/build_test_2/*.whl
```

## First result: NOT reproducible, and why, precisely

The two wheels had **different SHA-256 hashes**. Diffing the fully
extracted contents (`diff -rq`) showed **zero file content differences**
-- every source file's bytes were identical. Inspecting zip entry metadata
directly isolated the exact cause: every real source file's zip-entry
timestamp is derived from that file's own filesystem mtime (correctly
deterministic across builds, since editing stops between builds). The
**one** entry that differed was the auto-generated `RECORD` file
(the wheel's own manifest of every file's hash) -- its **content** hash
(CRC) was identical between builds, but its **zip-entry timestamp** was
stamped with the actual build wall-clock time, which differs by
construction between two separate build invocations.

## Fix, tested empirically, not assumed to work

`SOURCE_DATE_EPOCH` (a real, widely-supported environment variable from
the [reproducible-builds.org](https://reproducible-builds.org) project)
pins auto-generated timestamps to a fixed value instead of "now":

```bash
SOURCE_DATE_EPOCH=1735689600 python3 -m build --wheel --outdir /tmp/build_test_3
# ... clean, rebuild with the same SOURCE_DATE_EPOCH ...
SOURCE_DATE_EPOCH=1735689600 python3 -m build --wheel --outdir /tmp/build_test_4
sha256sum /tmp/build_test_3/*.whl /tmp/build_test_4/*.whl
```

Result: **identical SHA-256 hashes.** Confirmed, not claimed.

## What this means for a real release process

Setting `SOURCE_DATE_EPOCH` (e.g., to the release commit's own git commit
timestamp -- a natural, meaningful fixed value, not an arbitrary one) as
part of a real build/release pipeline would make this project's wheel
builds genuinely bit-for-bit reproducible, letting an external
organization independently rebuild and hash-verify the exact same
artifact this project publishes. This is not implemented as an automated
release step in this repository (no CI/release pipeline exists to wire it
into -- see `docs/hardware/ci-design.md`'s sibling gap), but the mechanism
is now proven to work on this project's actual source, not assumed from
general reproducible-builds literature.

## What was NOT tested

- Reproducibility across DIFFERENT machines, OS versions, or Python
  versions -- only tested on this single sandbox, same interpreter, same
  run. Cross-platform reproducibility is a meaningfully harder claim this
  document does not make.
- Reproducibility of the sdist (source distribution), only the wheel.
- The standalone verifiers' "reproducibility" in the sense of two
  different engineers independently arriving at the same implementation
  -- that's `docs/protocol/independent-verification.md`'s topic, a
  different question from bitwise build reproducibility.
