# macOS Übersicht Widgets

Minimal, glassmorphic desktop widgets for [Übersicht](https://tracesof.net/uebersicht/) on macOS.

---

## 1. `nowplaying.widget`

Displays currently playing audio on macOS (Spotify, Apple Music, YouTube Music, web browsers, local media players).

### Features
- Track title, artist, album, cover art, and progress bar.
- On-widget playback controls (previous, play/pause, next) with 0ms optimistic response.
- Draggable anywhere on screen with position preserved across reboots.
- Queries macOS MediaRemote directly via `nowplaying-cli`.

---

## 2. `shell.widget`

An interactive, draggable, and resizable desktop shell widget with an inherited **iTerm2 color theme**.

### Features
- **iTerm2 Theme Integration**: Automatically styled with the exact color palette (background, foreground, cursor, and full 16-color ANSI spectrum) from your iTerm2 profile.
- **Interactive Terminal**: Type any shell command directly into the prompt (`❯`) and hit Enter to execute.
- **PTY ANSI Engine**: Renders full-color terminal output (`fastfetch`, `git status`, `ls -G`, `top -l 1`) in rich styled text.
- **Command History & Lifecycle**: Up/Down arrow key history, active execution state indicator, and cancel support (`Esc` / `Ctrl+C`).
- **Draggable & Resizable**: Drag by the titlebar or window, and resize using the bottom-right grip. Position and size are preserved in `localStorage`.
- **Zero Background Daemons**: Runs 100% inside Übersicht's standard native environment—no open ports, no listening sockets, fully enterprise EDR compliant.

---

## 3. `cava.widget`

A terminal-styled desktop audio visualizer for [CAVA](https://github.com/karlstav/cava) inheriting your iTerm2 Gruvbox theme.

### Features
- **Authentic Terminal Appearance**: Renders responsive audio frequency bars using the 8-stop vertical gradient defined in `~/.config/cava/config` (`#59cc33` base → `#cccc33` mid → `#cc3333` peak).
- **CoreAudio Tap Integration**: Visualizes live system audio output via CoreAudio AudioTap.
- **Draggable & Resizable**: Drag by the title bar and resize via the bottom-right corner grip. Position and dimensions persist in `localStorage`.
- **Zero Sockets / EDR Friendly**: Uses local `/tmp` file IPC with automatic heartbeat cleanup (auto-exits when widget is hidden or Übersicht quits). No open ports or listening TCP daemons.

---

## Requirements

- [Übersicht](https://tracesof.net/uebersicht/)
- [nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli) (for `nowplaying.widget`):
  ```bash
  brew install nowplaying-cli
  ```
- [cava](https://github.com/karlstav/cava) (for `cava.widget`):
  ```bash
  brew install cava
  ```

---

## Install

Copy or symlink the widgets into your Übersicht widgets directory:

```bash
git clone https://github.com/etherlucid/uebersicht-now-playing.git
cp -r uebersicht-now-playing/nowplaying.widget "$HOME/Library/Application Support/Übersicht/widgets/"
cp -r uebersicht-now-playing/shell.widget "$HOME/Library/Application Support/Übersicht/widgets/"
cp -r uebersicht-now-playing/cava.widget "$HOME/Library/Application Support/Übersicht/widgets/"
```

Or symlink:

```bash
ln -s "$(pwd)/nowplaying.widget" "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget"
ln -s "$(pwd)/shell.widget" "$HOME/Library/Application Support/Übersicht/widgets/shell.widget"
ln -s "$(pwd)/cava.widget" "$HOME/Library/Application Support/Übersicht/widgets/cava.widget"
```
