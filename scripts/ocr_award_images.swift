#!/usr/bin/swift

import AppKit
import Foundation
import Vision

struct OCRResult: Codable {
    let path: String
    let text: String
    let lines: [String]
    let error: String?
}

func loadCGImage(from path: String) -> CGImage? {
    guard let image = NSImage(contentsOfFile: path) else {
        return nil
    }
    var rect = CGRect(origin: .zero, size: image.size)
    return image.cgImage(forProposedRect: &rect, context: nil, hints: nil)
}

func recognizeText(from path: String) -> OCRResult {
    guard let cgImage = loadCGImage(from: path) else {
        return OCRResult(path: path, text: "", lines: [], error: "Unable to load image")
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["ko-KR", "en-US"]

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

    do {
        try handler.perform([request])
        let observations = request.results ?? []
        let lines = observations.compactMap { observation in
            observation.topCandidates(1).first?.string.trimmingCharacters(in: .whitespacesAndNewlines)
        }.filter { !$0.isEmpty }
        return OCRResult(
            path: path,
            text: lines.joined(separator: "\n"),
            lines: lines,
            error: nil
        )
    } catch {
        return OCRResult(path: path, text: "", lines: [], error: error.localizedDescription)
    }
}

let paths = Array(CommandLine.arguments.dropFirst())
let results = paths.map(recognizeText)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]

do {
    let data = try encoder.encode(results)
    FileHandle.standardOutput.write(data)
} catch {
    let fallback = """
    [{"path":"","text":"","lines":[],"error":"\(error.localizedDescription)"}]
    """
    FileHandle.standardOutput.write(fallback.data(using: .utf8)!)
}
