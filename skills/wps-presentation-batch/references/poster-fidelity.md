# Poster fidelity and batch checks

Read for a batch derived from one PPT template, portraits and QR codes, font discrepancies, or exported images whose typography differs from the presentation. The observations below were verified on macOS with PowerPoint 16.111.3; re-check application behavior on other installations.

## 1. Export engine affects typography

Observed failure: LibreOffice exported a time text box with DrawingML `a:pPr algn="dist"` using tighter spacing than PowerPoint. The font name and size were correct, but the rendered distributed alignment was not. PowerPoint's native PDF export preserved the evenly spread digits and punctuation.

- For this failure, change the export route, not the source text or font size.
- Prefer native export from the authoring application when available. PowerPoint may still differ from WPS on application-specific features, so inspect a representative sample.
- Do not label an external renderer's preview as an inspection in PowerPoint or WPS.
- Check time/date fields, CJK fonts, weight, line breaks and image crops. A PDF text-extraction check cannot verify spacing or visual fidelity.

### Verified macOS PowerPoint route

Use the installed application's scripting dictionary to confirm commands. On this host it is at `/Applications/Microsoft PowerPoint.app/Contents/Resources/PowerPoint.sdef`.

Work on uniquely named copies to avoid accidentally exporting or closing a user-owned open presentation. The following API pattern was exercised successfully:

```applescript
tell application "Microsoft PowerPoint"
    with timeout of 900 seconds
        open POSIX file "/absolute/staging/unique-copy.pptx"
        set p to active presentation
        save p in (POSIX file "/absolute/staging/export.pdf") as save as PDF
        close p saving no
    end timeout
end tell
```

The `POSIX file` wrapper on the destination matters. In the observed run, a bare POSIX path string returned without error but did not create the expected PDF. Check that the PDF exists, is nonempty, opens, and has the expected page count. Close only presentations opened for the operation; handle errors without closing unrelated user documents. Do not launch concurrent exports through the same application instance or rely on `active presentation` after an intervening user action; validate its name against the uniquely named copy.

Rasterize the verified PDF with Poppler, for example:

```sh
pdftoppm -scale-to 3600 -png -singlefile /absolute/staging/export.pdf /absolute/staging/date-name
```

`-singlefile` is appropriate only after confirming one page. For multiple slides use page-indexed names/ranges. A 3600-pixel longest edge was useful for these portrait posters, not a universal requirement; retain the actual aspect ratio. Stage all images, inspect representative pages and every known-problem field, then replace authorized destination files. Native PDF export followed by rasterization should be described accurately rather than as direct native PNG export.

## 2. Diagnose missing fonts before rewriting formatting

Compare both stored properties and actual font availability:

- `a:rPr` and paragraph defaults: `sz`, `b`, `spc`, kerning, color, Latin/East Asian/complex-script typefaces.
- `a:pPr`, `a:bodyPr`, autofit, margins, alignment, shape transforms, and theme/master inheritance where relevant.
- Font family and specific weights. A family match alone may still substitute Medium or Heavy.

Observed case: every PPT declared the same fonts as the template, yet the Mac lacked both `思源黑体 Medium` and `思源黑体 Heavy`. CoreText resolved those names to Helvetica. Installing the actual Source Han Sans SC Medium and Heavy fonts made both resolve to their intended PostScript names.

A read-only Swift probe:

```swift
import CoreText
for name in ["思源黑体 Medium", "思源黑体 Heavy"] {
    let font = CTFontCreateWithName(name as CFString, 30, nil)
    print(name, CTFontCopyPostScriptName(font), CTFontCopyFamilyName(font))
}
```

CoreText substitution is evidence about the system, not proof of what an already-running WPS window currently uses. A correct font name in XML is likewise not proof of correct display.

If font installation is within the authorized repair, validate the downloaded font, use an official source and the host's network/proxy rules, and install persistently in the user's font directory. Verify resolution afterward. `CTFontManagerRegisterFontsForURL` may report "already registered" because copying into `~/Library/Fonts` already registered it; verify the resolved font rather than treating that alone as failure. The user may need to reopen the document or restart the app after saving their work; do not forcibly quit it.

Fonts placed only in a temporary export directory fix that renderer, not the user's editor. Never claim they were installed in the system. Temporary substitutes such as Noto can help inspect layout but must be disclosed and must not silently become final typography. Inspect PDF embedded fonts with `pdffonts` when useful.

## 3. Preserve the current template and edits

- Re-read actual current files before each batch. Users may have inserted portraits, changed text, or adjusted spacing since a previous turn.
- Keep an explicit mapping from date/name to presentation, portrait and QR code; honor confirmed spelling and date corrections. Match by identity, not row index or loose filename similarity.
- Do not interpret "start from doctor X; previously inserted ones can be skipped" as an alphabetical cutoff without checking the intended order. Audit all candidate files and distinguish already completed, pending with available materials, and missing materials. When the range is explicit, respect it and report any pending work outside it.
- Use existing picture hashes and relationships to detect repeated placeholders, but verify their meaning before replacing them. Shape order alone is not a reliable portrait selector.
- Preserve images and QR codes during text-only edits. Preserve text, QR code relationships, and crop/position choices outside the intended portrait operation.
- Treat a requested two-character-name space as a display convention for the current project, not a universal Chinese-name rule. Copy the reference's actual space/run formatting, retain filenames without the display space unless requested, and preserve existing correct user edits.

For a narrow OOXML patch, edit only the necessary ZIP parts. Preserve unrelated parts byte-for-byte. Keep run-level language/style differences when they matter, and change existing runs rather than flattening all rich text. When a template is copied between shapes, retain the destination's IDs and relationships and avoid carrying doctor-specific text. Save a recoverable backup, verify the ZIP and text coverage, and render for visual fit.

Do not force long hospital names or three-character names back into placeholder-sized boxes that cannot contain them. Preserve font size; adapt width/placement within the approved reference layout. Do not change these merely to address a missing-font complaint.

## 4. Portrait and transparency handling

- Compare available originals against transparent outputs by confirmed identity; an older spelling can otherwise appear to be missing.
- PNG format alone does not prove transparency. Inspect the alpha channel and the visual boundary against a contrasting background.
- Preserve original photographs. Use an editing workflow allowed by the active tools and user instructions. A prior explicit request for deterministic local background removal can remain applicable; a batch request alone does not authorize switching editing methods.
- For deterministic masking, retain original dimensions and RGB values and change alpha only; verify those invariants. Low-resolution input stays low-resolution even after background removal.
- Fit portraits proportionally into the approved area, usually with a common bottom alignment when the reference uses it. Avoid stretching people to identical width and height. Inspect whether transparent margins make a person appear too small.
- Keep the original media or a backup. On insertion, update the intended image relationship/media, not every similarly named image. Remove stale crop settings only when necessary for the requested placement.
- Report missing portraits separately; do not substitute another person's portrait or label a placeholder as complete.

## 5. Finder visibility and complete delivery

Observed failure: shell listing showed 25 files while Finder showed only 3. The other 22 had the macOS `hidden` flag. Copying metadata from staging can propagate this flag; hidden working locations should not determine deliverable visibility.

Inspect using `ls -lO@` or `Path.stat().st_flags`. Clear an unintended hidden bit on known deliverables while preserving other flags:

```python
import os, stat
os.chflags(output_path, output_path.stat().st_flags & ~stat.UF_HIDDEN)
```

Do not blame iCloud, synchronization or the user's view merely because shell file counts differ. Check hidden flags and whether the two paths resolve to the same location first. Do not toggle Finder's global hidden-file setting as a substitute for correcting output metadata.

Before delivery, verify expected identities and filenames, readable files, dimensions/page counts, nonhidden outputs, and latest-source provenance. A manifest of source hashes can detect edits made during a long export. Rerender affected sources if they change. When the user requests all posters regenerated after multiple edits, reread all latest PPTs; do not reuse older PDFs or refresh only the last changed doctor. Avoid adding private contact sheets, logs, scripts or backups to the deliverable folder.
