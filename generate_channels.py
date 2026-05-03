import os
import re
import requests
import json
import shutil
import base64
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
M3U_URL = "https://raw.githubusercontent.com/sportlive18/Jio-Auto-Update-m3u-playlist/refs/heads/main/jiotv.m3u"
OUTPUT_DIR = "Channel"

# Ensure output directory exists and is clean
if os.path.exists(OUTPUT_DIR):
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}', flush=True)
else:
    os.makedirs(OUTPUT_DIR)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CHANNEL_TITLE}</title>
<meta name="referrer" content="no-referrer">
<script src="https://cdn.jsdelivr.net/npm/shaka-player@4.16.2/dist/shaka-player.ui.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/shaka-player@4.16.2/dist/controls.css"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.shaka-video-container{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;}
video{width:100%;height:100%;object-fit:contain;background:#000;}
</style>
</head>
<body>
<div class="shaka-video-container" id="player-container">
<video id="video" autoplay muted playsinline preload="metadata"></video>
</div>
<script>
(async function(){
  shaka.polyfill.installAll();
  if(!shaka.Player.isBrowserSupported()) return;

  const CONFIG={
    streamUrl:"{STREAM_URL}",
    keyId:"{KEY_ID}",
    key:"{KEY}",
    licenseUrl:"{LICENSE_URL}",
    cookie:"{COOKIE}",
    cookieUrl:"https://sayan10-sportlink-cookies.pages.dev/api/cookie.json"
  };

  const video=document.getElementById("video");
  const container=document.getElementById("player-container");
  const player=new shaka.Player();
  await player.attach(video);
  const ui=new shaka.ui.Overlay(player,container,video);

  ui.configure({
    addBigPlayButton: true,
    controlPanelElements: [
      "mute", "play_pause", "time_and_duration", "spacer", "quality", "picture_in_picture", "fullscreen"
    ],
    seekBarColors: {
      base: "rgba(255, 255, 255, 0.3)",
      buffered: "rgba(255, 255, 255, 0.5)",
      played: "rgb(0, 150, 255)"
    }
  });

  const drmConfig = {};
  if (CONFIG.keyId && CONFIG.key) {
    // Shaka expects hex for clearKeys
    drmConfig.clearKeys = {[CONFIG.keyId]: CONFIG.key};
  } else if (CONFIG.licenseUrl) {
    drmConfig.servers = {'com.widevine.alpha': CONFIG.licenseUrl};
  }

  player.configure({
    drm: drmConfig,
    manifest:{defaultPresentationDelay:5},
    streaming:{lowLatencyMode:true,bufferingGoal:10,rebufferingGoal:2,safeSeekOffset:5}
  });

  let cookieValue=CONFIG.cookie || "";
  if(!cookieValue){
      try{
        const response=await fetch(CONFIG.cookieUrl,{cache:"no-store"});
        const data=await response.json();
        cookieValue=data.cookie||"";
      }catch(e){}
  }

  if(cookieValue){
    player.getNetworkingEngine().registerRequestFilter((type,request)=>{
      request.headers["Referer"]="https://www.jiotv.com/";
      request.headers["User-Agent"]="plaYtv/7.1.5 (Linux;Android 13) ExoPlayerLib/2.11.6";
      request.headers["Cookie"]=cookieValue;
      let urlCookie=cookieValue.startsWith("__hdnea__=")?cookieValue.substring(10):cookieValue;
      if((type===shaka.net.NetworkingEngine.RequestType.MANIFEST||type===shaka.net.NetworkingEngine.RequestType.SEGMENT)&&!request.uris[0].includes("__hdnea__")){
        const sep=request.uris[0].includes("?")?"&":"?";
        request.uris[0]+=sep+"__hdnea__="+urlCookie;
      }
    });
  }

  try{
    await player.load(CONFIG.streamUrl);
    video.play().catch(()=>{});
  }catch(e){}
  video.addEventListener("play",()=>{video.muted=false;});
})();
</script>
</body>
</html>"""

def b64url_to_hex(b64):
    padding = '=' * (4 - len(b64) % 4)
    b64 = b64.replace('-', '+').replace('_', '/') + padding
    return base64.b64decode(b64).hex()

def fetch_key(url, session, retries=3):
    if not url or not url.startswith("http"):
        return None, None, url
    for i in range(retries):
        try:
            headers = {
                'User-Agent': 'plaYtv/7.1.5 (Linux;Android 13) ExoPlayerLib/2.11.6',
                'Referer': 'https://www.jiotv.com/'
            }
            resp = session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if "keys" in data and len(data["keys"]) > 0:
                        kid_b64 = data["keys"][0]["kid"]
                        k_b64 = data["keys"][0]["k"]
                        return b64url_to_hex(kid_b64), b64url_to_hex(k_b64), ""
                except: pass
            elif resp.status_code == 429: time.sleep(1)
        except Exception:
            if i == retries - 1: pass
    return "", "", url

def generate():
    print(f"Fetching M3U from {M3U_URL}...", flush=True)
    try:
        response = requests.get(M3U_URL, timeout=30)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return

    raw_channels = []
    current_key_url = ""
    for line in lines:
        line = line.strip()
        if not line: continue
        if "inputstream.adaptive.license_key=" in line:
            current_key_url = line.split("=", 1)[-1]
        elif line.startswith("https://"):
            parts = line.split("|")
            stream_url = parts[0]
            cookie = parts[1].replace("cookie=", "").strip() if len(parts) > 1 and "cookie=" in parts[1] else ""
            match = re.search(r'/bpk-tv/([^/]+)/', stream_url)
            ch_name = match.group(1) if match else stream_url.split('/')[-2]
            raw_channels.append({"name": ch_name, "url": stream_url, "key_url": current_key_url, "cookie": cookie})
            current_key_url = ""

    print(f"Found {len(raw_channels)} channels. Fetching keys...", flush=True)
    
    # Pre-list logos for matching
    existing_logos = []
    if os.path.exists("logos"):
        existing_logos = {f.lower(): f for f in os.listdir("logos") if f.lower().endswith(".png")}
    
    session = requests.Session()
    def process_channel(ch):
        kid, k, l_url = fetch_key(ch['key_url'], session)
        if not ch['key_url'].startswith("http") and ":" in ch['key_url']:
            parts = ch['key_url'].split(":")
            kid, k, l_url = parts[0], parts[1], ""
            
        # Logo matching
        logo_path = ""
        base_name = ch['name'].lower()
        # Try multiple candidates: full name, name without _MOB, name without _BTS, etc.
        candidates = [
            base_name + ".png",
            base_name.replace("_mob", "") + ".png",
            base_name.replace("_bts", "") + ".png",
            base_name.split("_")[0] + ".png"
        ]
        for cand in candidates:
            if cand in existing_logos:
                logo_path = "logos/" + existing_logos[cand]
                break
                
        return {
            "name": ch['name'],
            "url": ch['url'],
            "keyId": kid,
            "key": k,
            "licenseUrl": l_url,
            "cookie": ch['cookie'],
            "logo": logo_path
        }

    with ThreadPoolExecutor(max_workers=10) as executor:
        channels = list(executor.map(process_channel, raw_channels))

    print(f"Generating files...", flush=True)
    for ch in channels:
        safe_name = ch['name'].replace(' ', '_')
        file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.html")
        content = HTML_TEMPLATE.replace("{CHANNEL_TITLE}", ch['name'].replace('_', ' '))\
                               .replace("{STREAM_URL}", ch['url'])\
                               .replace("{KEY_ID}", ch['keyId'] or "")\
                               .replace("{KEY}", ch['key'] or "")\
                               .replace("{LICENSE_URL}", ch['licenseUrl'] or "")\
                               .replace("{COOKIE}", ch['cookie'] or "")
        with open(file_path, "w", encoding="utf-8") as f: f.write(content)
            
    with open(os.path.join(OUTPUT_DIR, "channels.json"), "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2)
    print(f"Done! Generated {len(channels)} files.", flush=True)

if __name__ == "__main__":
    generate()


