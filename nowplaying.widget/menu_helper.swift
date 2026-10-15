import AppKit
import Foundation

struct StreamInfo: Codable {
    var index: Int
    var title: String?
    var artist: String?
    var appName: String?
    var isActive: Bool?
}

struct MenuState: Codable {
    var sizePreset: String?
    var enableSnapping: Bool?
    var isPlaying: Bool?
    var isPaused: Bool?
    var title: String?
    var artist: String?
    var appName: String?
    var streams: [StreamInfo]?
}

class MenuDelegate: NSObject {
    var outputAction: String?

    @objc func handleItem(_ sender: NSMenuItem) {
        outputAction = sender.representedObject as? String
    }
}

var state = MenuState()
if CommandLine.arguments.count > 1 {
    let jsonStr = CommandLine.arguments[1]
    if let data = jsonStr.data(using: .utf8) {
        state = (try? JSONDecoder().decode(MenuState.self, from: data)) ?? MenuState()
    }
}

let currentPreset = state.sizePreset ?? "medium"
let hasSnapping = state.enableSnapping ?? true
let isPlaying = state.isPlaying ?? false
let isPaused = state.isPaused ?? false

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let delegate = MenuDelegate()
let menu = NSMenu(title: "Now Playing Controls")
menu.autoenablesItems = false

// Header Item
var headerTitle = "🎵 Now Playing"
if let appName = state.appName, !appName.isEmpty {
    headerTitle = "🎵 Now Playing (\(appName))"
}
let header = NSMenuItem(title: headerTitle, action: nil, keyEquivalent: "")
header.isEnabled = false
menu.addItem(header)

// If track is playing, show track title/artist (truncated if too long) as disabled subtitle
if isPlaying, let title = state.title, !title.isEmpty {
    let artist = state.artist ?? ""
    let subtitleText = (artist.isEmpty || artist == "Playback Idle") ? title : "\(title) – \(artist)"
    let truncatedSubtitle = subtitleText.count > 36 ? String(subtitleText.prefix(33)) + "…" : subtitleText
    let trackItem = NSMenuItem(title: truncatedSubtitle, action: nil, keyEquivalent: "")
    trackItem.isEnabled = false
    menu.addItem(trackItem)
}

menu.addItem(NSMenuItem.separator())

// Playback Controls (when playing)
if isPlaying {
    let playPauseTitle = isPaused ? "▶  Play" : "⏸  Pause"
    let playPauseItem = NSMenuItem(title: playPauseTitle, action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    playPauseItem.target = delegate
    playPauseItem.representedObject = "{\"action\":\"CONTROL_PLAYPAUSE\"}"
    menu.addItem(playPauseItem)

    let nextItem = NSMenuItem(title: "⏭  Next Track", action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    nextItem.target = delegate
    nextItem.representedObject = "{\"action\":\"CONTROL_NEXT\"}"
    menu.addItem(nextItem)

    let prevItem = NSMenuItem(title: "⏮  Previous Track", action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    prevItem.target = delegate
    prevItem.representedObject = "{\"action\":\"CONTROL_PREVIOUS\"}"
    menu.addItem(prevItem)

    menu.addItem(NSMenuItem.separator())
}

// Multi-stream audio source submenu (if more than 1 stream)
if let streams = state.streams, streams.count > 1 {
    let streamParent = NSMenuItem(title: "Audio Source", action: nil, keyEquivalent: "")
    let streamMenu = NSMenu(title: "Audio Source")
    streamMenu.autoenablesItems = false
    for s in streams {
        let appName = s.appName ?? "Player"
        let sTitle = s.title ?? "Unknown Track"
        let fullLabel = "\(appName): \(sTitle)"
        let label = fullLabel.count > 32 ? String(fullLabel.prefix(29)) + "…" : fullLabel
        let item = NSMenuItem(title: label, action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
        item.target = delegate
        item.representedObject = "{\"action\":\"SET_STREAM_INDEX\",\"index\":\(s.index)}"
        if s.isActive == true {
            item.state = .on
        }
        streamMenu.addItem(item)
    }
    streamParent.submenu = streamMenu
    menu.addItem(streamParent)
}

// Widget Size Submenu
let sizeParent = NSMenuItem(title: "Widget Size", action: nil, keyEquivalent: "")
let sizeMenu = NSMenu(title: "Widget Size")
sizeMenu.autoenablesItems = false
let sizeOptions: [(String, String)] = [
    ("Small (154 × 154)", "small"),
    ("Medium (300 × 154)", "medium"),
    ("Large (300 × 435)", "large")
]
for (label, key) in sizeOptions {
    let item = NSMenuItem(title: label, action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    item.target = delegate
    item.representedObject = "{\"action\":\"SET_SIZE_PRESET\",\"preset\":\"\(key)\"}"
    if currentPreset == key {
        item.state = .on
    }
    sizeMenu.addItem(item)
}
sizeParent.submenu = sizeMenu
menu.addItem(sizeParent)

// Snapping Toggle
let snapItem = NSMenuItem(title: "Snap to Edges", action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
snapItem.target = delegate
snapItem.representedObject = "{\"action\":\"TOGGLE_SNAPPING\"}"
if hasSnapping {
    snapItem.state = .on
}
menu.addItem(snapItem)

menu.addItem(NSMenuItem.separator())

// Reset Position
let resetItem = NSMenuItem(title: "Reset Position", action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
resetItem.target = delegate
resetItem.representedObject = "{\"action\":\"RESET_POSITION\"}"
menu.addItem(resetItem)

// Pop up native menu above all windows at cursor location
let mouseLoc = NSEvent.mouseLocation
menu.popUp(positioning: nil, at: mouseLoc, in: nil)

if let action = delegate.outputAction {
    print(action)
}
