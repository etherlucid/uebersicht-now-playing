#!/usr/bin/env python3
import sys
import os
import json
import ctypes
import subprocess

CACHE_RATINGS_FILE = "/tmp/nowplaying_ratings.json"

def send_mediaremote_command(cmd_id):
    try:
        mr = ctypes.CDLL('/System/Library/PrivateFrameworks/MediaRemote.framework/MediaRemote')
        mr.MRMediaRemoteSendCommand.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        mr.MRMediaRemoteSendCommand.restype = ctypes.c_bool
        return mr.MRMediaRemoteSendCommand(cmd_id, None)
    except Exception:
        return False

def find_nowplaying_cli():
    paths = [
        "/opt/homebrew/bin/nowplaying-cli",
        "/usr/local/bin/nowplaying-cli",
    ]
    for p in paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return "/opt/homebrew/bin/nowplaying-cli"

def get_mediaremote_client_bundle_id():
    cli = find_nowplaying_cli()
    if not os.path.exists(cli):
        return ""
    try:
        proc = subprocess.run([cli, "get-raw"], capture_output=True, text=True, timeout=0.8)
        stdout = proc.stdout.strip()
        if stdout and stdout != "null":
            data = json.loads(stdout)
            return (data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or "").lower()
    except Exception:
        pass
    return ""

def control_apple_music(action):
    try:
        check = subprocess.run(
            ["pgrep", "-x", "Music"],
            capture_output=True,
            timeout=0.5
        )
        if check.returncode == 0:
            if action == "like":
                res = subprocess.run(
                    ["osascript", "-e", '''
tell application "Music"
  set favorited of current track to not (favorited of current track)
  return favorited of current track
end tell'''],
                    capture_output=True,
                    text=True,
                    timeout=1.2
                )
                val = res.stdout.strip().lower()
                return {"success": True, "rating": "liked" if val == "true" else "none"}
            elif action == "dislike":
                res = subprocess.run(
                    ["osascript", "-e", '''
tell application "Music"
  set disliked of current track to not (disliked of current track)
  return disliked of current track
end tell'''],
                    capture_output=True,
                    text=True,
                    timeout=1.2
                )
                val = res.stdout.strip().lower()
                return {"success": True, "rating": "disliked" if val == "true" else "none"}
            elif action == "toggleplaypause":
                subprocess.run(["osascript", "-e", 'tell application "Music" to playpause'], timeout=1.0)
                return {"success": True}
            elif action == "next":
                subprocess.run(["osascript", "-e", 'tell application "Music" to next track'], timeout=1.0)
                return {"success": True}
            elif action == "previous":
                subprocess.run(["osascript", "-e", 'tell application "Music" to previous track'], timeout=1.0)
                return {"success": True}
    except Exception:
        pass
    return {"success": False, "rating": None}

def control_spotify(action):
    try:
        check = subprocess.run(
            ["pgrep", "-x", "Spotify"],
            capture_output=True,
            timeout=0.5
        )
        if check.returncode == 0:
            if action == "toggleplaypause":
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to playpause'], timeout=1.0)
                return {"success": True}
            elif action == "next":
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to next track'], timeout=1.0)
                return {"success": True}
            elif action == "previous":
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to previous track'], timeout=1.0)
                return {"success": True}
    except Exception:
        pass
    return {"success": False, "rating": None}

def control_ytmusic(action):
    try:
        check = subprocess.run(
            ["pgrep", "-x", "Web App"],
            capture_output=True,
            timeout=0.5
        )
        if check.returncode != 0:
            return {"success": False, "rating": None}

        if action in ("like", "dislike"):
            script = f'''
tell application "System Events"
  try
    tell process "Web App"
      set w to window 1
      set s to first UI element of w whose role is "AXSplitGroup"
      set tb to first UI element of s whose role is "AXTabGroup"
      set g1 to first UI element of tb whose role is "AXGroup"
      set g2 to first UI element of g1 whose role is "AXGroup"
      set sa to first UI element of g2 whose role is "AXScrollArea"
      set wa to first UI element of sa whose role is "AXWebArea"
      set playerBar to first UI element of wa whose description is "Player bar"
      if "{action}" is "like" then
        set btn to first checkbox of UI element 18 of playerBar
        click btn
        delay 0.15
        set newVal to value of btn as text
        return newVal
      else
        set btn to UI element 19 of playerBar
        click btn
        delay 0.15
        set newVal to value of btn as text
        return newVal
      end if
    end tell
  on error
    return "error"
  end try
  return "error"
end tell
'''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.8)
            val = res.stdout.strip()
            if val == "1":
                return {"success": True, "rating": "liked" if action == "like" else "disliked"}
            elif val == "0":
                return {"success": True, "rating": "none"}
            else:
                return {"success": False, "rating": None}

        elif action in ("toggleplaypause", "next", "previous"):
            script = f'''
tell application "System Events"
  try
    tell process "Web App"
      set w to window 1
      set s to first UI element of w whose role is "AXSplitGroup"
      set tb to first UI element of s whose role is "AXTabGroup"
      set g1 to first UI element of tb whose role is "AXGroup"
      set g2 to first UI element of g1 whose role is "AXGroup"
      set sa to first UI element of g2 whose role is "AXScrollArea"
      set wa to first UI element of sa whose role is "AXWebArea"
      set playerBar to first UI element of wa whose description is "Player bar"
      if "{action}" is "toggleplaypause" then
        try
          set btn to first UI element of playerBar whose description is "Pause"
          click btn
        on error
          try
            set btn to first UI element of playerBar whose description is "Play"
            click btn
          on error
            click UI element 4 of playerBar
          end try
        end try
      else if "{action}" is "next" then
        try
          set btn to first UI element of playerBar whose description is "Next"
          click btn
        on error
          click UI element 7 of playerBar
        end try
      else if "{action}" is "previous" then
        try
          set btn to first UI element of playerBar whose description is "Previous"
          click btn
        on error
          click UI element 1 of playerBar
        end try
      end if
      return "ok"
    end tell
  on error
    return "error"
  end try
end tell
'''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.8)
            return {"success": True}
    except Exception:
        pass
    return {"success": False, "rating": None}

def update_cached_rating(track_key, rating):
    if not track_key:
        return
    ratings = {}
    if os.path.exists(CACHE_RATINGS_FILE):
        try:
            with open(CACHE_RATINGS_FILE, "r") as f:
                ratings = json.load(f)
        except Exception:
            ratings = {}
    if rating and rating != "none":
        ratings[track_key] = rating
    else:
        ratings.pop(track_key, None)
    try:
        with open(CACHE_RATINGS_FILE, "w") as f:
            json.dump(ratings, f)
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False}))
        return

    action = sys.argv[1].lower()
    stream_id = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    app_name = sys.argv[3].lower() if len(sys.argv) > 3 else ""
    bundle_id = sys.argv[4].lower() if len(sys.argv) > 4 else ""
    track_key = sys.argv[5] if len(sys.argv) > 5 else ""

    is_yt = ("yt" in app_name or "youtube" in app_name or "webapp" in bundle_id or "ytmusic" in stream_id)
    is_apple = ("apple music" in app_name or "com.apple.music" in bundle_id or "apple_music" in stream_id or "music" in app_name)
    is_spotify = ("spotify" in app_name or "spotify" in bundle_id or "spotify" in stream_id)

    result = {"success": False, "rating": None}

    if is_yt:
        result = control_ytmusic(action)
    elif is_apple:
        result = control_apple_music(action)
    elif is_spotify:
        result = control_spotify(action)
    else:
        # Generic MediaRemote stream (Safari, Chrome, Podcasts, VLC, Firefox, etc.)
        # Safeguard: ensure that MediaRemote's current active client actually matches this stream!
        # If another app (like YTMusic) is currently active, sending MRMediaRemoteSendCommand would mistakenly command it.
        current_mr_bundle = get_mediaremote_client_bundle_id()
        is_target_active = False
        if bundle_id and bundle_id in current_mr_bundle:
            is_target_active = True
        elif app_name and app_name in current_mr_bundle:
            is_target_active = True
        elif not current_mr_bundle:
            is_target_active = True

        if is_target_active:
            if action in ("toggleplaypause", "next", "previous"):
                cmd_map = {
                    "toggleplaypause": 2, # kMRTogglePlayPause
                    "next": 4,            # kMRNextTrack
                    "previous": 5         # kMRPreviousTrack
                }
                cmd_id = cmd_map.get(action, 2)
                ok = send_mediaremote_command(cmd_id)
                result = {"success": ok}
            else:
                result = {"success": False, "rating": None}
        else:
            # Target stream is not the active MediaRemote client; do not hijack the active player!
            result = {"success": False, "rating": None}

    if result.get("success") and result.get("rating") is not None and track_key:
        update_cached_rating(track_key, result["rating"])

    print(json.dumps(result))

if __name__ == "__main__":
    main()
