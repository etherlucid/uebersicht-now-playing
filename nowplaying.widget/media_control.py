#!/usr/bin/env python3
import sys
import os
import json
import ctypes
import subprocess

CACHE_STATE_FILE = "/tmp/nowplaying_state.json"
CACHE_RATINGS_FILE = "/tmp/nowplaying_ratings.json"

def reset_progress_state():
    if os.path.exists(CACHE_STATE_FILE):
        try:
            os.remove(CACHE_STATE_FILE)
        except Exception:
            pass

def find_nowplaying_cli():
    paths = [
        "/opt/homebrew/bin/nowplaying-cli",
        "/usr/local/bin/nowplaying-cli",
    ]
    for p in paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return "/opt/homebrew/bin/nowplaying-cli"

def get_mediaremote_raw():
    cli = find_nowplaying_cli()
    if not os.path.exists(cli):
        return None
    try:
        proc = subprocess.run([cli, "get-raw"], capture_output=True, text=True, timeout=0.8)
        stdout = proc.stdout.strip()
        if stdout and stdout != "null":
            return json.loads(stdout)
    except Exception:
        pass
    return None

def send_mediaremote_command(action):
    cli = find_nowplaying_cli()
    cmd_name = "togglePlayPause"
    action_l = (action or "").lower()
    if action_l == "next":
        cmd_name = "next"
    elif action_l == "previous":
        cmd_name = "previous"
    elif action_l in ("toggleplaypause", "playpause"):
        cmd_name = "togglePlayPause"
    elif action_l == "play":
        cmd_name = "play"
    elif action_l == "pause":
        cmd_name = "pause"

    if os.path.exists(cli):
        try:
            subprocess.Popen([cli, cmd_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    cmd_map = {
        "toggleplaypause": 2,
        "playpause": 2,
        "next": 4,
        "previous": 5,
        "play": 0,
        "pause": 1
    }
    cmd_id = cmd_map.get(action_l, 2)
    try:
        mr = ctypes.CDLL('/System/Library/PrivateFrameworks/MediaRemote.framework/MediaRemote')
        mr.MRMediaRemoteSendCommand.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        mr.MRMediaRemoteSendCommand.restype = ctypes.c_bool
        return mr.MRMediaRemoteSendCommand(cmd_id, None)
    except Exception:
        return False

def stream_matches_mediaremote(mr_data, stream_id, app_name, bundle_id, track_key):
    if not mr_data:
        return False

    mr_bundle = (mr_data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or "").lower()
    mr_title = (mr_data.get("kMRMediaRemoteNowPlayingInfoTitle") or "").lower().strip()

    target_title = ""
    if track_key:
        parts = track_key.split("___")
        target_title = parts[0].lower().strip()

    stream_id = (stream_id or "").lower()
    app_name = (app_name or "").lower()
    bundle_id = (bundle_id or "").lower()

    is_yt = (stream_id == "ytmusic" or "youtube" in app_name or "yt music" in app_name or "webapp" in bundle_id)
    is_apple = (stream_id == "apple_music" or "apple.music" in bundle_id or bundle_id == "com.apple.music" or app_name in ("apple music", "music"))
    is_spotify = (stream_id == "spotify" or "spotify" in bundle_id or "spotify" in app_name)

    title_matches = False
    if target_title and mr_title:
        if target_title == mr_title or target_title in mr_title or mr_title in target_title:
            title_matches = True

    bundle_matches = False
    if is_apple:
        bundle_matches = ("apple.music" in mr_bundle or mr_bundle == "com.apple.music")
    elif is_spotify:
        bundle_matches = ("spotify" in mr_bundle)
    elif is_yt:
        bundle_matches = ("webkit" in mr_bundle or "webapp" in mr_bundle or "youtube" in mr_bundle or "ytmusic" in mr_bundle)
    else:
        bundle_matches = (
            (bool(bundle_id) and bundle_id in mr_bundle) or
            (bool(app_name) and app_name in mr_bundle) or
            (bool(stream_id) and stream_id in mr_bundle)
        )

    if title_matches and bundle_matches:
        return True

    if title_matches:
        if is_yt and any(x in mr_bundle for x in ["com.apple.music", "spotify", "firefox", "chrome"]):
            return False
        if is_apple and any(x in mr_bundle for x in ["spotify", "firefox", "chrome", "webkit"]):
            return False
        if is_spotify and any(x in mr_bundle for x in ["com.apple.music", "webkit", "firefox", "chrome"]):
            return False
        return True

    if not target_title and bundle_matches:
        return True

    return False

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
            elif action in ("toggleplaypause", "playpause"):
                subprocess.run(["osascript", "-e", 'tell application "Music" to playpause'], timeout=1.0)
                return {"success": True}
            elif action == "play":
                subprocess.run(["osascript", "-e", 'tell application "Music" to play'], timeout=1.0)
                return {"success": True}
            elif action == "pause":
                subprocess.run(["osascript", "-e", 'tell application "Music" to pause'], timeout=1.0)
                return {"success": True}
            elif action == "next":
                reset_progress_state()
                subprocess.run(["osascript", "-e", 'tell application "Music" to next track'], timeout=1.0)
                return {"success": True}
            elif action == "previous":
                reset_progress_state()
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
            if action in ("toggleplaypause", "playpause"):
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to playpause'], timeout=1.0)
                return {"success": True}
            elif action == "play":
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to play'], timeout=1.0)
                return {"success": True}
            elif action == "pause":
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to pause'], timeout=1.0)
                return {"success": True}
            elif action == "next":
                reset_progress_state()
                subprocess.run(["osascript", "-e", 'tell application "Spotify" to next track'], timeout=1.0)
                return {"success": True}
            elif action == "previous":
                reset_progress_state()
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
    tell application process "Web App"
      if (count of windows) is 0 then return "error"
      tell window 1
        set s to first UI element whose role is "AXSplitGroup"
        set tb to first UI element of s whose role is "AXTabGroup"
        set g1 to first UI element of tb whose role is "AXGroup"
        set g2 to first UI element of g1 whose role is "AXGroup"
        set sa to first UI element of g2 whose role is "AXScrollArea"
        set wa to first UI element of sa whose role is "AXWebArea"
        set pb to first UI element of wa whose description is "Player bar"
        if "{action}" is "like" then
          set lkBtn to first UI element of (UI element 14 of pb) whose role is "AXCheckBox"
          set oldVal to value of lkBtn as text
          click lkBtn
          if oldVal is "1" then return "0"
          return "1"
        else
          set dlkBtn to UI element 15 of pb
          set oldVal to value of dlkBtn as text
          click dlkBtn
          if oldVal is "1" then return "0"
          return "1"
        end if
      end tell
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

        elif action in ("toggleplaypause", "playpause", "next", "previous", "play", "pause"):
            if action in ("previous", "next"):
                reset_progress_state()
            script = f'''
tell application "System Events"
  try
    tell application process "Web App"
      if (count of windows) is 0 then return "error"
      tell window 1
        set s to first UI element whose role is "AXSplitGroup"
        set tb to first UI element of s whose role is "AXTabGroup"
        set g1 to first UI element of tb whose role is "AXGroup"
        set g2 to first UI element of g1 whose role is "AXGroup"
        set sa to first UI element of g2 whose role is "AXScrollArea"
        set wa to first UI element of sa whose role is "AXWebArea"
        set pb to first UI element of wa whose description is "Player bar"
        if "{action}" is in {{"toggleplaypause", "playpause", "play", "pause"}} then
          click UI element 4 of pb
        else if "{action}" is "next" then
          click UI element 7 of pb
        else if "{action}" is "previous" then
          click UI element 1 of pb
        end if
      end tell
      return "ok"
    end tell
  on error
    return "error"
  end try
end tell
'''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if res.stdout.strip() == "ok":
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
    if action in ("previous", "next"):
        reset_progress_state()

    stream_id = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    app_name = sys.argv[3].lower() if len(sys.argv) > 3 else ""
    bundle_id = sys.argv[4].lower() if len(sys.argv) > 4 else ""
    track_key = sys.argv[5] if len(sys.argv) > 5 else ""

    is_yt = (stream_id == "ytmusic" or "youtube" in app_name or "yt music" in app_name or "webapp" in bundle_id)
    is_apple = (stream_id == "apple_music" or "apple.music" in bundle_id or bundle_id == "com.apple.music" or app_name in ("apple music", "music"))
    is_spotify = (stream_id == "spotify" or "spotify" in bundle_id or "spotify" in app_name)

    result = {"success": False, "rating": None}

    # Ratings are app-specific (MediaRemote does not handle ratings)
    if action in ("like", "dislike"):
        if is_yt:
            result = control_ytmusic(action)
        elif is_apple:
            result = control_apple_music(action)
        else:
            result = {"success": False, "rating": None}
    else:
        # Playback control: toggleplaypause, next, previous
        mr_data = get_mediaremote_raw()
        matches_mr = stream_matches_mediaremote(mr_data, stream_id, app_name, bundle_id, track_key)

        if matches_mr:
            # Target stream matches the active MediaRemote session.
            # Default to mediaremote for fast, native playback control.
            ok = send_mediaremote_command(action)
            if ok:
                result = {"success": True}
            else:
                # Fallback to app-specific control if MediaRemote fails
                if is_yt:
                    result = control_ytmusic(action)
                elif is_apple:
                    result = control_apple_music(action)
                elif is_spotify:
                    result = control_spotify(action)
        else:
            # Target stream does NOT match the active MediaRemote session.
            # Directly control the target application to prevent hijacking the other player.
            if is_yt:
                result = control_ytmusic(action)
            elif is_apple:
                result = control_apple_music(action)
            elif is_spotify:
                result = control_spotify(action)
            else:
                # Generic stream (browser tab, etc.) that is not currently active in MediaRemote
                result = {"success": False, "rating": None}

    if result.get("success") and result.get("rating") is not None and track_key:
        update_cached_rating(track_key, result["rating"])

    print(json.dumps(result))

if __name__ == "__main__":
    main()
