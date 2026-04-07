import os
import re
import requests

# Configuration
M3U_URL = "https://raw.githubusercontent.com/alex4528x/m3u/refs/heads/main/jtv.m3u"
OUTPUT_DIR = "Channel"
TEMPLATE_FILE = "template_demo.html" # We'll create this first

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Provided Template (minified or kept clean)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CHANNEL_TITLE}</title>
<meta name="referrer" content="no-referrer">
<script src="https://cdn.jsdelivr.net/npm/shaka-player@4.16.2/dist/shaka-player.ui.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/shaka-player@4.16.2/dist/controls.css"/>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FMP9REY96D"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-FMP9REY96D');
</script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.shaka-video-container{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;}
video{width:100%;height:100%;object-fit:contain;background:#000;}
.custom-watermark{position:absolute;z-index:40;pointer-events:none;top:65%;left:6%;transform:translateY(-50%);font-size:11px;font-weight:600;color:rgba(255,255,255,0.12);}
.block-overlay{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at center, #1a1a1a 0%, #000000 100%);text-align:center;}
.block-box{padding:40px;max-width:500px;width:90%;background:rgba(20, 20, 20, 0.95);border-radius:16px;border:1px solid rgba(255, 255, 255, 0.1);box-shadow:0 20px 50px rgba(0,0,0,0.5);animation: fadeInUp 0.6s ease-out;}
@keyframes fadeInUp {from { opacity: 0; transform: translateY(30px); }to { opacity: 1; transform: translateY(0); }}
.block-title{font-size:42px;font-weight:800;color:#ffffff;text-transform:uppercase;letter-spacing:2px;margin-bottom:20px;text-shadow:0 0 10px rgba(255, 0, 0, 0.3);}
.block-sub{font-size:14px;font-weight:500;color:rgba(255, 255, 255, 0.6);line-height:1.6;}
.block-icon{ display: none; }.block-note{ display: none; }
@media(max-width:700px){ .custom-watermark{font-size:9px;top:60%;left:16%} .block-title{font-size:28px} .block-box{padding:25px} .block-sub{font-size:12px} }
</style>
</head>
<body>
<div class="shaka-video-container" id="player-container">
<video id="video" autoplay muted playsinline preload="metadata"></video>
<div class="custom-watermark"> </div>
</div>
<script>
(function(){
  function isSandboxedEnv(){
    try {
      if (window.self === window.top) return false;
      if (window.frameElement && window.frameElement.hasAttribute("sandbox")) return true;
      try { document.domain = document.domain; if (window.frameElement && !window.frameElement.getAttribute("sandbox")) return false; } catch (e) { return true; }
      return false;
    } catch(e) { return true; }
  }
  function triggerBlockScreen(title, message){
    const container = document.getElementById("player-container");
    const video = document.getElementById("video");
    try { video.pause(); video.removeAttribute('src'); video.load(); } catch(e){}
    const overlay = document.createElement("div");
    overlay.className = "block-overlay";
    overlay.id = "sandbox-block-display";
    overlay.innerHTML = `<div class="block-box"><div class="block-title">${title}</div><div class="block-sub">${message}</div></div>`;
    document.body.appendChild(overlay);
    container.style.display = 'none';
  }
  if(isSandboxedEnv()){ triggerBlockScreen('Disable Sandbox', 'Opening Chrome Browser Only & Disable Ad blocker'); return; }
  const CONFIG={
    streamUrl:"{STREAM_URL}",
    keyId:"400131994b445d8c8817202248760fda",
    key:"2d56cb6f07a75b9aff165d534ae2bfc4",
    cookieUrl:"https://allrounder-live2.pages.dev/api/cookie.json"
  };
  document.addEventListener("DOMContentLoaded",async()=>{
    shaka.polyfill.installAll();
    if(!shaka.Player.isBrowserSupported()) return;
    const video=document.getElementById("video");
    const container=document.getElementById("player-container");
    video.muted=true;
    const player=new shaka.Player();
    await player.attach(video);
    const ui=new shaka.ui.Overlay(player,container,video);
    ui.configure({ addBigPlayButton: true, controlPanelElements: [ "mute", "play_pause", "time_and_duration", "spacer", "quality", "picture_in_picture", "fullscreen" ], seekBarColors: { base: "white", buffered: "red", played: "green" } });
    player.configure({ drm:{clearKeys:{[CONFIG.keyId]:CONFIG.key}}, manifest:{defaultPresentationDelay:5}, streaming:{ lowLatencyMode:true, bufferingGoal:10, rebufferingGoal:2, safeSeekOffset:5 } });
    let cookieValue="";
    try{ const response=await fetch(CONFIG.cookieUrl,{cache:"no-store"}); const data=await response.json(); cookieValue=data.cookie||""; }catch(e){}
    if(cookieValue){
      player.getNetworkingEngine().registerRequestFilter((type,request)=>{
        request.headers["Referer"]="https://www.jiotv.com/";
        request.headers["User-Agent"]="plaYtv/7.1.5 (Linux;Android 13) ExoPlayerLib/2.11.6";
        request.headers["Cookie"]=cookieValue;
        let urlCookie=cookieValue.startsWith("__hdnea__=")?cookieValue.substring(10):cookieValue;
        if((type===shaka.net.NetworkingEngine.RequestType.MANIFEST|| type===shaka.net.NetworkingEngine.RequestType.SEGMENT)&& !request.uris[0].includes("__hdnea__")){
          const sep=request.uris[0].includes("?")?"&":"?";
          request.uris[0]+=sep+"__hdnea__="+urlCookie;
        }
      });
    }
    try{ await player.load(CONFIG.streamUrl); video.play().catch(()=>{}); }catch(e){}
    video.addEventListener("play",()=>{ video.muted=false; });
  });
})();
</script>
<script>(function(s){s.dataset.zone='10603308',s.src='https://bvtpk.com/tag.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')))</script>
</body>
</html>"""

def generate():
    print(f"Fetching M3U from {M3U_URL}...")
    response = requests.get(M3U_URL)
    if response.status_code != 200:
        print("Failed to fetch M3U")
        return

    lines = response.text.splitlines()
    channels = []
    
    # Simple extraction logic: find all https:// URLs that point to .mpd
    for line in lines:
        if line.startswith("https://") and ".mpd" in line:
            # Extract name from URL
            # Example: https://jiotvpllive.cdn.jio.com/bpk-tv/Star_Sports_HD1_Hindi_BTS/output/index.mpd
            match = re.search(r'/bpk-tv/([^/]+)/', line)
            if match:
                ch_name = match.group(1)
                channels.append({"name": ch_name, "url": line})
            else:
                # Fallback to last segment if structure is different
                ch_name = line.split('/')[-2] if '/' in line else "Channel"
                channels.append({"name": ch_name, "url": line})

    print(f"Found {len(channels)} channels. Starting generation...")

    for ch in channels:
        safe_name = ch['name'].replace(' ', '_')
        file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.html")
        
        # Format title (replace underscores with spaces)
        title = ch['name'].replace('_', ' ')
        
        content = HTML_TEMPLATE.replace("{CHANNEL_TITLE}", title).replace("{STREAM_URL}", ch['url'])
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    print(f"Successfully generated {len(channels)} files in {OUTPUT_DIR}/")

    # Generate channels.json for the dashboard
    import json
    json_path = os.path.join(OUTPUT_DIR, "channels.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=2)
    print(f"Generated {json_path}")

if __name__ == "__main__":
    generate()
