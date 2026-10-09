# WPS macro contract

This reference is for generating WPS JavaScript macros. It does not provide a WPS runtime. Unless a WPS connector explicitly reports execution, the macro remains code for the user to paste and run in WPS.

## Object coverage

Describe the exact traversal before writing the macro. A typical slide-shape traversal covers ordinary text boxes, placeholders, groups, and table cells. It does not automatically cover slide masters, layouts, SmartArt, chart text, embedded documents, comments, or every object exposed by WPS.

Notes pages are separate from visible slide content. Include them only when the user asks for notes or explicitly accepts changing notes. The macro should expose this as a clear option rather than silently editing notes.

## Title selection

Prefer an actual title placeholder or an explicit shape selector. A top-coordinate heuristic is only a fallback because logos, headers, dates, page numbers, and decorative labels can also sit near the top of a slide.

If groups are traversed, carry the exact matched child shape forward and format that child. Do not mark a group as a title candidate and then format the first text child found later. The candidate and the modified object must be the same object.

## Color-only changes

The default title-color operation changes only `TextFrame.TextRange.Font.Color.RGB`. It must leave font size, position, width, height, wrapping, and autosize unchanged. Layout operations belong in a separate command and require explicit user intent.

The standard RGB integer calculation is:

```js
const rgb = r + (g << 8) + (b << 16);
```

Validate that `r`, `g`, and `b` are integers in the inclusive range 0 to 255 before applying the value.

## Text replacement

Use a name that reflects the scope. If the macro traverses every slide shape, a name such as `replaceTextEverywhere` is clearer than `replaceTitleText`.

Replacement rules should be applied in an intentional order. If one rule removes a brand suffix and a later rule matches the remaining brand name, test the sequence with representative text. Confirm whether the WPS `TextRange.Replace` implementation replaces one or all matches in the target version. Count actual occurrences only when the implementation measures actual occurrences; otherwise report matched text ranges or objects.

## Font replacement

Checking only the aggregate `TextRange.Font.Name` works only when the entire range has one font. For mixed formatting, iterate the text runs or characters exposed by the target WPS object model. For Chinese text, check whether the target runtime stores the East Asian font separately, for example through a `NameFarEast`-style property. Do not promise full replacement if the runtime does not expose those properties.

## Error handling

Use narrow error boundaries around optional object types. Record the slide number, object identifier or name, operation, and error message for skipped objects. A final “completed” message must include changed, skipped, and failed counts so a silent partial run is not mistaken for success.

## JavaScript compatibility

`const`, `let`, template strings, array destructuring, and `String.prototype.startsWith()` require a sufficiently modern WPS JavaScript runtime. If the target WPS version is unknown, either use conservative syntax or call out the compatibility requirement. `Dir()` and `MkDir()` are not standard JavaScript and must not be assumed to exist merely because they are familiar from VBA.
