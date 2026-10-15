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

// Size Options (Top-level, matching native Apple presentation without pixel size)
let sizeOptions: [(String, String)] = [
    ("Small", "small"),
    ("Medium", "medium"),
    ("Large", "large")
]
for (label, key) in sizeOptions {
    let item = NSMenuItem(title: label, action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    item.target = delegate
    item.representedObject = "{\"action\":\"SET_SIZE_PRESET\",\"preset\":\"\(key)\"}"
    if currentPreset == key {
        item.state = .on
    }
    menu.addItem(item)
}

menu.addItem(NSMenuItem.separator())

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

// Order Submenu
let orderParent = NSMenuItem(title: "Order", action: nil, keyEquivalent: "")
let orderMenu = NSMenu(title: "Order")
orderMenu.autoenablesItems = false
let orderOptions: [(String, String)] = [
    ("Bring to Front", "ORDER_FRONT"),
    ("Bring Forward", "ORDER_FORWARD"),
    ("Send Backward", "ORDER_BACKWARD"),
    ("Send to Back", "ORDER_BACK")
]
for (label, act) in orderOptions {
    let item = NSMenuItem(title: label, action: #selector(MenuDelegate.handleItem(_:)), keyEquivalent: "")
    item.target = delegate
    item.representedObject = "{\"action\":\"\(act)\"}"
    orderMenu.addItem(item)
}
orderParent.submenu = orderMenu
menu.addItem(orderParent)

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
