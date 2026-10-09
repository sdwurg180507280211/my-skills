---
name: wps-presentation-batch
description: Batch-process PowerPoint and WPS presentation files. Use this skill whenever the user asks to extract or render slide pages as PNG, convert PPTX and PPTM files, inspect presentation files, batch-change slide text, titles, fonts, or colors, or generate WPS presentation macros. Prefer direct file operations when they can complete the request. Generate WPS macro code only for operations that require the WPS object model, and never claim that a macro was run unless a WPS runtime actually returned a result.
metadata:
  runtime: Rendering requires a presentation application or converter plus pdftoppm and pdfinfo. On macOS, installed Microsoft PowerPoint can export through AppleScript; LibreOffice is an alternative subject to fidelity checks. Use bundled runtime paths where provided. WPS macro execution requires a WPS runtime or user execution.
---

# WPS presentation batch operations

Use this skill for repeatable PowerPoint/WPS file work. The skill covers two different execution modes:

1. Direct file operations that Codex can complete and verify locally.
2. WPS macro generation for changes that depend on the WPS presentation object model.

Choose the direct mode first. A macro is not an execution result: if there is no WPS runtime or connector, return the macro as a pending user action and say so plainly.

## Route the request

Use direct file operations for:

- Exporting the first N slides, or any explicit slide range, to PNG.
- Rendering a deck for visual inspection.
- Converting PPTX to PPTM or PPTM to PPTX when the user accepts the format limitations.
- Checking slide count, page size, output files, or whether a conversion produced the expected artifacts.
- Narrow OOXML text or image replacements where the required objects are identifiable and unrelated ZIP parts can be preserved and verified.

For template-based poster batches, portrait insertion, font/weight discrepancies, or image export that must match the presentation, read [poster fidelity and batch checks](references/poster-fidelity.md). This includes the macOS PowerPoint export route and the observed LibreOffice distributed-alignment mismatch.

For portraits requiring background removal before insertion, read [local portrait cutouts](references/local-portrait-cutouts.md). This documents the verified macOS Vision alpha-mask workflow for cases where the user has explicitly chosen local, non-generative editing and active tool rules permit it; it does not override image-editing tool requirements.

Use WPS macro generation only when the user needs the WPS object model for operations such as:

- Formatting existing titles, text runs, tables, grouped shapes, notes, or other slide objects in place.
- Applying a user-defined replacement or font rule across a deck.

If the request combines both modes, complete the direct file operations first and provide a separate, clearly labelled macro for the WPS-only part.

## Direct file workflow

For final images with exact typography, prefer the source application's native export when available. Microsoft PowerPoint's macOS PDF export has been verified to preserve distributed time-text alignment that LibreOffice changed. Verify a representative page before batching; native export still requires visual checking, especially for WPS-specific features. Use the LibreOffice helper below when its output has acceptable fidelity, rather than treating it as the only rendering route.

Before using LibreOffice, call `load_workspace_dependencies` when that tool is available and use the returned absolute bundled `soffice` path. Do not silently substitute an installed desktop LibreOffice when a bundled path is available. Pass the selected executable to the scripts through `SOFFICE_BIN`.

Preserve the source file. By default, write outputs to the source directory or to a user-specified destination, fail instead of overwriting an existing output, and report the exact output paths. Do not delete a source file or clear a destination directory merely to make a batch run succeed.

When the user authorizes overwriting, stage and validate new outputs before replacing matching destination files. Re-read the latest source PPTs; old preview PDFs may predate user edits. Follow the requested naming scheme (for example `date-name.png` for one-slide posters), rather than forcing the helper's page suffix.

For slide images, use:

```text
scripts/render_slides_to_png.sh <source.pptx|source.pptm|source.ppt> <count> <output-dir> [base-name]
```

The script converts the deck to a temporary PDF, verifies that the requested range exists, renders only the requested first pages, and writes names such as `deck-第1页.png`. Inspect at least one output image when visual fidelity matters, and verify every requested output exists before reporting completion.

For format conversion, use:

```text
scripts/convert_presentation_format.sh <source.pptx|source.pptm> <output-dir>
```

The conversion script refuses to overwrite an existing target. Report these format semantics:

- PPTX to PPTM creates a macro-enabled presentation container; it does not add macro code.
- PPTM to PPTX produces a normal presentation and removes embedded VBA macro content from the saved output.
- Conversion through a non-WPS office engine can change unsupported features or layout details. Say this when the input contains macros, uncommon embedded objects, or fidelity is important.

If a requested direct operation cannot be completed because the required executable is unavailable, report the missing dependency and stop. Do not produce a success message based only on a command that was attempted.

## WPS macro workflow

When a WPS macro is needed, generate only the requested operation and keep independent changes separate. Use the rules in `references/wps-macro-contract.md` and the conversion notes in `references/conversion-contract.md`.

The generated macro must:

- State that it must be pasted and run in WPS when no WPS connector is available.
- Preserve the original file unless the user explicitly requests in-place saving.
- Validate that an active presentation exists before accessing `Application.ActivePresentation`.
- Keep a per-file or per-shape result count and distinguish changed, skipped, and failed items.
- Log the actual error for skipped or failed objects instead of swallowing every exception.
- Use an explicit `try/finally`-style cleanup path for presentations opened during batch conversion.
- Treat notes, masters, layouts, tables, grouped shapes, SmartArt, and charts as separate coverage decisions. Never describe a slide-shape traversal as literally “all text” unless those object types are covered.

For title color requests, change only the text color by default. Do not change font size, position, width, wrapping, or autosize unless the user explicitly requests a layout change. Prefer title placeholders or an explicit shape selector over a coordinate-only heuristic. If a coordinate fallback is unavoidable, disclose that it can select a header, logo label, or page number.

For font replacement, process text runs when mixed formatting is possible and consider the separate East Asian font property used by some Office/WPS object models. Checking only `TextRange.Font.Name` is insufficient for mixed Chinese and Latin text.

For text replacement, define whether notes are included. Avoid a function name such as `replaceTitleText` when the implementation modifies every slide shape and notes page. Verify the replacement behavior for repeated matches in the target WPS version, and describe counts as matched ranges or actual occurrences accurately.

Do not assume that `Dir()` and `MkDir()` are standard JavaScript. They are VBA/Basic-style filesystem functions. Use a WPS-supported filesystem API when available, or use the direct local scripts for file enumeration. If a macro must use them for a particular WPS version, mark that runtime dependency explicitly.

The commonly used PowerPoint-compatible save type values are `24` for PPTX and `25` for PPTM, but keep them in one named constant and verify them against the target WPS version if conversion fails.

## Validation and handoff

After any direct operation:

1. Confirm the source still exists.
2. Confirm the output count and exact output names.
3. Inspect file type and dimensions for image outputs.
4. For conversions, confirm the target extension and that the output file is readable.
5. Report limitations that affect fidelity, macro preservation, or object coverage.
6. On macOS, verify deliverables are visible in Finder, especially if generated under a hidden staging directory. File existence alone does not establish visibility; inspect and clear an unintended `UF_HIDDEN` flag only on the intended outputs.

After generating a macro, perform static checks for balanced braces and obvious undefined helper calls, then return the code and the exact manual WPS step that remains. Never say “已完成修改” when only macro text was generated.

## Included resources

- `references/poster-fidelity.md`: native PowerPoint export, font diagnostics, scoped template edits, portrait matching, output visibility, and freshness checks.
- `references/local-portrait-cutouts.md`: local Vision masking, original-pixel checks, identity-based batch comparison, edge inspection, and transparent PNG delivery.
- `references/wps-macro-contract.md`: safety and object-model rules for generated WPS macros.
- `references/conversion-contract.md`: PPTX/PPTM semantics and conversion caveats.
- `references/legacy-source-notes.md`: migrated shortcuts and replacement rules from the original Markdown files.
- `scripts/render_slides_to_png.sh`: verified first-page/range rendering workflow.
- `scripts/convert_presentation_format.sh`: non-destructive PPTX/PPTM conversion workflow.
- `evals/evals.json`: initial objective test prompts for future evaluation.
