# uebersicht-now-playing

A minimal, glassmorphic desktop Now Playing widget for [Übersicht](https://tracesof.net/uebersicht/) on macOS.

Queries macOS MediaRemote directly via `nowplaying-cli`, displaying playback metadata, album artwork, track progress, genuine application badges, and responsive controls across all native and web media apps.

---

## Features

- **Multi-App Media Remote**: Seamlessly detects and controls Spotify, Apple Music, YouTube Music (Safari PWA & browsers), Firefox, Chrome, Safari, and other macOS media players.
- **Authentic macOS App Badges**: Displays genuine macOS application icons extracted directly from app bundles.
- **Multi-Stream Carousel**: Cycle between multiple active media streams with chevrons and indicator dots. Prioritizes actively playing media and dedicated audio players.
- **3 Size Presets**:
  - **Small (154×154)**: Compact 1:1 square card with track art, title, artist, and compact controls.
  - **Medium (300×154)**: Standard desktop card with full metadata, progress bar, time indicators, and rating buttons.
  - **Large (300×435)**: Full-bleed poster card with prominent album artwork, expanded typography, and detailed playback controls.
- **Stationary Anchor**: Right-click context menu lets you switch size presets seamlessly without shifting your configured top-left screen position.
- **Smart Artwork Caching**: Artwork is cached per-track on disk to eliminate flicker, prevent phantom clearing, and protect web app art.
- **Like / Dislike Ratings**: Dedicated rating controls with direct integration for YouTube Music and Apple Music.
- **Draggable Anywhere**: Drag the card anywhere on screen; position is preserved across reboots and widget reloads in `localStorage`.

---

## Requirements

- [Übersicht](https://tracesof.net/uebersicht/)
- [nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli):
  ```bash
  brew install nowplaying-cli
  ```

---

## Installation

1. Clone or copy the widget to your Übersicht widgets folder:
   ```bash
   git clone https://github.com/etherlucid/uebersicht-now-playing.git
   cp -r uebersicht-now-playing/nowplaying.widget "$HOME/Library/Application Support/Übersicht/widgets/"
   ```

   *Or symlink:*
   ```bash
   ln -s "$(pwd)/uebersicht-now-playing/nowplaying.widget" "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget"
   ```

2. (Optional) Copy `main.css` to `~/Library/Application Support/Übersicht/widgets/main.css` for shared font/backdrop styling.

3. Refresh Übersicht.

---

## Related Widgets

- [uebersicht-cava](https://github.com/etherlucid/uebersicht-cava): Responsive desktop audio visualizer for CAVA.
- [uebersicht-shell](https://github.com/etherlucid/uebersicht-shell): Interactive desktop terminal & fastfetch widget.
