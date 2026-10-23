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
CACHE_STREAMS_FILE = "/tmp/nowplaying_streams_cache.json"
CACHE_RATINGS_FILE = "/tmp/nowplaying_ratings.json"
CACHE_ART_DIR = "/tmp/nowplaying_art_cache_v2"
CACHE_YTMUSIC_ART_FILE = "/tmp/nowplaying_ytmusic_art.txt"
CACHE_APP_ICON_DIR = "/tmp/nowplaying_app_icons"
CACHE_APP_ICON_SCRIPT = "/tmp/nowplaying_get_app_icon.js"

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

    if (!appPath) return "";

    var icon = ws.iconForFile(appPath);
    if (!icon) return "";

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
    if (!pngData) return "";
    var b64 = pngData.base64EncodedStringWithOptions(0);
    return "data:image/png;base64," + ObjC.unwrap(b64);
}
'''

def get_app_icon(bundle_id, app_name):
    bundle_id = (bundle_id or "").strip()
    app_name = (app_name or "").strip()
    if not bundle_id and not app_name:
        return ""

    cache_key = f"{bundle_id}___{app_name}".lower()
    if cache_key in _APP_ICON_MEM_CACHE:
        return _APP_ICON_MEM_CACHE[cache_key]

    if not os.path.exists(CACHE_APP_ICON_DIR):
        try:
            os.makedirs(CACHE_APP_ICON_DIR, exist_ok=True)
        except Exception:
            pass

    key_hash = hashlib.md5(cache_key.encode("utf-8", errors="ignore")).hexdigest()
    cache_file = os.path.join(CACHE_APP_ICON_DIR, f"{key_hash}.txt")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = f.read().strip()
                if cached_data:
                    _APP_ICON_MEM_CACHE[cache_key] = cached_data
                    return cached_data
        except Exception:
            pass

    # Ensure JXA script exists
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
            timeout=1.5
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

    _APP_ICON_MEM_CACHE[cache_key] = ""
    return ""

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
            timeout=1.5
        )
        stdout = proc.stdout.strip()
        if not stdout or stdout == "null":
            return None
        return json.loads(stdout)
    except Exception:
        return None

def get_track_art_cache_path(track_key):
    if not track_key:
        return ""
    h = hashlib.md5(track_key.encode("utf-8", errors="ignore")).hexdigest()
    return os.path.join(CACHE_ART_DIR, f"{h}.txt")

def download_and_encode_image(url, timeout=2.0):
    if not url:
        return ""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if not data:
                return ""
            b64 = base64.b64encode(data).decode("ascii")
            mime = "image/jpeg"
            if data.startswith(b"\x89PNG"):
                mime = "image/png"
            elif data.startswith(b"GIF"):
                mime = "image/gif"
            elif data.startswith(b"RIFF") and b"WEBP" in data[:16]:
                mime = "image/webp"
            return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

def clean_title_and_artist(artist, title):
    t = (title or "").strip()
    noise_patterns = [
        r'\s*[\(\[][^\)\]]*(?:remaster|deluxe|edition|bonus|anniversary|official|video|audio|visualizer|hd|4k)[^\)\]]*[\)\]]',
        r'\s*[\(\[](?:feat\.|ft\.).*?[\)\]]',
        r'\s*-\s*single\s*$',
        r'\s*-\s*ep\s*$',
        r'\s*-\s*remaster(?:ed)?(?:\s*\d{4})?.*$',
        r'\s*-\s*\d{4}\s*remaster.*$',
    ]
    cleaned_t = t
    for pat in noise_patterns:
        cleaned_t = re.sub(pat, '', cleaned_t, flags=re.I).strip()
    if cleaned_t:
        t = cleaned_t

    a = re.sub(r'(\s*[-•]\s*Topic|\s*Topic\b)', '', artist or '', flags=re.I).strip()
    primary_a = re.split(r'[,&•]|\s+(?:feat\.|ft\.|x|vs\.)\s+', a, flags=re.I)[0].strip()
    return primary_a, a, t

def fetch_online_artwork(artist, title):
    if not title:
        return ""

    primary_a, clean_a, clean_t = clean_title_and_artist(artist, title)

    queries = []
    if primary_a and clean_t:
        queries.append(f"{primary_a} {clean_t}".strip())
    if clean_a and clean_t and clean_a != primary_a:
        queries.append(f"{clean_a} {clean_t}".strip())
    core_t = re.sub(r'\s*[\(\[].*?[\)\]]', '', clean_t).strip()
    if core_t and core_t != clean_t:
        if primary_a:
            queries.append(f"{primary_a} {core_t}".strip())
        queries.append(core_t)
    if clean_t:
        queries.append(clean_t.strip())
    if artist and title:
        raw_q = f"{artist} {title}".strip()
        if raw_q not in queries:
            queries.append(raw_q)

    seen = set()
    uniq_queries = []
    for q in queries:
        ql = q.lower()
        if q and ql not in seen:
            seen.add(ql)
            uniq_queries.append(q)

    # Tier 1: Deezer Search API (superb square 1000x1000 official album covers)
    for q in uniq_queries:
        try:
            url = f"https://api.deezer.com/search?q={urllib.parse.quote(q)}&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                if items:
                    album = items[0].get("album", {})
                    img_url = album.get("cover_xl") or album.get("cover_big")
                    if img_url:
                        b64_data = download_and_encode_image(img_url, timeout=1.8)
                        if b64_data:
                            return b64_data
        except Exception:
            pass

    # Tier 2: iTunes Search API (high-res 600x600 square covers)
    for q in uniq_queries:
        try:
            url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
                "term": q,
                "media": "music",
                "limit": "1"
            })
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    raw_url = results[0].get("artworkUrl100", "")
                    if raw_url:
                        high_res = raw_url.replace("100x100bb", "600x600bb").replace("100x100", "600x600")
                        b64_data = download_and_encode_image(high_res, timeout=1.8)
                        if b64_data:
                            return b64_data
        except Exception:
            pass

    # Tier 3: YouTube Search fallback
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(uniq_queries[0] if uniq_queries else title)}"
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

def process_artwork(data, track_key, artist="", title="", bundle_id="", app_name=""):
    if not track_key and not title:
        return ""

    if not os.path.exists(CACHE_ART_DIR):
        try:
            os.makedirs(CACHE_ART_DIR, exist_ok=True)
        except Exception:
            pass

    bundle_l = (bundle_id or (data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") if data else "") or "").lower()
    app_l = (app_name or "").lower()
    is_yt = ("webapp" in bundle_l or "ytmusic" in bundle_l or "youtube" in app_l or "webkit" in bundle_l)

    pa, ca, ct = clean_title_and_artist(artist, title)
    canonical_key = f"{ct}___{ca}".lower() if ct else (track_key or "").lower()

    official_cache_file = get_track_art_cache_path(f"official___{canonical_key}")
    track_cache_file = get_track_art_cache_path(canonical_key)

    # 1. Fast path: return verified official album art if already cached
    if os.path.exists(official_cache_file):
        try:
            with open(official_cache_file, "r") as f:
                cached_art = f.read().strip()
                if cached_art and cached_art.startswith("data:image/"):
                    return cached_art
        except Exception:
            pass

    # 2. For YouTube Music: Prioritize official square song album art over video thumbnails
    # (Matches user requirement: always use song album art for music videos on YouTube Music,
    # and keeps artwork intact when switching between music video and audio modes)
    if is_yt and title:
        no_art_file = get_track_art_cache_path(f"no_art___{canonical_key}")
        should_fetch = True
        if os.path.exists(no_art_file):
            try:
                if (time.time() - os.path.getmtime(no_art_file)) < 300:
                    should_fetch = False
            except Exception:
                pass

        if should_fetch:
            online_art = fetch_online_artwork(artist, title)
            if online_art and online_art.startswith("data:image/"):
                try:
                    with open(official_cache_file, "w") as f:
                        f.write(online_art)
                    with open(track_cache_file, "w") as f:
                        f.write(online_art)
                    with open(CACHE_ART_FILE, "w") as f:
                        f.write(online_art)
                    with open(CACHE_YTMUSIC_ART_FILE, "w") as f:
                        f.write(online_art)
                except Exception:
                    pass
                return online_art
            else:
                try:
                    with open(no_art_file, "w") as f:
                        f.write("none")
                except Exception:
                    pass

    # 3. Fast path: check standard track cache file (for non-YT or if online was not found)
    if track_cache_file and os.path.exists(track_cache_file):
        try:
            with open(track_cache_file, "r") as f:
                cached_art = f.read().strip()
                if cached_art and cached_art.startswith("data:image/"):
                    return cached_art
        except Exception:
            pass

    # 4. Process raw artwork from MediaRemote if present (used directly for Apple Music, Spotify, or fallback)
    raw_art = data.get("kMRMediaRemoteNowPlayingInfoArtworkData") if data else None
    if raw_art and track_cache_file:
        try:
            art_bytes = base64.b64decode(raw_art)
            tmp_in = "/tmp/nowplaying_art.tiff"
            tmp_out = "/tmp/nowplaying_art.jpg"
            with open(tmp_in, "wb") as f:
                f.write(art_bytes)

            dims_proc = subprocess.run(
                ["sips", "-1", "-g", "pixelWidth", "-g", "pixelHeight", tmp_in],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            w, h = 0, 0
            if dims_proc.returncode == 0:
                for chunk in dims_proc.stdout.split("|"):
                    if "pixelWidth:" in chunk:
                        try:
                            w = int(chunk.split(":")[1].strip())
                        except Exception:
                            pass
                    elif "pixelHeight:" in chunk:
                        try:
                            h = int(chunk.split(":")[1].strip())
                        except Exception:
                            pass

            max_dim = max(w, h)
            cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85"]
            if max_dim > 800:
                cmd.extend(["-Z", "800"])
            cmd.extend([tmp_in, "--out", tmp_out])

            subprocess.run(cmd, capture_output=True, timeout=1.2)

            if os.path.exists(tmp_out):
                with open(tmp_out, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode("ascii")
                artwork_data_url = f"data:image/jpeg;base64,{b64_img}"
                with open(track_cache_file, "w") as f:
                    f.write(artwork_data_url)
                with open(CACHE_ART_FILE, "w") as f:
                    f.write(artwork_data_url)
                if is_yt:
                    with open(CACHE_YTMUSIC_ART_FILE, "w") as f:
                        f.write(artwork_data_url)
                return artwork_data_url
        except Exception:
            pass

    # 5. Non-YT online resolution fallback
    if title:
        online_art = fetch_online_artwork(artist, title)
        if online_art and online_art.startswith("data:image/"):
            try:
                with open(track_cache_file, "w") as f:
                    f.write(online_art)
                with open(CACHE_ART_FILE, "w") as f:
                    f.write(online_art)
            except Exception:
                pass
            return online_art

    return ""

def is_process_running(proc_name):
    try:
        res = subprocess.run(["pgrep", "-x", proc_name], capture_output=True, timeout=0.5)
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
        else: # playback_rate == 1
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

def get_ytmusic_rating():
    if not is_process_running("Web App"):
        return None
    script = '''
tell application "System Events"
  try
    tell application process "Web App"
      if (count of windows) is 0 then return "none"
      tell window 1
        set s to first UI element whose role is "AXSplitGroup"
        set tb to first UI element of s whose role is "AXTabGroup"
        set g1 to first UI element of tb whose role is "AXGroup"
        set g2 to first UI element of g1 whose role is "AXGroup"
        set sa to first UI element of g2 whose role is "AXScrollArea"
        set wa to first UI element of sa whose role is "AXWebArea"
        set pb to first UI element of wa whose description is "Player bar"
        
        set els to UI elements of pb
        set c to count of els
        repeat with i from 14 to c
          set el to item i of els
          if role of el is "AXCheckBox" then
            set dlkVal to value of el as text
            set lkVal to "0"
            try
              set lkVal to value of (first UI element of (item (i - 1) of els)) as text
            end try
            return (lkVal & "," & dlkVal)
          end if
        end repeat
        return "none"
      end tell
    end tell
  on error
    return "none"
  end try
end tell
'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2.5)
        out = res.stdout.strip()
        if out.startswith("1,"):
            return "liked"
        elif out.endswith(",1"):
            return "disliked"
        elif out == "0,0":
            return None
    except Exception:
        pass
    return None

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
        
        return (t & "|||" & a & "|||" & tm & "|||" & pp & "|||" & lk & "|||" & dlk & "|||" & winTitle & "|||" & al)
      end tell
    end tell
  on error
    return "none"
  end try
end tell
'''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            title = parts[0].strip()
            artist = parts[1].strip() if len(parts) > 1 else ""
            time_str = parts[2].strip() if len(parts) > 2 else ""
            pp_title = parts[3].strip() if len(parts) > 3 else "Play"
            lk_val = parts[4].strip() if len(parts) > 4 else "0"
            dlk_val = parts[5].strip() if len(parts) > 5 else "0"

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

            # Resolve artwork
            yt_art_key = f"{title}___{artist}___"
            artwork_url = process_artwork({}, yt_art_key, artist, title, "com.apple.Safari.WebApp.F5D92F4A-8F5E-4368-A535-047D3666F565", "YouTube Music")

            return {
                "id": "ytmusic",
                "title": title,
                "artist": artist,
                "album": "",
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
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.2)
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
                art_url = process_artwork({}, am_art_key, artist, name, "com.apple.Music", "Apple Music")

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
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.2)
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

def get_audio_pids():
    try:
        res = subprocess.run(["pmset", "-g", "assertions"], capture_output=True, text=True, timeout=0.8)
        pids = set()
        for line in res.stdout.splitlines():
            if "Created for PID:" in line:
                pid = line.split("Created for PID:")[1].strip().rstrip(".")
                if pid.isdigit():
                    pids.add(int(pid))
        return pids
    except Exception:
        return set()

def is_proc_playing_audio(proc_name):
    try:
        res = subprocess.run(["pgrep", "-i", proc_name], capture_output=True, text=True, timeout=0.5)
        pids = [int(p) for p in res.stdout.split() if p.isdigit()]
        audio_pids = get_audio_pids()
        return any(p in audio_pids for p in pids)
    except Exception:
        return False

def is_dedicated_music_app(stream):
    app_name = (stream.get("appName") or "").lower()
    bundle_id = (stream.get("bundleId") or "").lower()
    stream_id = (stream.get("id") or "").lower()
    music_keywords = ["youtube music", "ytmusic", "spotify", "apple music", "music", "itunes", "tidal", "deezer", "qobuz", "pandora", "soundcloud", "bandcamp"]
    for kw in music_keywords:
        if kw in app_name or kw in bundle_id or kw in stream_id:
            return True
    return False

def stream_sort_key(s):
    # 1. Playing apps first: rate == 1 gets top priority (weight 100)
    is_playing = 100 if s.get("rate") == 1 else 0

    # 2. Actual music apps bias: dedicated music players get a +10 boost
    # (keeps generic web browsers / HTML video tabs like Firefox/Chrome behind music players when both play)
    music_bias = 10 if is_dedicated_music_app(s) else 0

    # 3. Rich metadata bonus: has artist or album art (+2)
    has_rich_meta = 2 if (s.get("artist") or s.get("artwork")) else 0

    # 4. Recency timestamp as final tie-breaker
    recency = float(s.get("updatedAt", 0))

    return (is_playing, music_bias, has_rich_meta, recency)

def main():
    now = time.time()
    streams_map = {}

    # Load recent cached streams (only dedicated music apps: YTMusic, Apple Music, Spotify)
    # Generic browser streams (Firefox, Chrome, Safari) are NEVER kept from cache because when their
    # media tab closes, they have no persistent session, cannot be controlled, and would hijack playback controls.
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

    # 1. Primary MediaRemote NowPlaying query
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
            artwork_url = process_artwork(mr_data, art_track_key, artist, title, bundle_id, app_name)
            current_elapsed = calculate_progress(progress_track_key, raw_elapsed, duration, playback_rate)

            # Rating determination
            rating = None
            if supports_rating:
                if stream_id == "ytmusic":
                    # Rating is fetched in get_ytmusic_direct_stream to avoid redundant JXA calls
                    rating = None
                elif stream_id == "apple_music":
                    am_s = get_apple_music_stream()
                    if am_s:
                        rating = am_s.get("rating")
            else:
                rating = None

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
                "rating": rating,
                "supportsRating": supports_rating,
                "updatedAt": round(now, 3)
            }
            streams_map[stream_id] = primary_stream

    # 2. Check YouTube Music if running
    if is_process_running("Web App"):
        yt_stream = get_ytmusic_direct_stream()
        if yt_stream:
            if "ytmusic" in streams_map:
                existing = streams_map["ytmusic"]
                if not yt_stream.get("artwork") and existing.get("artwork"):
                    yt_stream["artwork"] = existing["artwork"]
                elif yt_stream.get("artwork") and not existing.get("artwork"):
                    existing["artwork"] = yt_stream["artwork"]
                if existing.get("album"):
                    yt_stream["album"] = existing["album"]
                if existing.get("bundleId"):
                    yt_stream["bundleId"] = existing["bundleId"]
                if existing.get("artist") and existing.get("artist") != existing.get("title"):
                    yt_stream["artist"] = existing["artist"]
                streams_map["ytmusic"] = yt_stream
                if primary_stream and primary_stream.get("id") == "ytmusic":
                    primary_stream["elapsed"] = yt_stream["elapsed"]
                    primary_stream["duration"] = yt_stream["duration"]
                    primary_stream["rate"] = yt_stream["rate"]
                    primary_stream["rating"] = yt_stream["rating"]
                    if yt_stream.get("artwork"):
                        primary_stream["artwork"] = yt_stream["artwork"]
                    if yt_stream.get("title"):
                        primary_stream["title"] = yt_stream["title"]
                    if yt_stream.get("artist"):
                        primary_stream["artist"] = yt_stream["artist"]
                    new_state = {
                        "track_id": progress_track_key,
                        "anchor_elapsed": yt_stream["elapsed"],
                        "anchor_time": now,
                        "last_raw_elapsed": yt_stream["elapsed"],
                        "last_rate": yt_stream["rate"],
                        "last_updated": now
                    }
                    try:
                        with open(CACHE_STATE_FILE, "w") as f:
                            json.dump(new_state, f)
                    except Exception:
                        pass
            else:
                streams_map["ytmusic"] = yt_stream

    # 3. Check Apple Music if running
    if is_process_running("Music"):
        am_stream = get_apple_music_stream()
        if am_stream:
            if "apple_music" in streams_map:
                existing = streams_map["apple_music"]
                if not am_stream.get("artwork") and existing.get("artwork"):
                    am_stream["artwork"] = existing["artwork"]
                elif am_stream.get("artwork") and not existing.get("artwork"):
                    existing["artwork"] = am_stream["artwork"]
                streams_map["apple_music"] = am_stream
                if primary_stream and primary_stream.get("id") == "apple_music":
                    primary_stream["elapsed"] = am_stream["elapsed"]
                    primary_stream["duration"] = am_stream["duration"]
                    primary_stream["rate"] = am_stream["rate"]
                    primary_stream["rating"] = am_stream["rating"]
                    if am_stream.get("artwork"):
                        primary_stream["artwork"] = am_stream["artwork"]
            else:
                streams_map["apple_music"] = am_stream

    # 4. Check Spotify if running
    if is_process_running("Spotify"):
        sp_stream = get_spotify_stream()
        if sp_stream:
            if "spotify" in streams_map:
                existing = streams_map["spotify"]
                if not sp_stream.get("artwork") and existing.get("artwork"):
                    sp_stream["artwork"] = existing["artwork"]
                elif sp_stream.get("artwork") and not existing.get("artwork"):
                    existing["artwork"] = sp_stream["artwork"]
                streams_map["spotify"] = sp_stream
                if primary_stream and primary_stream.get("id") == "spotify":
                    primary_stream["elapsed"] = sp_stream["elapsed"]
                    primary_stream["duration"] = sp_stream["duration"]
                    primary_stream["rate"] = sp_stream["rate"]
                    if sp_stream.get("artwork"):
                        primary_stream["artwork"] = sp_stream["artwork"]
            else:
                streams_map["spotify"] = sp_stream


    # Filter out dead streams
    active_streams = []
    for s_id, s in streams_map.items():
        if not s.get("title") or s.get("title") == "null":
            continue
        # Generic browser streams (Firefox, Chrome, Safari) must be the current primary MediaRemote stream.
        # If the user closed the tab or MediaRemote switched away, discard immediately.
        if not is_dedicated_music_app(s):
            if not (primary_stream and primary_stream.get("id") == s_id):
                continue
        active_streams.append(s)

    # Sort: actively playing first, slight bias for actual music apps, then recency
    active_streams.sort(key=stream_sort_key, reverse=True)

    # Attach authentic macOS application icons
    for s in active_streams:
        s["appIcon"] = get_app_icon(s.get("bundleId", ""), s.get("appName", ""))

    # Save cache
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
