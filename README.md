# macOS Übersicht Widgets

Minimal, glassmorphic desktop widgets for [Übersicht](https://tracesof.net/uebersicht/) on macOS.

---

## 1. `nowplaying.widget`

Displays the currently playing audio on macOS (Spotify, Apple Music, YouTube Music, web browsers, local media players).

### Features
- Shows track title, artist, album, cover art, and progress bar.
- On-widget playback controls (previous, play/pause, next) with instant 0ms optimistic response.
- Draggable anywhere on screen with position saved across reboots.
- Queries macOS MediaRemote directly using `nowplaying-cli`.

---

## 2. `cava.widget`

Real-time audio visualizer displaying live frequency spectrum from the [cava](https://github.com/kaskas7/cava) CLI visualizer.

### Features
- **GPU-accelerated Canvas**: Smooth 35 FPS audio bars rendered via HTML5 canvas.
- **Draggable & Resizable**: Drag anywhere on screen or drag the bottom-right corner grip to resize to any width/height.
- **Persistent Layout**: Position and dimensions saved in `localStorage`.
- **Low Overhead**: Lightweight background daemon streams frames via Server-Sent Events (SSE) with near-zero CPU usage.

---

## Requirements

- [Übersicht](https://tracesof.net/uebersicht/)
- [nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli):
  ```bash
  brew install nowplaying-cli
  ```
- [cava](https://github.com/kaskas7/cava):
  ```bash
  brew install cava
  ```

---

## Install

Copy or symlink the widgets into your Übersicht widgets directory:

```bash
git clone https://github.com/etherlucid/uebersicht-now-playing.git
cp -r uebersicht-now-playing/nowplaying.widget "$HOME/Library/Application Support/Übersicht/widgets/"
cp -r uebersicht-now-playing/cava.widget "$HOME/Library/Application Support/Übersicht/widgets/"
```

Or symlink:

```bash
ln -s "$(pwd)/nowplaying.widget" "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget"
ln -s "$(pwd)/cava.widget" "$HOME/Library/Application Support/Übersicht/widgets/cava.widget"
```
