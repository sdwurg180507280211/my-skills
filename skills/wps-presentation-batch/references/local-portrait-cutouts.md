# Local portrait background removal on macOS

Use for portrait preparation associated with a presentation batch. The mask-generation and alpha-composition approach below was exercised successfully on eight portraits, from 288×377 to 4480×6720 pixels.

## Choose a permitted editing route

Follow active image-tool requirements first. Use this local route when the user explicitly requests or has already approved local non-generative background removal, and the current tool instructions allow that exception. That approval persists within the authorized task; do not ask repeatedly. "Batch" or "preserve likeness" alone is not explicit permission to bypass a required editing tool.

The aim is to segment the subject and alter transparency, preserving the original decoded RGB values. It does not regenerate a face, beautify the subject, restore resolution, synthesize missing clothing, or promise perfect hair matting. Do not claim a generative edit preserves every original pixel.

## Identify only the missing work

Compare original portraits and transparent outputs by a confirmed date/name mapping, ignoring extension differences. Reconcile known name corrections and incorrect dates before deciding that a portrait is absent. Do not rely only on file counts, stem equality, or file ordering.

Classify each identity as usable transparent output, output requiring correction, original awaiting processing, or missing original. Inspect existing alpha and appearance; a PNG can still have an opaque background, and a mostly opaque image can legitimately contain a close-cropped portrait. Avoid reprocessing completed portraits without reason. Use the user's requested date-name convention, keeping display spaces in PPT names separate from filename identity.

Read the source images before processing. Background removal cannot determine whether a photograph belongs to the intended person; use the supplied materials and confirmed mapping. Do not infer missing portraits from a face resemblance.

## Verified mask generation

Requirements: macOS 14 or later for `VNGenerateForegroundInstanceMaskRequest`, a usable Swift compiler, Vision/CoreImage, and Pillow for composition. Check availability rather than assuming every Mac supports the request. No third-party model download was needed on the verified host. If the request fails, report its actual error and choose another permitted route instead of saving a fully opaque image as a successful cutout.

Normalize EXIF orientation once into a working PNG before segmentation, so the mask and original pixels share the same coordinates. Keep the original file unchanged. Use a unique staging directory and explicit absolute source/output paths.

The core Swift API sequence used successfully:

```swift
import Foundation
import Vision
import CoreImage
import ImageIO

// Validate argument count, source existence, destination policy, and OS version
// in the caller before invoking this core sequence.
let source = URL(fileURLWithPath: CommandLine.arguments[1])
let destination = URL(fileURLWithPath: CommandLine.arguments[2])
let request = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(url: source, options: [:])
try handler.perform([request])
guard let result = request.results?.first,
      !result.allInstances.isEmpty else {
    fatalError("No foreground instance detected")
}
let mask = try result.generateScaledMaskForImage(
    forInstances: result.allInstances, from: handler)
try CIContext().writePNGRepresentation(
    of: CIImage(cvPixelBuffer: mask), to: destination,
    format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
```

Compile a working copy with `swiftc` and invoke it with source and mask paths as separate arguments. This produces a mask, not a finished transparent portrait. `allInstances` worked for the supplied single-person photos; it can retain furniture or other foreground objects. Inspect and, where necessary, select the intended instance. Do not promise that all detected instances equal the person.

## Apply alpha without repainting

Use `ImageOps.exif_transpose` on the original, then convert to RGBA. Feed an orientation-normalized working image to Vision. For CMYK or unusual color profiles, define and check the color conversion rather than claiming byte-identical native-channel values.

Read the generated mask's grayscale intensity as alpha. Confirm orientation and dimensions match; resize the mask only if necessary and understood, never stretch or resample the original portrait to repair a mask mismatch. Apply the alpha to the original RGBA image with `putalpha`. If the source already contains transparency, intersect/multiply the old and new alpha so removed pixels cannot become visible again. Preserve source RGB values, dimensions, and applicable color profile. Save as RGBA PNG; JPEG cannot retain transparency.

Validate against the orientation-normalized decoded original:

```python
assert result.size == original.size
assert ImageChops.difference(
    result.convert("RGB"), original.convert("RGB")
).getbbox() is None
alpha = result.getchannel("A")
lo, hi = alpha.getextrema()
assert lo < hi and lo < 255 and hi > 0
```

An alpha-range check detects obvious failed outputs, not quality. For a usual opaque portrait cutout, fully transparent background and an opaque foreground are expected; investigate deviations instead of forcing thresholds that destroy edge detail. "Original pixels retained" refers to the decoded, orientation-normalized RGB comparison, not unchanged compressed source bytes.

## Inspect and deliver

- Compare original and cutout on a contrasting light and dark background, including full-resolution edge crops when needed. Check hair, glasses, ears, white coats, hands, and gaps between arms and torso.
- Watch for blue/gray background fringe, holes in clothing, retained stools, lost hair, or clipped hands. Segmentation alone may need edge refinement. Disclose a material remaining defect rather than calling every nonempty alpha channel successful.
- A 288×377 portrait remains low resolution after background removal. Do not call it high definition or upscale silently to imply recovered detail.
- Put finished PNGs in the requested transparent-background folder. Keep masks, code, previews and originals out of that delivery folder unless requested. Check that output files have no unintended macOS hidden flag.
- Preserve originals and existing good cutouts. Only overwrite authorized outputs; verify all expected identities and readable RGBA files before reporting completion.
- Removing backgrounds and inserting portraits into PPT are separate actions. Do not claim insertion happened when only PNG files were produced. When insertion is requested, follow the identity and proportional-placement checks in `poster-fidelity.md`.
