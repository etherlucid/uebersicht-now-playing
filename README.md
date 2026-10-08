# nowplaying.widget

An [Übersicht](https://tracesof.net/uebersicht/) desktop widget that displays the currently playing audio on macOS (Spotify, Apple Music, YouTube Music, web browsers, local media players).

## What it does

- Shows track title, artist, album, cover art, and progress bar.
- On-widget playback controls (previous, play/pause, next).
- Draggable anywhere on screen with position saved across reboots.
- Queries macOS MediaRemote directly using `nowplaying-cli`.

## Requirements

- [Übersicht](https://tracesof.net/uebersicht/)
- [nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli):
  ```bash
  brew install nowplaying-cli
  ```

## Install

Copy or symlink `nowplaying.widget` into your Übersicht widgets folder:

```bash
git clone https://github.com/etherlucid/uebersicht-now-playing.git
cp -r uebersicht-now-playing/nowplaying.widget "$HOME/Library/Application Support/Übersicht/widgets/"
```

Or symlink:

```bash
ln -s "$(pwd)/nowplaying.widget" "$HOME/Library/Application Support/Übersicht/widgets/nowplaying.widget"
```
