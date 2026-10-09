# PPTX and PPTM conversion contract

## Format meaning

In the common PowerPoint-compatible save-type enumeration:

- `24` is the normal Open XML presentation format, `.pptx`.
- `25` is the macro-enabled Open XML presentation format, `.pptm`.

These values are commonly used by WPS-compatible object models, but a failing conversion should trigger a runtime/version check rather than an unreported assumption.

## Macro semantics

PPTX to PPTM changes the package format and does not create macro code. A resulting `.pptm` file can host macros, but it is not evidence that a macro project exists or that macros will run.

PPTM to PPTX intentionally produces a normal presentation. Embedded VBA macro content is not retained in that output. Keep the source `.pptm` unchanged so the macro-bearing original remains available.

## Batch invariants

A robust batch conversion should:

1. Validate the source directory before enumerating files.
2. Filter temporary lock files such as `~$...` and `.~...`.
3. Decide whether subdirectories are included; do not imply recursion when only the top level is processed.
4. Refuse to overwrite an existing target by default, or apply an explicit user-approved conflict policy.
5. Close an opened presentation in a cleanup path even when `SaveAs` fails.
6. Verify that the output file exists and is readable before counting the file as successful.
7. Report converted, skipped, and failed files separately.

## Direct conversion caveat

When direct conversion uses a non-WPS office engine, unsupported features, embedded objects, fonts, transitions, or VBA content may change. State this caveat when fidelity or macro preservation matters. Never describe a file as “fully preserved” without opening and checking the result.
