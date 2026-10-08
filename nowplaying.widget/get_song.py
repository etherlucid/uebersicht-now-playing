#!/usr/bin/env python3
import sys
import os
import json
import base64
import subprocess
import shutil

CACHE_TRACK_FILE = "/tmp/nowplaying_track.txt"
CACHE_ART_FILE = "/tmp/nowplaying_art_data.txt"

def find_nowplaying_cli():
    paths = [
        "/opt/homebrew/bin/nowplaying-cli",
        "/usr/local/bin/nowplaying-cli",
    ]
    for p in paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    which_p = shutil.which("nowplaying-cli")
    if which_p:
        return which_p
    return "/opt/homebrew/bin/nowplaying-cli"

def get_nowplaying_data():
    cli = find_nowplaying_cli()
    if not os.path.exists(cli) and not shutil.which(cli):
        return None

    try:
        proc = subprocess.run(
            [cli, "get-raw"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        stdout = proc.stdout.strip()
        if not stdout or stdout == "null":
            return None
        return json.loads(stdout)
    except Exception:
        return None

def process_artwork(data, track_key):
    cached_track = ""
    if os.path.exists(CACHE_TRACK_FILE):
        try:
            with open(CACHE_TRACK_FILE, "r") as f:
                cached_track = f.read().strip()
        except Exception:
            pass

    artwork_data_url = ""

    # If the track changed, convert new artwork
    if track_key != cached_track:
        raw_art = data.get("kMRMediaRemoteNowPlayingInfoArtworkData")
        if raw_art:
            try:
                art_bytes = base64.b64decode(raw_art)
                tmp_in = "/tmp/nowplaying_art.tiff"
                tmp_out = "/tmp/nowplaying_art.jpg"
                with open(tmp_in, "wb") as f:
                    f.write(art_bytes)

                subprocess.run(
                    ["sips", "-Z", "160", "-s", "format", "jpeg", tmp_in, "--out", tmp_out],
                    capture_output=True,
                    timeout=1.0
                )

                if os.path.exists(tmp_out):
                    with open(tmp_out, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode("ascii")
                    artwork_data_url = f"data:image/jpeg;base64,{b64_img}"
                    with open(CACHE_ART_FILE, "w") as f:
                        f.write(artwork_data_url)
            except Exception:
                pass
        else:
            if os.path.exists(CACHE_ART_FILE):
                try:
                    os.remove(CACHE_ART_FILE)
                except Exception:
                    pass

        try:
            with open(CACHE_TRACK_FILE, "w") as f:
                f.write(track_key)
        except Exception:
            pass
    else:
        # Track hasn't changed, reuse cached artwork
        if os.path.exists(CACHE_ART_FILE):
            try:
                with open(CACHE_ART_FILE, "r") as f:
                    artwork_data_url = f.read().strip()
            except Exception:
                pass

    return artwork_data_url

def get_app_name(bundle_id):
    if not bundle_id:
        return "macOS Audio"
    b = bundle_id.lower()
    if "spotify" in b:
        return "Spotify"
    if "apple.music" in b or "itunes" in b:
        return "Apple Music"
    if "safari" in b or "webkit" in b:
        return "Web Audio"
    if "chrome" in b:
        return "Google Chrome"
    if "firefox" in b:
        return "Firefox"
    if "iina" in b:
        return "IINA"
    if "vlc" in b:
        return "VLC"
    return "macOS Audio"

def main():
    data = get_nowplaying_data()
    if not data:
        print(json.dumps({"playing": False}))
        return

    title = data.get("kMRMediaRemoteNowPlayingInfoTitle") or ""
    if not title or title == "null":
        print(json.dumps({"playing": False}))
        return

    artist = data.get("kMRMediaRemoteNowPlayingInfoArtist") or ""
    if artist == "null":
        artist = ""

    album = data.get("kMRMediaRemoteNowPlayingInfoAlbum") or ""
    if album == "null":
        album = ""

    duration = float(data.get("kMRMediaRemoteNowPlayingInfoDuration") or 0)
    elapsed = float(data.get("kMRMediaRemoteNowPlayingInfoElapsedTime") or 0)
    playback_rate = int(data.get("kMRMediaRemoteNowPlayingInfoPlaybackRate") or 0)
    bundle_id = data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or ""

    track_key = f"{title}___{artist}___{album}"
    artwork_url = process_artwork(data, track_key)
    app_name = get_app_name(bundle_id)

    result = {
        "playing": True,
        "title": title,
        "artist": artist,
        "album": album,
        "duration": round(duration, 1),
        "elapsed": round(elapsed, 1),
        "rate": playback_rate,
        "artwork": artwork_url,
        "bundleId": bundle_id,
        "appName": app_name
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
