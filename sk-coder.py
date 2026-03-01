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
IS_TERMUX = os.path.exists("/sdcard") or os.environ.get("TERMUX_VERSION")
if IS_TERMUX:
    IMG_DIR = "/sdcard/Pictures/SK_Grok_Bulk"
    if not os.path.exists("/sdcard"):
        IMG_DIR = os.path.expanduser("~/images")
else:
    IMG_DIR = "images"

os.makedirs(IMG_DIR, exist_ok=True)

# Auto-detect websockets version for cross-platform header arg
_ws_ver = tuple(int(x) for x in websockets.__version__.split(".")[:2])
_HEADERS_KWARG = "additional_headers" if _ws_ver >= (12, 0) else "extra_headers"

# ── ANSI Color Codes ──────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[92m"
    CYAN    = "\033[96m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GOLD    = "\033[33m"
    BGBLACK = "\033[40m"

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

URI           = "wss://grok.com/ws/imagine/listen"
PIPELINE_SIZE = 10   # Parallel requests in-flight at once


def _glitch_print(art, color):
    """Print banner with king-style glitch effect."""
    os.system("cls" if sys.platform == "win32" else "clear")
    GLITCH_CHARS = "!#$%&*@><|/\\^~"
    for line in art.strip().split("\n"):
        if line.strip() and random.random() > 0.65:
            g = "".join(random.choice(GLITCH_CHARS) for _ in range(min(len(line), 38)))
            print(f"\r{C.RED}{C.DIM}{g}{C.RESET}", end="", flush=True)
            time.sleep(0.015)
            print(f"\r{' ' * 40}", end="", flush=True)
        print(f"{color}{C.BOLD}{line}{C.RESET}")


def gprint(msg, color=C.GREEN, end="\n"):
    print(f"{color}{msg}{C.RESET}", end=end, flush=True)


def hline(char="═", color=C.GOLD, width=38):
    print(f"{color}{char * width}{C.RESET}", flush=True)


def banner():
    # ── KING-style banner (mobile-width ~38 chars) ──
    CROWN = [
        "       .+.   .+.   .+.       ",
        "      (###) (###) (###)      ",
        "  .+. |###| |###| |###| .+. ",
        " (###)|###| |###| |###|(###)",
        " |###||#####################|",
        " |###########################|",
    ]

    HACKER = [
        " +-+-+-+-+-+-+",
        " |H|A|C|K|E|R|",
        " +-+-+-+-+-+-+",
    ]

    SK = [
        "   +-+-+",
        "   |S|K|",
        "   +-+-+",
    ]

    KING_COLORS = [C.GOLD, C.YELLOW, C.RED, C.WHITE, C.GOLD, C.GREEN]

    for cycle in range(6):
        os.system("cls" if sys.platform == "win32" else "clear")
        col = KING_COLORS[cycle % len(KING_COLORS)]

        # Crown
        for line in CROWN:
            print(f"{C.GOLD}{C.BOLD}{line}{C.RESET}")

        print()
        # HACKER block
        for line in HACKER:
            if line.strip() and random.random() > 0.6:
                g = "".join(random.choice("!#$%><*@") for _ in range(len(line)))
                print(f"\r{C.RED}{C.DIM}{g}{C.RESET}", end="", flush=True)
                time.sleep(0.02)
                print(f"\r{' ' * 40}", end="", flush=True)
            print(f"{col}{C.BOLD}{line}{C.RESET}")

        # SK block
        for line in SK:
            print(f"{C.RED}{C.BOLD}{line}{C.RESET}")

        if cycle == 5:
            break

        print(f"\n{C.DIM}  [ cycling {cycle+1}/5 — Ctrl+C to skip ]{C.RESET}")
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            break

    # ── Final locked-in KING banner ──
    os.system("cls" if sys.platform == "win32" else "clear")
    for line in CROWN:
        print(f"{C.GOLD}{C.BOLD}{line}{C.RESET}")
    print()

    # Big-block HACKER SK stacked
    HACKER_SK_FINAL = [
        f"{C.RED}{C.BOLD} ██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗{C.RESET}",
        f"{C.RED}{C.BOLD} ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗{C.RESET}",
        f"{C.RED}{C.BOLD} ███████║███████║██║     █████╔╝ █████╗  ██████╔╝{C.RESET}",
        f"{C.RED}{C.BOLD} ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗{C.RESET}",
        f"{C.RED}{C.BOLD} ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║{C.RESET}",
        f"{C.GOLD}{C.BOLD} ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝{C.RESET}",
        "",
        f"{C.YELLOW}{C.BOLD}          ██████╗ ██╗  ██╗{C.RESET}",
        f"{C.YELLOW}{C.BOLD}         ██╔════╝ ██║ ██╔╝{C.RESET}",
        f"{C.YELLOW}{C.BOLD}         ╚█████╗  █████╔╝ {C.RESET}",
        f"{C.YELLOW}{C.BOLD}          ╚═══██╗ ██╔═██╗ {C.RESET}",
        f"{C.YELLOW}{C.BOLD}         ██████╔╝ ██║  ██╗{C.RESET}",
        f"{C.GOLD}{C.BOLD}         ╚═════╝  ╚═╝  ╚═╝{C.RESET}",
    ]
    for line in HACKER_SK_FINAL:
        print(line)
        time.sleep(0.04)

    print()
    hline("═", C.GOLD)
    print(f"{C.GOLD}{C.BOLD}   ♛  GROK BULK GEN // PIPELINE v2.0  ♛{C.RESET}")
    hline("═", C.GOLD)

    BOOT = [
        "  [♛] Initializing SK exploit framework ...",
        "  [♛] Loading WebSocket injection module ...",
        "  [♛] Bypassing rate-limit firewall ...",
        "  [♛] Hooking pipeline dispatcher ...",
        "  [♛] Arming image extraction engine ...",
        "  [♛] STORAGE ACCESS GRANTED ✔",
        "  [♛] ALL SYSTEMS ARMED. READY TO FIRE.",
    ]
    print()
    for i, msg in enumerate(BOOT):
        col  = C.RED + C.BOLD if i == len(BOOT) - 1 else C.GOLD
        print(f"{col}{msg}{C.RESET}")
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
    gprint(f"  TARGET  : {prompt}", C.YELLOW)
    gprint(f"  PIPE    : {PIPELINE_SIZE} parallel requests", C.CYAN)
    gprint(f"  SAVE TO : {IMG_DIR}", C.CYAN)
    gprint(f"  START   : {time.strftime('%H:%M:%S')}", C.CYAN)
    hline()
    gprint("  [SYS] Establishing WebSocket tunnel ...", C.MAGENTA)

    async with websockets.connect(
        URI,
        **{_HEADERS_KWARG: HEADERS},
        compression="deflate",
        ping_interval=20,
        ping_timeout=10
    ) as ws:

        gprint("  [SYS] TUNNEL ESTABLISHED ✔", C.GREEN)
        gprint(f"  [SYS] Flooding pipeline [{PIPELINE_SIZE} reqs] ...", C.MAGENTA)

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

        gprint(f"  [SYS] Pipeline active. Intercepting streams ...\n", C.MAGENTA)
        hline("─", C.DIM)

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
            except asyncio.TimeoutError:
                gprint("  [WARN] Idle — re-injecting ...", C.YELLOW)
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
                    crown  = f"{C.GOLD}{C.BOLD}[♛]{C.RESET}"
                    num    = f"{C.BOLD}{C.WHITE}[{total_saved:04d}]{C.RESET}"
                    jid    = f"{C.DIM}{C.CYAN}{short_id}{C.RESET}"
                    name   = f"{C.GREEN}{fname}{C.RESET}"
                    stats  = f"{C.DIM}{C.YELLOW}| {rate:.1f}/s | {elapsed}s{C.RESET}"
                    print(f"  {crown} {num} {jid} → {name} {stats}", flush=True)

            if req_id and req_id in in_flight:
                active = req_active.get(req_id, set())
                done   = req_done.get(req_id, 0)
                if done >= 1 and len(active) == 0:
                    in_flight.discard(req_id)
                    await send_request()


def main():
    banner()
    hline("═", C.GOLD)
    gprint(f"  {C.GOLD}♛{C.RESET} GROK UNLIMITED  //  BULK MODE", C.BOLD + C.WHITE)
    gprint("  [!] Ctrl+C to stop at any time", C.RED)
    hline("═", C.GOLD)
    print()

    prompt = input(f"  {C.GOLD}[♛]{C.RESET} Enter target prompt: ").strip()
    if not prompt:
        gprint("  [!] No prompt. Aborting.", C.RED)
        return

    print()
    try:
        asyncio.run(run_forever(prompt))
    except KeyboardInterrupt:
        print()
        hline("═", C.RED)
        gprint("  [!] SESSION TERMINATED", C.RED + C.BOLD)
        hline("═", C.RED)
    except Exception as e:
        gprint(f"\n  [ERR] {e}", C.RED)


if __name__ == "__main__":
    main()
