#!/usr/bin/env python3
import sys
import os
import json
import base64
import subprocess
import shutil
import time
import hashlib
import re
import urllib.request
import urllib.parse

CACHE_TRACK_FILE = "/tmp/nowplaying_track.txt"
CACHE_ART_FILE = "/tmp/nowplaying_art_data.txt"
CACHE_STATE_FILE = "/tmp/nowplaying_state.json"
CACHE_STREAMS_FILE = "/tmp/nowplaying_streams_cache_v5.json"
CACHE_RATINGS_FILE = "/tmp/nowplaying_ratings.json"
CACHE_ART_DIR = "/tmp/nowplaying_art_cache_v5"
CACHE_YTMUSIC_ART_FILE = "/tmp/nowplaying_ytmusic_art_v5.txt"
CACHE_APP_ICON_DIR = "/tmp/nowplaying_app_icons_v5"
CACHE_APP_ICON_SCRIPT = "/tmp/nowplaying_get_app_icon_v5.js"
CACHE_BG_PLAYERS_FILE = "/tmp/nowplaying_bg_players_v5.json"
CACHE_BG_PLAYERS_LOCK = "/tmp/nowplaying_bg_players_v5.lock"
CACHE_FETCH_LOCK_DIR = "/tmp/nowplaying_fetch_locks_v5"

_APP_ICON_MEM_CACHE = {}

JXA_APP_ICON_SCRIPT_CODE = '''ObjC.import("AppKit");

function run(argv) {
    var bundleId = argv[0] || "";
    var appName = argv[1] || "";

    var ws = $.NSWorkspace.sharedWorkspace;
    var fm = $.NSFileManager.defaultManager;
    var appPath = null;

    function checkPath(p) {
        if (!p) return null;
        var str = ObjC.unwrap(p);
        if (fm.fileExistsAtPath(str)) return str;
        return null;
    }

    var lowerB = bundleId.toLowerCase();
    if (bundleId && lowerB.indexOf("webkit") === -1 && lowerB.indexOf("mediaremote") === -1) {
        var url = ws.URLForApplicationWithBundleIdentifier(bundleId);
        if (url && url.path) {
            appPath = checkPath(url.path);
        }
    }

    if (!appPath && appName) {
        try {
            var p = ws.fullPathForApplication(appName);
            if (p) appPath = checkPath(p);
        } catch(e) {}
    }

    if (!appPath && appName) {
        var home = ObjC.unwrap($.NSHomeDirectory());
        var dirs = [
            "/Applications",
            "/System/Applications",
            home + "/Applications",
            "/System/Volumes/Preboot/Cryptexes/App/System/Applications"
        ];
        var candidates = [appName, appName + ".app"];
        var lower = appName.toLowerCase();
        if (lower.indexOf("youtube") !== -1 || lower.indexOf("yt") !== -1) {
            candidates.push("YT Music.app", "YouTube Music.app");
        } else if (lower.indexOf("apple") !== -1 && lower.indexOf("music") !== -1) {
            candidates.push("Music.app");
        }
        for (var i = 0; i < dirs.length; i++) {
            for (var j = 0; j < candidates.length; j++) {
                var testP = dirs[i] + "/" + candidates[j];
                if (fm.fileExistsAtPath(testP)) {
                    appPath = testP;
                    break;
                }
            }
            if (appPath) break;
        }
    }

    if (!appPath) return "NONE";

    var icon = ws.iconForFile(appPath);
    if (!icon) return "NONE";

    var size = 64;
    var rep = $.NSBitmapImageRep.alloc.initWithBitmapDataPlanesPixelsWidePixelsHighBitsPerSampleSamplesPerPixelHasAlphaIsPlanarColorSpaceNameBytesPerRowBitsPerPixel(
        null, size, size, 8, 4, true, false, $.NSDeviceRGBColorSpace, 0, 0
    );
    $.NSGraphicsContext.saveGraphicsState;
    var ctx = $.NSGraphicsContext.graphicsContextWithBitmapImageRep(rep);
    $.NSGraphicsContext.setCurrentContext(ctx);
    icon.drawInRectFromRectOperationFraction(
        $.NSMakeRect(0, 0, size, size),
        $.NSZeroRect,
        $.NSCompositingOperationCopy,
        1.0
    );
    $.NSGraphicsContext.restoreGraphicsState;

    var pngData = rep.representationUsingTypeProperties($.NSBitmapImageFileTypePNG, $({}));
    if (!pngData) return "NONE";
    var b64 = pngData.base64EncodedStringWithOptions(0);
    return "data:image/png;base64," + ObjC.unwrap(b64);
}
'''


def ensure_dirs():
    for d in (CACHE_ART_DIR, CACHE_APP_ICON_DIR, CACHE_FETCH_LOCK_DIR):
        if not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass


def get_app_icon(bundle_id, app_name):
    bundle_id = (bundle_id or "").strip()
    app_name = (app_name or "").strip()
    if not bundle_id and not app_name:
        return ""

    lower_b = bundle_id.lower()
    norm_b = "" if ("webkit" in lower_b or "mediaremote" in lower_b) else lower_b
    cache_key = f"{norm_b}___{app_name.lower()}"
    if cache_key in _APP_ICON_MEM_CACHE:
        return _APP_ICON_MEM_CACHE[cache_key]

    ensure_dirs()
    key_hash = hashlib.md5(cache_key.encode("utf-8", errors="ignore")).hexdigest()
    cache_file = os.path.join(CACHE_APP_ICON_DIR, f"{key_hash}.txt")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                val = f.read().strip()
            if val == "NONE":
                if (time.time() - os.path.getmtime(cache_file)) < 3600:
                    _APP_ICON_MEM_CACHE[cache_key] = ""
                    return ""
            elif val.startswith("data:image/"):
                _APP_ICON_MEM_CACHE[cache_key] = val
                return val
        except Exception:
            pass

    if not os.path.exists(CACHE_APP_ICON_SCRIPT):
        try:
            with open(CACHE_APP_ICON_SCRIPT, "w") as f:
                f.write(JXA_APP_ICON_SCRIPT_CODE)
        except Exception:
            pass

    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", CACHE_APP_ICON_SCRIPT, bundle_id, app_name],
            capture_output=True,
            text=True,
            timeout=1.2
        )
        out = proc.stdout.strip()
        if out.startswith("data:image/png;base64,"):
            try:
                with open(cache_file, "w") as f:
                    f.write(out)
            except Exception:
                pass
            _APP_ICON_MEM_CACHE[cache_key] = out
            return out
    except Exception:
        pass

    try:
        with open(cache_file, "w") as f:
            f.write("NONE")
    except Exception:
        pass
    _APP_ICON_MEM_CACHE[cache_key] = ""
    return ""


def find_nowplaying_cli():
    for p in ("/opt/homebrew/bin/nowplaying-cli", "/usr/local/bin/nowplaying-cli"):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    which_p = shutil.which("nowplaying-cli")
    return which_p or "/opt/homebrew/bin/nowplaying-cli"


def get_nowplaying_data():
    cli = find_nowplaying_cli()
    if not os.path.exists(cli):
        return None
    try:
        proc = subprocess.run(
            [cli, "get-raw"],
            capture_output=True,
            text=True,
            timeout=0.8
        )
        stdout = proc.stdout.strip()
        if not stdout or stdout == "null":
            return None
        return json.loads(stdout)
    except Exception:
        return None


def detect_mime(data_bytes):
    if not data_bytes:
        return None
    if data_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if data_bytes.startswith(b"GIF8"):
        return "image/gif"
    if data_bytes.startswith(b"RIFF") and b"WEBP" in data_bytes[:16]:
        return "image/webp"
    return None


def bytes_to_data_url(art_bytes):
    if not art_bytes:
        return ""
    mime = detect_mime(art_bytes)
    if mime and len(art_bytes) <= 300000:
        b64 = base64.b64encode(art_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"

    # Convert TIFF or oversized image to compact high-quality JPEG via sips
    pid = os.getpid()
    tmp_in = f"/tmp/np_art_in_{pid}.img"
    tmp_out = f"/tmp/np_art_out_{pid}.jpg"
    try:
        with open(tmp_in, "wb") as f:
            f.write(art_bytes)
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85", "-Z", "600", tmp_in, "--out", tmp_out],
            capture_output=True,
            timeout=1.0
        )
        if os.path.exists(tmp_out):
            with open(tmp_out, "rb") as f:
                jpg_bytes = f.read()
            if jpg_bytes:
                b64 = base64.b64encode(jpg_bytes).decode("ascii")
                return f"data:image/jpeg;base64,{b64}"
    except Exception:
        pass
    finally:
        for p in (tmp_in, tmp_out):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    if mime:
        b64 = base64.b64encode(art_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"
    return ""


def download_and_encode_image(url, timeout=2.0):
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if not data:
                return ""
            return bytes_to_data_url(data)
    except Exception:
        return ""


def fetch_online_artwork(artist, title):
    if not title:
        return ""

    clean_artist = re.sub(r'(\s*[-•]\s*Topic|\s*Topic\b)', '', artist or '', flags=re.I).strip()
    clean_title = re.sub(r'(\(Official.*?\)|\[Official.*?\]|\(Audio\)|\[Audio\])', '', title or '', flags=re.I).strip()
    query = f"{clean_artist} {clean_title}".strip() or clean_title or title or ""
    if not query:
        return ""

    # Tier 1: iTunes Search API
    try:
        url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
            "term": query,
            "media": "music",
            "limit": "1"
        })
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                raw_url = results[0].get("artworkUrl100", "")
                if raw_url:
                    high_res = raw_url.replace("100x100bb", "600x600bb").replace("100x100", "600x600")
                    b64_data = download_and_encode_image(high_res, timeout=1.5)
                    if b64_data:
                        return b64_data
    except Exception:
        pass

    # Tier 2: Deezer Search API
    try:
        url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            if items:
                img_url = items[0].get("album", {}).get("cover_xl") or items[0].get("album", {}).get("cover_big")
                b64_data = download_and_encode_image(img_url, timeout=1.5)
                if b64_data:
                    return b64_data
    except Exception:
        pass

    # Tier 3: YouTube Search
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            vids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
            if vids:
                thumb_url = f"https://i.ytimg.com/vi/{vids[0]}/hqdefault.jpg"
                b64_data = download_and_encode_image(thumb_url, timeout=2.0)
                if b64_data:
                    return b64_data
    except Exception:
        pass

    return ""


def get_canonical_track_hash(artist, title, track_key=""):
    t = (title or "").strip().lower()
    a = (artist or "").strip().lower()
    base = f"{t}___{a}" if t else (track_key or "").strip().lower()
    return hashlib.md5(base.encode("utf-8", errors="ignore")).hexdigest()


def read_cached_data_url(path):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r") as f:
            val = f.read().strip()
        if val.startswith("data:image/") or val.startswith("http://") or val.startswith("https://"):
            return val
    except Exception:
        pass
    return ""


def write_cached_data_url(path, val):
    if not path or not val:
        return
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            f.write(val)
        os.replace(tmp, path)
    except Exception:
        pass


def spawn_background_art_fetch(artist, title, track_hash):
    ensure_dirs()
    lock_file = os.path.join(CACHE_FETCH_LOCK_DIR, f"{track_hash}.lock")
    if os.path.exists(lock_file):
        try:
            if (time.time() - os.path.getmtime(lock_file)) < 15:
                return
        except Exception:
            pass
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--fetch-art", artist or "", title or "", track_hash],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True
        )
    except Exception:
        pass


def run_fetch_art_worker(artist, title, track_hash):
    ensure_dirs()
    lock_file = os.path.join(CACHE_FETCH_LOCK_DIR, f"{track_hash}.lock")
    direct_file = os.path.join(CACHE_ART_DIR, f"direct_{track_hash}.txt")
    fallback_file = os.path.join(CACHE_ART_DIR, f"fallback_{track_hash}.txt")
    no_art_file = os.path.join(CACHE_ART_DIR, f"no_art_{track_hash}.txt")

    try:
        # Never fetch online artwork if direct media player artwork already exists
        if read_cached_data_url(direct_file):
            return
        online_art = fetch_online_artwork(artist, title)
        if online_art:
            write_cached_data_url(fallback_file, online_art)
        else:
            with open(no_art_file, "w") as f:
                f.write("none")
    except Exception:
        pass
    finally:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception:
            pass


def process_artwork(data, track_key, artist="", title=""):
    if not track_key and not title:
        return ""

    ensure_dirs()
    track_hash = get_canonical_track_hash(artist, title, track_key)
    direct_file = os.path.join(CACHE_ART_DIR, f"direct_{track_hash}.txt")
    fallback_file = os.path.join(CACHE_ART_DIR, f"fallback_{track_hash}.txt")
    no_art_file = os.path.join(CACHE_ART_DIR, f"no_art_{track_hash}.txt")

    # 1. HIGHEST PRIORITY: Direct artwork from the media player (MediaRemote kMRMediaRemoteNowPlayingInfoArtworkData)
    raw_art = data.get("kMRMediaRemoteNowPlayingInfoArtworkData") if data else None
    if raw_art and isinstance(raw_art, str):
        raw_clean = "".join(raw_art.split())
        if raw_clean:
            raw_sig = f"{raw_clean[:512]}_{len(raw_clean)}_{ raw_clean[-256:] if len(raw_clean) > 256 else '' }"
            raw_hash = hashlib.md5(raw_sig.encode("ascii", errors="ignore")).hexdigest()
            raw_cache_file = os.path.join(CACHE_ART_DIR, f"raw_{raw_hash}.txt")

            cached_raw = read_cached_data_url(raw_cache_file)
            if cached_raw:
                if not os.path.exists(direct_file):
                    write_cached_data_url(direct_file, cached_raw)
                return cached_raw

            try:
                art_bytes = base64.b64decode(raw_clean)
                data_url = bytes_to_data_url(art_bytes)
                if data_url:
                    write_cached_data_url(raw_cache_file, data_url)
                    write_cached_data_url(direct_file, data_url)
                    b_id = (data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or "").lower() if data else ""
                    if "webapp" in b_id or "safari" in b_id or "webkit" in b_id:
                        write_cached_data_url(CACHE_YTMUSIC_ART_FILE, data_url)
                    return data_url
            except Exception:
                pass

    # 2. Cached direct artwork previously provided by the media player for this track
    cached_direct = read_cached_data_url(direct_file)
    if cached_direct:
        return cached_direct

    # 3. Cached fallback online artwork (only used when media player provided no artwork)
    cached_fallback = read_cached_data_url(fallback_file)
    if cached_fallback:
        return cached_fallback

    # 4. Trigger non-blocking online fallback ONLY if media player provided no artwork
    if title:
        can_try_online = True
        if os.path.exists(no_art_file):
            try:
                if (time.time() - os.path.getmtime(no_art_file)) < 300:
                    can_try_online = False
            except Exception:
                pass
        if can_try_online:
            spawn_background_art_fetch(artist, title, track_hash)

    return ""


def is_process_running(proc_name):
    try:
        res = subprocess.run(["pgrep", "-x", proc_name], capture_output=True, timeout=0.3)
        return res.returncode == 0
    except Exception:
        return False


def get_app_name(bundle_id):
    if not bundle_id:
        return "macOS Audio"
    b = bundle_id.lower()
    if "spotify" in b:
        return "Spotify"
    if "apple.music" in b or "itunes" in b:
        return "Apple Music"
    if "safari.webapp" in b:
        return "YouTube Music"
    if "safari" in b:
        return "Safari"
    if "chrome" in b:
        return "Google Chrome"
    if "firefox" in b:
        return "Firefox"
    if "webkit" in b:
        if is_process_running("Web App"):
            return "YouTube Music"
        return "Web Audio"
    if "iina" in b:
        return "IINA"
    if "vlc" in b:
        return "VLC"
    return "macOS Audio"


def calculate_progress(track_key, raw_elapsed, duration, playback_rate):
    now = time.time()
    state = {}
    if os.path.exists(CACHE_STATE_FILE):
        try:
            with open(CACHE_STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {}

    saved_track = state.get("track_id", "")
    saved_anchor_elapsed = float(state.get("anchor_elapsed", 0.0))
    saved_anchor_time = float(state.get("anchor_time", now))
    saved_raw_elapsed = float(state.get("last_raw_elapsed", 0.0))
    saved_rate = int(state.get("last_rate", 1))
    last_updated = float(state.get("last_updated", now))

    is_new_track = (track_key != saved_track)

    if is_new_track:
        anchor_elapsed = raw_elapsed
        anchor_time = now
        last_raw_elapsed = raw_elapsed
        current_elapsed = anchor_elapsed
    else:
        gap = now - last_updated
        if gap > 30.0:
            if abs(raw_elapsed - saved_raw_elapsed) > 0.05:
                anchor_elapsed = raw_elapsed
                anchor_time = now
                last_raw_elapsed = raw_elapsed
                current_elapsed = raw_elapsed
            else:
                anchor_elapsed = saved_anchor_elapsed
                anchor_time = now
                last_raw_elapsed = raw_elapsed
                current_elapsed = saved_anchor_elapsed
        elif playback_rate == 0:
            if saved_rate == 1:
                elapsed_so_far = saved_anchor_elapsed + max(0.0, now - saved_anchor_time)
                current_elapsed = elapsed_so_far
                anchor_elapsed = elapsed_so_far
                anchor_time = now
                last_raw_elapsed = raw_elapsed
            else:
                if abs(raw_elapsed - saved_raw_elapsed) > 0.5:
                    anchor_elapsed = raw_elapsed
                    anchor_time = now
                    last_raw_elapsed = raw_elapsed
                    current_elapsed = raw_elapsed
                else:
                    current_elapsed = saved_anchor_elapsed
                    anchor_elapsed = saved_anchor_elapsed
                    anchor_time = now
                    last_raw_elapsed = raw_elapsed
        else:
            if saved_rate == 0:
                if abs(raw_elapsed - saved_raw_elapsed) > 0.5:
                    anchor_elapsed = raw_elapsed
                else:
                    anchor_elapsed = saved_anchor_elapsed
                anchor_time = now
                last_raw_elapsed = raw_elapsed
                current_elapsed = anchor_elapsed
            else:
                calculated_elapsed = saved_anchor_elapsed + max(0.0, now - saved_anchor_time)
                if abs(raw_elapsed - saved_raw_elapsed) > 0.05:
                    anchor_elapsed = raw_elapsed
                    anchor_time = now
                    last_raw_elapsed = raw_elapsed
                    current_elapsed = raw_elapsed
                else:
                    current_elapsed = calculated_elapsed
                    anchor_elapsed = saved_anchor_elapsed
                    anchor_time = saved_anchor_time
                    last_raw_elapsed = saved_raw_elapsed

    if duration > 0:
        current_elapsed = min(duration, max(0.0, current_elapsed))
    else:
        current_elapsed = max(0.0, current_elapsed)

    new_state = {
        "track_id": track_key,
        "anchor_elapsed": anchor_elapsed,
        "anchor_time": anchor_time,
        "last_raw_elapsed": last_raw_elapsed,
        "last_rate": playback_rate,
        "last_updated": now
    }
    try:
        with open(CACHE_STATE_FILE, "w") as f:
            json.dump(new_state, f)
    except Exception:
        pass

    return current_elapsed


def get_ytmusic_direct_stream():
    if not is_process_running("Web App"):
        return None
    script = '''
tell application "System Events"
  try
    tell application process "Web App"
      if (count of windows) is 0 then return "none"
      tell window 1
        set winTitle to name
        set s to first UI element whose role is "AXSplitGroup"
        set tb to first UI element of s whose role is "AXTabGroup"
        set g1 to first UI element of tb whose role is "AXGroup"
        set g2 to first UI element of g1 whose role is "AXGroup"
        set sa to first UI element of g2 whose role is "AXScrollArea"
        set wa to first UI element of sa whose role is "AXWebArea"
        set pb to first UI element of wa whose description is "Player bar"
        
        set t to ""
        try
          set hdgs to every UI element of pb whose role is "AXHeading"
          if (count of hdgs) > 0 then
            set t to title of item 1 of hdgs as text
          end if
        end try
        
        set lnks to every UI element of pb whose role is "AXLink"
        set a to ""
        set al to ""
        if (count of lnks) > 0 then
          set a to title of item 1 of lnks
          if (count of lnks) > 1 then
            set al to title of item 2 of lnks
          end if
        end if
        if a is "" then
          try
            set a to value of UI element 13 of pb
          end try
        end if
        
        set tm to ""
        try
          set tmEl to first UI element of pb whose (role is "AXStaticText" and value contains " / ")
          set tm to value of tmEl as text
        end try
        
        set pp to "Play"
        try
          set ppBtn to first UI element of pb whose (role is "AXButton" and (title is in {"Play", "Pause"} or description is in {"Play", "Pause"}))
          set pp to description of ppBtn as text
          if pp is "" then set pp to title of ppBtn as text
        end try
        
        set lk to "0"
        set dlk to "0"
        try
          set els to UI elements of pb
          set c to count of els
          repeat with i from 14 to c
            set el to item i of els
            if role of el is "AXCheckBox" then
              set dlk to value of el as text
              try
                set lk to value of (first UI element of (item (i - 1) of els)) as text
              end try
              exit repeat
            end if
          end repeat
        end try
        
        return (t & "|||" & a & "|||" & tm & "|||" & pp & "|||" & lk & "|||" & dlk & "|||" & winTitle & "|||" & al)
      end tell
    end tell
  on error
    return "none"
  end try
end tell
'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.2)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            title = parts[0].strip()
            artist = parts[1].strip() if len(parts) > 1 else ""
            time_str = parts[2].strip() if len(parts) > 2 else ""
            pp_title = parts[3].strip() if len(parts) > 3 else "Play"
            lk_val = parts[4].strip() if len(parts) > 4 else "0"
            dlk_val = parts[5].strip() if len(parts) > 5 else "0"
            album = parts[7].strip() if len(parts) > 7 else ""

            if not title:
                win_title = parts[6].strip() if len(parts) > 6 else ""
                if " | YouTube Music" in win_title:
                    title = win_title.replace(" | YouTube Music", "").strip()

            if not title:
                return None

            elapsed = 0.0
            duration = 0.0
            if " / " in time_str:
                e_str, d_str = time_str.split(" / ", 1)
                try:
                    e_parts = [float(x) for x in e_str.split(":")]
                    elapsed = e_parts[0] * 60 + e_parts[1] if len(e_parts) == 2 else e_parts[0]
                    d_parts = [float(x) for x in d_str.split(":")]
                    duration = d_parts[0] * 60 + d_parts[1] if len(d_parts) == 2 else d_parts[0]
                except Exception:
                    pass

            rate = 1 if pp_title.lower() == "pause" else 0
            rating = "liked" if lk_val == "1" else ("disliked" if dlk_val == "1" else None)

            yt_art_key = f"{title}___{artist}___"
            artwork_url = process_artwork({}, yt_art_key, artist, title)

            return {
                "id": "ytmusic",
                "title": title,
                "artist": artist,
                "album": album,
                "duration": round(duration, 1),
                "elapsed": round(elapsed, 1),
                "rate": rate,
                "artwork": artwork_url,
                "bundleId": "com.apple.Safari.WebApp.F5D92F4A-8F5E-4368-A535-047D3666F565",
                "appName": "YouTube Music",
                "rating": rating,
                "supportsRating": True,
                "updatedAt": round(time.time(), 3)
            }
    except Exception:
        pass
    return None


def get_apple_music_stream():
    if not is_process_running("Music"):
        return None
    script = '''
tell application "System Events"
  if (name of processes) contains "Music" then
    tell application "Music"
      set pState to player state as text
      set tName to name of current track
      set tArtist to artist of current track
      set tAlbum to album of current track
      set tDur to duration of current track
      set tPos to player position
      set tFav to favorited of current track
      set tDis to disliked of current track
      return (pState & "|||" & tName & "|||" & tArtist & "|||" & tAlbum & "|||" & (tDur as text) & "|||" & (tPos as text) & "|||" & (tFav as text) & "|||" & (tDis as text))
    end tell
  end if
  return "none"
end tell
'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.0)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            p_state = parts[0].lower()
            name = parts[1].strip()
            artist = parts[2].strip()
            album = parts[3].strip()
            duration = float(parts[4]) if parts[4] else 0.0
            pos = float(parts[5]) if parts[5] else 0.0
            fav = parts[6].lower() == "true"
            dis = parts[7].lower() == "true"
            rating = "liked" if fav else ("disliked" if dis else None)
            rate = 1 if p_state == "playing" else 0

            art_url = ""
            if name:
                am_art_key = f"{name}___{artist}___{album}"
                art_url = process_artwork({}, am_art_key, artist, name)

            return {
                "id": "apple_music",
                "title": name,
                "artist": artist,
                "album": album,
                "duration": round(duration, 1),
                "elapsed": round(pos, 1),
                "rate": rate,
                "artwork": art_url,
                "bundleId": "com.apple.Music",
                "appName": "Apple Music",
                "rating": rating,
                "supportsRating": True,
                "updatedAt": round(time.time(), 3)
            }
    except Exception:
        pass
    return None


def get_spotify_stream():
    if not is_process_running("Spotify"):
        return None
    script = '''
tell application "System Events"
  if (name of processes) contains "Spotify" then
    tell application "Spotify"
      set pState to player state as text
      set tName to name of current track
      set tArtist to artist of current track
      set tAlbum to album of current track
      set tDur to (duration of current track) / 1000
      set tPos to player position
      set tArt to artwork url of current track
      return (pState & "|||" & tName & "|||" & tArtist & "|||" & tAlbum & "|||" & (tDur as text) & "|||" & (tPos as text) & "|||" & tArt)
    end tell
  end if
  return "none"
end tell
'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.0)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            p_state = parts[0].lower()
            name = parts[1].strip()
            artist = parts[2].strip()
            album = parts[3].strip()
            duration = float(parts[4]) if parts[4] else 0.0
            pos = float(parts[5]) if parts[5] else 0.0
            art_url = parts[6].strip() if len(parts) > 6 else ""
            rate = 1 if p_state == "playing" else 0

            return {
                "id": "spotify",
                "title": name,
                "artist": artist,
                "album": album,
                "duration": round(duration, 1),
                "elapsed": round(pos, 1),
                "rate": rate,
                "artwork": art_url,
                "bundleId": "com.spotify.client",
                "appName": "Spotify",
                "rating": None,
                "supportsRating": False,
                "updatedAt": round(time.time(), 3)
            }
    except Exception:
        pass
    return None


def run_poll_players_worker():
    try:
        result = {"ts": time.time(), "players": {}}
        if is_process_running("Web App"):
            yt = get_ytmusic_direct_stream()
            if yt:
                result["players"]["ytmusic"] = yt
        if is_process_running("Music"):
            am = get_apple_music_stream()
            if am:
                result["players"]["apple_music"] = am
        if is_process_running("Spotify"):
            sp = get_spotify_stream()
            if sp:
                result["players"]["spotify"] = sp
        tmp_path = f"{CACHE_BG_PLAYERS_FILE}.tmp.{os.getpid()}"
        with open(tmp_path, "w") as f:
            json.dump(result, f)
        os.replace(tmp_path, CACHE_BG_PLAYERS_FILE)
    except Exception:
        pass
    finally:
        try:
            if os.path.exists(CACHE_BG_PLAYERS_LOCK):
                os.remove(CACHE_BG_PLAYERS_LOCK)
        except Exception:
            pass


def get_cached_bg_players():
    now = time.time()
    data = {}
    need_refresh = True
    if os.path.exists(CACHE_BG_PLAYERS_FILE):
        try:
            with open(CACHE_BG_PLAYERS_FILE, "r") as f:
                parsed = json.load(f)
            age = now - float(parsed.get("ts", 0))
            if age < 15.0:
                data = parsed.get("players", {})
            if age < 3.0:
                need_refresh = False
        except Exception:
            pass

    if need_refresh:
        lock_active = False
        if os.path.exists(CACHE_BG_PLAYERS_LOCK):
            try:
                if (now - os.path.getmtime(CACHE_BG_PLAYERS_LOCK)) < 5.0:
                    lock_active = True
            except Exception:
                pass
        if not lock_active:
            try:
                with open(CACHE_BG_PLAYERS_LOCK, "w") as f:
                    f.write(str(os.getpid()))
                subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), "--poll-players"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    start_new_session=True
                )
            except Exception:
                pass

    return data


def is_app_running(bundle_id, app_name):
    target = f"{bundle_id} {app_name}".lower()
    if "firefox" in target:
        return is_process_running("firefox") or is_process_running("Firefox")
    if "spotify" in target:
        return is_process_running("Spotify")
    if "apple.music" in target or app_name.lower() == "music" or "itunes" in target:
        return is_process_running("Music")
    if "webapp" in target or "ytmusic" in target or "youtube" in target:
        return is_process_running("Web App")
    if "chrome" in target:
        return is_process_running("Google Chrome")
    if "safari" in target:
        return is_process_running("Safari")
    return True


def is_dedicated_music_app(stream):
    app_name = (stream.get("appName") or "").lower()
    bundle_id = (stream.get("bundleId") or "").lower()
    stream_id = (stream.get("id") or "").lower()
    music_keywords = ("youtube music", "ytmusic", "spotify", "apple music", "music", "itunes", "tidal", "deezer", "qobuz", "pandora", "soundcloud", "bandcamp")
    for kw in music_keywords:
        if kw in app_name or kw in bundle_id or kw in stream_id:
            return True
    return False


def stream_sort_key(s):
    is_playing = 100 if s.get("rate") == 1 else 0
    music_bias = 10 if is_dedicated_music_app(s) else 0
    has_rich_meta = 2 if (s.get("artist") or s.get("artwork")) else 0
    recency = float(s.get("updatedAt", 0))
    return (is_playing, music_bias, has_rich_meta, recency)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--fetch-art" and len(sys.argv) >= 5:
            run_fetch_art_worker(sys.argv[2], sys.argv[3], sys.argv[4])
            return
        elif sys.argv[1] == "--poll-players":
            run_poll_players_worker()
            return

    now = time.time()
    streams_map = {}

    if os.path.exists(CACHE_STREAMS_FILE):
        try:
            with open(CACHE_STREAMS_FILE, "r") as f:
                cached = json.load(f)
                for s in cached:
                    b_id = s.get("bundleId", "")
                    app_n = s.get("appName", "")
                    if is_dedicated_music_app(s) and is_app_running(b_id, app_n):
                        streams_map[s["id"]] = s
        except Exception:
            streams_map = {}

    # 1. Fast primary MediaRemote NowPlaying query (~35ms)
    mr_data = get_nowplaying_data()
    primary_stream = None

    if mr_data:
        title = mr_data.get("kMRMediaRemoteNowPlayingInfoTitle") or ""
        if title and title != "null":
            artist = mr_data.get("kMRMediaRemoteNowPlayingInfoArtist") or ""
            if artist == "null":
                artist = ""
            album = mr_data.get("kMRMediaRemoteNowPlayingInfoAlbum") or ""
            if album == "null":
                album = ""

            duration = float(mr_data.get("kMRMediaRemoteNowPlayingInfoDuration") or 0)
            raw_elapsed = float(mr_data.get("kMRMediaRemoteNowPlayingInfoElapsedTime") or 0)
            playback_rate = int(mr_data.get("kMRMediaRemoteNowPlayingInfoPlaybackRate") or 0)
            bundle_id = mr_data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or ""
            uid = mr_data.get("kMRMediaRemoteNowPlayingInfoUniqueIdentifier") or ""

            b_lower = bundle_id.lower()
            if "safari.webapp" in b_lower or ("webkit" in b_lower and is_process_running("Web App")):
                app_name = "YouTube Music"
                stream_id = "ytmusic"
                supports_rating = True
            elif "apple.music" in b_lower:
                app_name = "Apple Music"
                stream_id = "apple_music"
                supports_rating = True
            elif "spotify" in b_lower:
                app_name = "Spotify"
                stream_id = "spotify"
                supports_rating = False
            elif "safari" in b_lower:
                app_name = "Safari"
                stream_id = "safari"
                supports_rating = False
            elif "chrome" in b_lower:
                app_name = "Google Chrome"
                stream_id = "chrome"
                supports_rating = False
            elif "firefox" in b_lower:
                app_name = "Firefox"
                stream_id = "firefox"
                supports_rating = False
            else:
                app_name = get_app_name(bundle_id)
                stream_id = bundle_id if bundle_id else "mediaremote"
                supports_rating = False

            art_track_key = f"{title}___{artist}___{album}"
            progress_track_key = f"{uid}___{title}___{artist}___{round(duration, 1)}"
            artwork_url = process_artwork(mr_data, art_track_key, artist, title)
            current_elapsed = calculate_progress(progress_track_key, raw_elapsed, duration, playback_rate)

            primary_stream = {
                "id": stream_id,
                "title": title,
                "artist": artist,
                "album": album,
                "duration": round(duration, 1),
                "elapsed": round(current_elapsed, 1),
                "rate": playback_rate,
                "artwork": artwork_url,
                "bundleId": bundle_id,
                "appName": app_name,
                "rating": None,
                "supportsRating": supports_rating,
                "updatedAt": round(now, 3)
            }
            streams_map[stream_id] = primary_stream

    # 2. Merge non-blocking background player state (YouTube Music, Apple Music, Spotify)
    bg_players = get_cached_bg_players()

    for pid, p_stream in bg_players.items():
        if not p_stream or not p_stream.get("title"):
            continue
        if pid in streams_map:
            existing = streams_map[pid]
            # Always prefer MediaRemote's direct artwork over background fallback
            if existing.get("artwork"):
                p_stream["artwork"] = existing["artwork"]
            elif p_stream.get("artwork"):
                existing["artwork"] = p_stream["artwork"]
            if existing.get("album") and not p_stream.get("album"):
                p_stream["album"] = existing["album"]
            if existing.get("bundleId"):
                p_stream["bundleId"] = existing["bundleId"]
            if existing.get("artist") and existing.get("artist") != existing.get("title"):
                p_stream["artist"] = existing["artist"]

            if primary_stream and primary_stream.get("id") == pid:
                if p_stream.get("rating") is not None:
                    primary_stream["rating"] = p_stream["rating"]
                if p_stream.get("artwork") and not primary_stream.get("artwork"):
                    primary_stream["artwork"] = p_stream["artwork"]
                if p_stream.get("duration") and not primary_stream.get("duration"):
                    primary_stream["duration"] = p_stream["duration"]
            else:
                streams_map[pid] = p_stream
        else:
            b_id = p_stream.get("bundleId", "")
            app_n = p_stream.get("appName", "")
            if is_app_running(b_id, app_n):
                streams_map[pid] = p_stream

    # Filter out dead streams
    active_streams = []
    for s_id, s in streams_map.items():
        if not s.get("title") or s.get("title") == "null":
            continue
        if not is_dedicated_music_app(s):
            if not (primary_stream and primary_stream.get("id") == s_id):
                continue
        if not s.get("artwork"):
            art_url = process_artwork(None, f"{s.get('title','')}___{s.get('artist','')}___{s.get('album','')}", s.get("artist", ""), s.get("title", ""))
            if art_url:
                s["artwork"] = art_url
        active_streams.append(s)

    active_streams.sort(key=stream_sort_key, reverse=True)

    for s in active_streams:
        s["appIcon"] = get_app_icon(s.get("bundleId", ""), s.get("appName", ""))

    try:
        with open(CACHE_STREAMS_FILE, "w") as f:
            json.dump(active_streams, f)
    except Exception:
        pass

    if not active_streams:
        if os.path.exists(CACHE_STATE_FILE):
            try:
                os.remove(CACHE_STATE_FILE)
            except Exception:
                pass
        print(json.dumps({"playing": False, "streams": []}))
        return

    main_stream = active_streams[0]
    result = {
        "playing": any(s.get("rate") == 1 for s in active_streams),
        "streams": active_streams,
        "title": main_stream.get("title", ""),
        "artist": main_stream.get("artist", ""),
        "album": main_stream.get("album", ""),
        "duration": main_stream.get("duration", 0),
        "elapsed": main_stream.get("elapsed", 0),
        "rate": main_stream.get("rate", 0),
        "artwork": main_stream.get("artwork", ""),
        "bundleId": main_stream.get("bundleId", ""),
        "appName": main_stream.get("appName", ""),
        "appIcon": main_stream.get("appIcon", ""),
        "rating": main_stream.get("rating"),
        "supportsRating": main_stream.get("supportsRating", False),
        "updatedAt": main_stream.get("updatedAt", now)
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
