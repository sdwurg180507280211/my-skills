# Batch background replacement

Read when the user asks to replace the master or slide background of one or more decks with a new image, for example a yearly template refresh where content stays the same and only the branded background changes. The observations below come from a 35-deck batch edited in WPS on macOS; re-check behavior on other decks.

## 1. Where the visible background comes from

A slide shows the first background found in this chain: slide `p:bg` → layout `p:bg` → master `p:bg`. Pictures on top of that are separate:

- A full-slide picture inside a **layout** (often `userDrawn`) covers the background of every slide that uses the layout, whatever the master says.
- A full-slide picture inside the **master** covers layouts only when `showMasterSp` is not `0` on both the layout and the slide.
- A slide's own `p:bg` overrides everything below it. Covers and section dividers usually have one.

So "replace the master background" only works on decks whose content slides inherit the master. Always run `inspect` first:

```text
python3 scripts/replace_backgrounds.py inspect <deck.pptx>...
```

Observed structures in one batch with identical branding:

| Structure | Master | Layouts | Result of changing only the master |
|---|---|---|---|
| A | image bg | content layout inherits; end-page layout has a full-slide picture | content slides change; cover keeps its slide bg; end page unchanged |
| B | theme `bgRef` | cover and content layouts each carry a full-slide picture | **nothing visible changes** |

## 2. Side effects of doing it by hand in WPS

Comparing a manually edited deck with its source showed:

- "Apply to all" removed the cover slide's own background, so the cover then showed the content background instead of a cover image. Ask whether the cover gets its own image.
- Saving re-computed `normAutofit fontScale` on a text placeholder (100% to 30%) without any text edit. Treat any WPS/PowerPoint resave as able to change autofit; the script never touches text bodies.
- Saving also renumbers media and may delete unused layouts, so byte-level diffs are noisy. Compare semantically by slide/layout/master and by image hash.

## 3. Scripted workflow

1. **Freeze the sources.** If another session or person may be editing the folder (lock files `.~name` or `~$name`, new media names, recent mtimes), read from a pristine copy such as the original archive and write to a new directory. Never edit in place.
2. **Inspect** every deck and classify it (section 1). Note slide-level overrides: they may be old-template copies (safe to clear) or deliberate designs (ask).
3. **Apply** to a new directory:

   ```text
   python3 scripts/replace_backgrounds.py apply <decks>... \
       --content content.png --cover cover.png --out-dir <new-dir> --report-dir <report-dir>
   ```

   Masters get `--content`; slides in `--cover-slides` (default `1`) get `--cover`; layout and other slide backgrounds are cleared so they inherit the master; full-slide non-placeholder pictures on masters and layouts are removed; orphaned media are dropped. Existing outputs are not overwritten without `--overwrite`.
4. **Check what was removed.** `--report-dir` keeps one copy of each removed image under `removed-images/`. Look at them: they must all be old backgrounds. A full-slide picture that is real content means the 90% size rule is wrong for that deck.
5. **Verify.** `apply` re-opens each output and fails a deck if any slide's effective background is not the requested image, a full-slide picture still covers it, or a relationship is broken that was not already broken in the source. Pre-existing broken relationships (for example a missing SmartArt drawing cache) are left alone and not reported as new.
6. **Look at it.** Structural checks do not prove the editor opens the file without a repair prompt. macOS Quick Look gives a quick cover thumbnail without starting an office suite: `qlmanage -t -s 800 -o <dir> <copy.pptx>`. For full pages prefer native PowerPoint export (see `poster-fidelity.md`), and ask the user to open a sample per structure in their delivery app.

## 4. Image size

Template backgrounds are often exported far larger than needed (5120×2880 PNG, ~8 MB). Each deck embeds its own copy, so a 35-deck batch grew by ~300 MB. Projection needs at most 3840×2160; 2560×1440 JPEG at quality 90 (4:4:4) was indistinguishable at 2× zoom on logos, small English text and gradients, and cut the batch from 561 MB to 266 MB.

- Check the alpha channel before converting PNG to JPEG; only convert when it is fully opaque.
- Keep the user's originals; write compressed copies elsewhere and show a zoomed side-by-side before regenerating.
- Images whose aspect ratio differs from the slide are stretched; `apply` warns about this.

## 5. Whole-series template (cover, title, content and end pages)

Lessons from a 17-deck batch. Use `scripts/swap_template_pages.py`:

```text
python3 scripts/swap_template_pages.py <decks>... --cover c.jpg --title t.jpg --content x.jpg \
    --restyle 14,15,16,17 --logo-box 15,15,68,68 --title-left 75 --end-text "感谢聆听|THANKS" \
    --out-dir <new-dir> --report-dir <report-dir>
```

- Compare the template images by MD5 first; the user re-exported them mid-task, and the title and end images were the same.
- Decks came in two families. Family A had a picture-only cover and kept every old decoration inside full-slide layout pictures, so swapping page by page was enough. Family B (`--restyle`) had no picture cover and kept its decorations as small pictures on the layouts; one deck had also pasted them onto every slide.
- `--restyle` inserts a cover slide, removes the layout decorations, and removes their slide copies by matching image MD5 across all restyled decks. The header rule copies differed by 1 pt and in rect versus roundRect, so they need a dedicated rule.
- On the new background the top-left logo overlapped family-B titles, so `--logo-box` moves those text boxes right and keeps their right edge.
- The old end page can be one picture of the thank-you text, or white text that disappears on a light background. `--end-text` rewrites it to the template's centred text, and appends an end page when the last slide is a summary.
- Tell the user about any brand or product logo in `removed-images/`.
- When one deck is wrong, rerun only that deck with `--overwrite` and render only the pages it changes. Re-running and re-rendering all 17 decks was the slowest part of the job.
- A second batch (21 decks of a single family, a master image plus a slide-1 cover image) used three images (cover, content, and an end image with the thank-you words already printed) and no title page. Flags: omit `--title`; use `--end-clear` to empty the old thanks slide so the words do not appear twice; use `--cover-title-box 92,166,580` to move the cover title out of the way of the artwork, left-aligned, as one block, with footer codes in the lowest 15% left in place; and use `--title-color 2986C4` to give the cover title, the title placeholders and the master title style the template's title colour (colour only), using a top-left non-white text box where a slide has no title placeholder.
- Read the template deck's own text colours (`PPT模板.pptx`) and not only its images; the user expected the title colour to follow the template.
