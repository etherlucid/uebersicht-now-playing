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
    if rating:
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

    if action == "like":
        # kMRLikeTrack = 106 (0x6A)
        send_mediaremote_command(106)
        control_apple_music("like")
        update_cached_rating(track_key, new_rating if new_rating in ("liked", "none") else "liked")
    elif action == "dislike":
        # kMRBanTrack = 107 (0x6B)
        send_mediaremote_command(107)
        control_apple_music("dislike")
        update_cached_rating(track_key, new_rating if new_rating in ("disliked", "none") else "disliked")

if __name__ == "__main__":
    main()
