# Migrated source notes

The initial source material was:

- `格式批量修改.md`
- `pptx格式互转pptm.md`

The feature inventory below is preserved for requests that refer to the original shortcuts. The implementation rules in `wps-macro-contract.md` take precedence over the old code.

## Formatting shortcuts

The original formatting document defined these title-color shortcuts:

- `titleToBlack()`
- `titleToBlue()`
- `titleToRed()`
- `titleToGreen()`
- `titleToYellow()`
- `titleToWhite()`
- `titleToDarkBlue()`
- `titleToOrange()`
- `titleToPurple()`

It also defined a font shortcut named `pingfangToYahei()` for replacing `苹方-简` with `微软雅黑`.

When generating a successor macro, preserve these names only when the user asks for compatibility with the old shortcuts. Keep color-only behavior separate from layout behavior, and disclose any unsupported WPS object types.

## Original replacement rules

The old `replaceDrugNames()` routine used the following ordered replacements:

```js
[
  ["尼膜同®", "尼莫地平片"],
  ["唯可同®", "维立西呱片"],
  ["拜瑞妥®", "利伐沙班片"],
  ["拜新同®", "硝苯地平控释片"],
  ["可申达®", "非奈利酮片"],
  ["希维她®", ""],
  ["尼膜同", "尼莫地平片"],
  ["唯可同", "维立西呱片"],
  ["拜瑞妥", "利伐沙班片"],
  ["拜新同", "硝苯地平控释片"],
  ["可申达", "非奈利酮片"],
  ["希维她", ""],
  ["拜耳", ""]
]
```

The order matters because the first six rules handle the registered-mark form before the unmarked form. Before using these rules in a new deck, ask the user to confirm that the substitutions are still intended for that deck.

## Conversion shortcuts

The original conversion document defined two batch entry points:

- `batchSaveAsPptm()` for PPTX to PPTM
- `batchSaveAsPptx()` for PPTM to PPTX

The direct scripts included with this Skill are preferred for file-level conversion. If a WPS macro with the old entry-point names is explicitly requested, retain the names but apply the cleanup, conflict, directory, and reporting rules from the current references.
