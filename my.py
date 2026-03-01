import asyncio
import websockets
import json
import base64
import os
import uuid
import time
import sys
import random

# ── Environment & Storage Setup ──────────────────────────────────────────────
# Check if running in Termux to save to Gallery
IS_TERMUX = os.path.exists("/sdcard") or os.environ.get("TERMUX_VERSION")
if IS_TERMUX:
    IMG_DIR = "/sdcard/Pictures/SK_Grok_Bulk"
    # Ensure standard Termux local folder as fallback if sdcard isn't mapped
    if not os.path.exists("/sdcard"):
        IMG_DIR = os.path.expanduser("~/images")
else:
    IMG_DIR = "images"

os.makedirs(IMG_DIR, exist_ok=True)

# ── Auto-detect websockets version for cross-platform header arg ──────────────
_ws_ver = tuple(int(x) for x in websockets.__version__.split(".")[:2])
_HEADERS_KWARG = "additional_headers" if _ws_ver >= (12, 0) else "extra_headers"

# ── ANSI Color Codes ──────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    BGBLACK= "\033[40m"

# Enable ANSI on Windows
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)

# ─── UPDATE COOKIES IF YOU GET AUTH ERRORS ────────────────────────────────────
HEADERS = {
    "Origin": "https://grok.com",
    "Cache-Control": "no-cache",
    "Accept-Language": "en-US,en;q=0.9",
    "Pragma": "no-cache",
    "Cookie": "i18nextLng=en; _ga=GA1.1.559586213.1755800838; stblid=2cecada7-1422-4186-ab95-8d9a9259af7c; sso=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMzViOWIwNDMtOTcwYi00YTA0LWE5ZjctOWZmNWU2M2U1ZTkyIn0.8Zm_X89ovRzUC4URnMFI7QcW8I0eer_zlsd73ssuZYE; sso-rw=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMzViOWIwNDMtOTcwYi00YTA0LWE5ZjctOWZmNWU2M2U1ZTkyIn0.8Zm_X89ovRzUC4URnMFI7QcW8I0eer_zlsd73ssuZYE; x-userid=907e5266-aea0-492e-b0af-0398305dd924; cf_clearance=y9ovrsSTdXRuOJDIGOp1eZBaJmrDqj_mBabgD6sGIyI-1772356773-1.2.1.1-1gHevOcGnq7wB2jD..6Bh4jzD.cmZR7cXBIgFBfe8lZaAanz_eWZRJOp0UkWnfjhtIpUSkxtdsqRbXxjOJxs3gO3OFwA0xtpNTZnyKx9CZ6EDibQ8webNgE9rID4qqhbotFaTuCLkVRIZVEzqPcP8O1fRVqFdhcUn7pve3A7ODXaQIVCe_zsq66EttmCgdy.QWkfaM218IBn5A7diJ7V6wpwiDBrux0qeLK1LyFrSIM; mp_ea93da913ddb66b6372b89d97b1029ac_mixpanel=%7B%22distinct_id%22%3A%22907e5266-aea0-492e-b0af-0398305dd924%22%2C%22%24device_id%22%3A%22b2b54290-b727-4206-83a5-e2f76917a407%22%2C%22%24search_engine%22%3A%22google%22%2C%22__mps%22%3A%7B%7D%2C%22__mpso%22%3A%7B%7D%2C%22__mpus%22%3A%7B%7D%2C%22__mpa%22%3A%7B%7D%2C%22__mpu%22%3A%7B%7D%2C%22__mpr%22%3A%5B%5D%2C%22__mpap%22%3A%5B%5D%2C%22%24user_id%22%3A%22907e5266-aea0-492e-b0af-0398305dd924%22%7D; __cf_bm=RMURqDA2Fe4yyHqHekL2pAZ0hQ.2ERRTXWUDJf6ZcOU-1772360626-1.0.1.1-gpcdXT2z7BxSZUl0fgG_fpBiUSp6YqhaL7NPaSkpG6t.AM6mGm7_CW3z.eux3I5LFadBo9.d0fLTiVHtg.41Az_i6jEstXbh_.7xXx_kvVA; _ga_8FEWB057YH=GS2.1.s1772359438$o19$g1$t1772360980$j60$l0$h0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}
# ──────────────────────────────────────────────────────────────────────────────

URI = "wss://grok.com/ws/imagine/listen"
PIPELINE_SIZE = 10   # Parallel requests in-flight at once


def print_banner(art, color):
    """Print a banner in a given color with a glitchy entrance."""
    os.system("cls" if sys.platform == "win32" else "clear")
    lines = art.strip().split("\n")
    for line in lines:
        # Subtle glitch: random chars before the real line
        if random.random() > 0.7:
            glitch = "".join(random.choice("!@#$%^&*()_+-=") for _ in range(len(line)))
            print(f"{C.RED}{glitch}{C.RESET}")
            time.sleep(0.01)
            # Clear line
            print("\033[A\033[K", end="") 
        print(f"{color}{C.BOLD}{line}{C.RESET}")


def gprint(msg, color=C.GREEN, end="\n"):
    print(f"{color}{msg}{C.RESET}", end=end, flush=True)


def hline(char="═", color=C.CYAN, width=60):
    print(f"{color}{char * width}{C.RESET}", flush=True)


def banner():
    # Stacked HACKER + SK for mobile impact
    HACKER_SK = r"""
  _  _   _   ___ _  _____ ___ 
 | || | /_\ / __| |/ / __| _ \
 | __ |/ _ \ (__| ' <| _||   /
 |_||_/_/ \_\___|_|\_\___|_|_|
      
      ___ _  __
     / __| |/ / 
     \__ \ ' <  
     |___/_|\_\ """

    SK = r"""
      ___ _  __
     / __| |/ / 
     \__ \ ' <  
     |___/_|\_\ """

    COLOR_CYCLE = [C.GREEN, C.CYAN, C.MAGENTA, C.YELLOW, C.RED, C.GREEN]
    BANNERS     = [SK, HACKER_SK]

    # Cycle between SK and HACKER SK, changing color every 2 seconds — 4 cycles
    for i in range(6):
        banner_art = BANNERS[i % 2]
        color      = COLOR_CYCLE[i % len(COLOR_CYCLE)]
        print_banner(banner_art, color)

        # After the last banner, print subtitle & boot — then stop cycling
        if i == 5:
            break

        print(f"\n  {C.DIM}{C.WHITE}[ changing in 2s... press Ctrl+C to skip ]{C.RESET}")
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            break

    # Final clear + show HACKER SK in green as the settled banner
    print_banner(HACKER_SK, C.GREEN)

    SUBTITLE = """
  ╔══════════════════════════════════════════════╗
  ║   GROK UNLIMITED IMAGE GEN  //  BULK MODE   ║
  ║         [ PIPELINE EXPLOIT v2.0 ]           ║
  ╚══════════════════════════════════════════════╝"""

    BOOT = [
        "[BOOT] Initializing SK exploit framework ...",
        "[BOOT] Loading WebSocket injection module ...",
        "[BOOT] Bypassing rate-limit firewall ...",
        "[BOOT] Hooking pipeline dispatcher ...",
        "[BOOT] Arming image extraction engine ...",
        "[SYS]  ALL SYSTEMS ARMED. READY TO FIRE.",
    ]

    for line in SUBTITLE.split("\n"):
        print(f"{C.CYAN}{line}{C.RESET}")
        time.sleep(0.03)

    print()
    for i, msg in enumerate(BOOT):
        col  = C.RED if i == len(BOOT) - 1 else C.DIM + C.GREEN
        bold = C.BOLD if i == len(BOOT) - 1 else ""
        print(f"  {col}{bold}{msg}{C.RESET}")
        time.sleep(0.18)

    print()
    print()


def make_payload(prompt):
    request_id = str(uuid.uuid4())
    payload = {
        "type": "conversation.item.create",
        "timestamp": int(time.time() * 1000),
        "item": {
            "type": "message",
            "content": [
                {
                    "requestId": request_id,
                    "text": prompt,
                    "type": "input_text",
                    "properties": {
                        "section_count": 0,
                        "is_kids_mode": False,
                        "enable_nsfw": True,
                        "skip_upsampler": False,
                        "enable_side_by_side": True,
                        "is_initial": False,
                        "aspect_ratio": "2:3"
                    }
                }
            ]
        }
    }
    return request_id, payload


async def run_forever(prompt):
    safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt)[:30]
    total_saved = 0
    start_time  = time.time()

    hline()
    gprint(f"  TARGET PROMPT  : {prompt}", C.YELLOW)
    gprint(f"  PIPELINE SIZE  : {PIPELINE_SIZE} parallel requests", C.CYAN)
    gprint(f"  OUTPUT FOLDER  : {IMG_DIR}", C.CYAN)
    gprint(f"  STARTED        : {time.strftime('%H:%M:%S')}", C.CYAN)
    hline()
    gprint("  [SYS] Establishing WebSocket tunnel to grok.com ...", C.MAGENTA)

    async with websockets.connect(
        URI,
        **{_HEADERS_KWARG: HEADERS},
        compression="deflate",
        ping_interval=20,
        ping_timeout=10
    ) as ws:

        gprint("  [SYS] TUNNEL ESTABLISHED ✔", C.GREEN)
        gprint(f"  [SYS] Flooding pipeline with {PIPELINE_SIZE} requests ...", C.MAGENTA)

        job_to_req = {}
        req_active = {}
        req_done   = {}
        in_flight  = set()

        async def send_request():
            req_id, payload = make_payload(prompt)
            await ws.send(json.dumps(payload))
            req_active[req_id] = set()
            req_done[req_id]   = 0
            in_flight.add(req_id)
            return req_id

        for _ in range(PIPELINE_SIZE):
            await send_request()

        gprint(f"  [SYS] Pipeline active. Intercepting image streams ...\n", C.MAGENTA)
        hline("─", C.DIM)

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
            except asyncio.TimeoutError:
                gprint("  [WARN] Idle timeout — re-injecting request ...", C.YELLOW)
                await send_request()
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            job_id   = data.get("job_id")
            pct      = data.get("percentage_complete", 0.0)
            req_id   = data.get("request_id")

            if job_id and req_id:
                job_to_req[job_id] = req_id
                if req_id in req_active:
                    if pct < 100.0:
                        req_active[req_id].add(job_id)
                    elif pct == 100.0:
                        req_active[req_id].discard(job_id)
                        req_done[req_id] = req_done.get(req_id, 0) + 1

            # Save final 100% images and print hacker-style log
            if msg_type == "image" and pct == 100.0:
                blob = data.get("blob")
                if blob:
                    ts_str   = str(int(time.time() * 1000))
                    short_id = (job_id or "img")[:8]
                    fname    = os.path.join(IMG_DIR, f"{safe_prompt}_{short_id}_{ts_str}.jpg")
                    if "," in blob:
                        blob = blob.split(",", 1)[1]
                    with open(fname, "wb") as f:
                        f.write(base64.b64decode(blob))
                    total_saved += 1
                    elapsed = int(time.time() - start_time)
                    rate    = total_saved / elapsed if elapsed > 0 else 0
                    # Hacker-style line with color
                    tag   = f"{C.GREEN}[+]{C.RESET}"
                    num   = f"{C.BOLD}{C.WHITE}[{total_saved:04d}]{C.RESET}"
                    jid   = f"{C.DIM}{C.CYAN}{short_id}{C.RESET}"
                    name  = f"{C.GREEN}{fname}{C.RESET}"
                    stats = f"{C.DIM}{C.YELLOW}| {rate:.1f} img/s | {elapsed}s elapsed{C.RESET}"
                    print(f"  {tag} {num} {jid} → {name} {stats}", flush=True)

            if req_id and req_id in in_flight:
                active = req_active.get(req_id, set())
                done   = req_done.get(req_id, 0)
                if done >= 1 and len(active) == 0:
                    in_flight.discard(req_id)
                    await send_request()


def main():
    banner()
    print()
    hline("═", C.GREEN)
    gprint("  GROK UNLIMITED IMAGE GENERATOR  //  BULK MODE", C.BOLD + C.GREEN)
    gprint("  [!] Press Ctrl+C to abort at any time", C.RED)
    hline("═", C.GREEN)
    print()

    prompt = input(f"  {C.CYAN}[>]{C.RESET} Enter target prompt: ").strip()
    if not prompt:
        gprint("  [!] No prompt supplied. Aborting.", C.RED)
        return

    print()
    try:
        asyncio.run(run_forever(prompt))
    except KeyboardInterrupt:
        print()
        hline("═", C.RED)
        gprint("  [!] SESSION TERMINATED BY USER", C.RED + C.BOLD)
        hline("═", C.RED)
    except Exception as e:
        gprint(f"\n  [ERR] {e}", C.RED)


if __name__ == "__main__":
    main()
