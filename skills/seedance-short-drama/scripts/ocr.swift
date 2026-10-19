import Foundation
import Vision
import AppKit

// 用法: ocr 图片1 [图片2 ...]
// 每行输出：文件名<TAB>置信度<TAB>文字<TAB>x,y,w,h（相对坐标，原点在左上）
// 注意：对斜着的、风格化的英文字体识别不到（实测漏掉过机器上的假品牌字），检查图仍需人看。
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path)\t0\t<无法读取>\t"); continue
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([request])
    for obs in (request.results ?? []) {
        guard let c = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        print(String(format: "%@\t%.2f\t%@\t%.2f,%.2f,%.2f,%.2f", (path as NSString).lastPathComponent, c.confidence, c.string,
                     b.origin.x, 1 - b.origin.y - b.height, b.width, b.height))
    }
}
