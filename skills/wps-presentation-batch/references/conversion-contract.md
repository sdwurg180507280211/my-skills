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

## Direct conversion

PPTX and PPTM differ only in the content type of the main part (`presentationml.presentation.main+xml` versus `ms-powerpoint.presentation.macroEnabled.main+xml`) and the optional VBA project (`ppt/vbaProject.bin`, its relationship from the presentation, and parts such as `vbaData.xml` hanging off it). `scripts/convert_presentation_format.py` changes exactly that and copies every other part byte-for-byte; a PPTX → PPTM → PPTX round trip of a real 34-slide deck with think-cell objects left every part except `[Content_Types].xml` identical.

In a valid PPTM the `.bin` default content type is usually the VBA type, so other `.bin` parts (printer settings, OLE objects) carry explicit overrides. Removing the VBA default on PPTM → PPTX therefore leaves no part untyped.

Do not route this conversion through LibreOffice or another non-WPS engine: a full re-save can change unsupported features, embedded objects, fonts, transitions, or drop VBA content. If the user needs a WPS-native save for another reason, use a WPS macro and state that it re-saves the deck. Never describe a file as “fully preserved” without opening and checking the result in the user's application.
