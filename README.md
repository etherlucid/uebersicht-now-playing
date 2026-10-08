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
- **ANSI Color Parsing**: Renders colored terminal outputs (`git`, `ls -G`, `cal`, custom scripts) in rich styled text.
- **Command History**: Navigate previous commands using Up/Down arrow keys.
- **Draggable & Resizable**: Drag by the titlebar or window, and resize using the bottom-right grip. Position and size are preserved in `localStorage`.
- **Zero Background Daemons**: Runs 100% inside Übersicht's standard native environment—no open ports, no listening sockets, fully enterprise EDR compliant.

---

## Requirements

- [Übersicht](https://tracesof.net/uebersicht/)
- [nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli) (for `nowplaying.widget`):
  ```bash
  brew install nowplaying-cli
  ```

---

## Install

Copy or symlink the widgets into your Übersicht widgets directory:

```bash
git clone https://github.com/etherlucid/uebersicht-now-playing.git
cp -r uebersicht-now-playing/nowplaying.widget "$HOME/Library/Application Support/Übersicht/widgets/"
cp -r uebersicht-now-playing/shell.widget "$HOME/Library/Application Support/Übersicht/widgets/"
```

Or symlink:

```bash
ln -s "$(pwd)/nowplaying.widget" "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget"
ln -s "$(pwd)/shell.widget" "$HOME/Library/Application Support/Übersicht/widgets/shell.widget"
```
