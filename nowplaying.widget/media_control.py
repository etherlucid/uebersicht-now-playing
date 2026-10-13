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

def control_apple_music(action):
    try:
        check = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to (name of processes) contains "Music"'],
            capture_output=True,
            text=True,
            timeout=1.0
        )
        if "true" in check.stdout.lower():
            if action == "like":
                subprocess.run(
                    ["osascript", "-e", 'tell application "Music" to set favorited of current track to not (favorited of current track)'],
                    capture_output=True,
                    timeout=1.0
                )
            elif action == "dislike":
                subprocess.run(
                    ["osascript", "-e", 'tell application "Music" to set disliked of current track to not (disliked of current track)'],
                    capture_output=True,
                    timeout=1.0
                )
    except Exception:
        pass

def toggle_ytmusic(action):
    script = f'''
tell application "System Events"
  try
    if (name of processes) contains "Web App" then
      set p to process "Web App"
      set w to window 1 of p
      set s to first UI element of w whose role is "AXSplitGroup"
      set tb to first UI element of s whose role is "AXTabGroup"
      set g1 to first UI element of tb whose role is "AXGroup"
      set g2 to first UI element of g1 whose role is "AXGroup"
      set sa to first UI element of g2 whose role is "AXScrollArea"
      set wa to first UI element of sa whose role is "AXWebArea"
      set playerBar to first UI element of wa whose description is "Player bar"
      if "{action}" is "like" then
        try
          set btn to first UI element of playerBar whose description is "Like"
          click btn
        on error
          set btn to first checkbox of UI element 18 of playerBar
          click btn
        end try
      else
        try
          set btn to first UI element of playerBar whose description is "Dislike"
          click btn
        on error
          set btn to UI element 19 of playerBar
          click btn
        end try
      end if
    end if
  on error
  end try
end tell
'''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.5)
    except Exception:
        pass

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
        return

    action = sys.argv[1].lower()
    track_key = sys.argv[2] if len(sys.argv) > 2 else ""
    new_rating = sys.argv[3] if len(sys.argv) > 3 else action

    if action in ("like", "dislike"):
        # 1. Toggle in YouTube Music if running
        toggle_ytmusic(action)
        # 2. Toggle in Apple Music if running
        control_apple_music(action)
        # 3. Send MediaRemote command
        cmd_id = 106 if action == "like" else 107
        send_mediaremote_command(cmd_id)
        # 4. Update rating cache
        update_cached_rating(track_key, new_rating)

if __name__ == "__main__":
    main()
