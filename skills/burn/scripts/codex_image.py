#!/usr/bin/env python3
"""Generate one image with Codex's built-in image tool, for a Claude-run burn.

Python 3.11+, standard library only. Tested with codex-cli 0.162.

    python codex_image.py --prompt "flat dark green app icon ..." --out public/icon-512.png
    python codex_image.py --check          # is Codex usable for images right now? (no image made)

It uses the person's own Codex (ChatGPT) subscription, so it checks that budget too:
  - `codex` is on PATH and `codex login status` succeeds
  - [assets] in config.toml allows it (codex_images = "auto" or "on")
  - Codex's own weekly usage is under assets.codex_max_weekly_pct (default 80)

Codex runs with a read-only sandbox, in an empty temp folder, with stdin closed. It
gets no write access and no extra network: the image tool runs on Codex's side and
saves the PNG under ~/.codex/generated_images/. This script copies that file to --out
after checking it really is a PNG.

Output: one JSON object. Exit 0 on success (or --check passing), 1 on failure,
2 when Codex isn't available or allowed (not an error: fall back to other assets).
"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DEFAULT_MAX_PCT = 80.0
TIMEOUT_S = 300


def burn_home() -> Path:
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


def codex_home() -> Path:
    env = os.environ.get("CODEX_HOME")
    return Path(env).expanduser() if env else Path.home() / ".codex"


def load_assets_config() -> dict:
    path = burn_home() / "config.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh).get("assets", {})


def codex_bin() -> str | None:
    return os.environ.get("BURN_CODEX_BIN") or shutil.which("codex")


def png_size(path: Path) -> tuple[int, int] | None:
    """(width, height) if the file is a PNG, else None."""
    try:
        with path.open("rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != PNG_MAGIC or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def codex_weekly_pct() -> float | None:
    """Codex's weekly used %, from its session logs (see usage.py)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import usage  # noqa: PLC0415 (sibling script, stdlib only)
    except ImportError:
        return None
    r = usage.read_codex()
    return r["weekly"]["used_pct"] if r.get("ok") else None


def availability(cfg: dict) -> dict:
    """Why Codex can or can't make images right now."""
    mode = str(cfg.get("codex_images", "auto")).lower()
    if mode == "off":
        return {"ok": False, "reason": "assets.codex_images is off in config.toml"}
    exe = codex_bin()
    if not exe:
        return {"ok": False, "reason": "the codex CLI isn't installed (or not on PATH)"}
    try:
        status = subprocess.run([exe, "login", "status"], capture_output=True, text=True,
                                timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "reason": f"couldn't run codex: {e}"}
    if status.returncode != 0:
        return {"ok": False, "reason": "codex isn't logged in (run `codex login`)"}
    limit = float(cfg.get("codex_max_weekly_pct", DEFAULT_MAX_PCT))
    used = codex_weekly_pct()
    if used is not None and used >= limit:
        return {"ok": False, "reason": f"Codex weekly usage is {used}%, at or over the {limit}% set for assets",
                "codex_weekly_pct": used}
    return {"ok": True, "codex": exe, "login": (status.stdout or status.stderr).strip(), "codex_weekly_pct": used,
            "limit_pct": limit, "note": None if used is not None else "Codex usage unknown; going ahead"}


def build_prompt(prompt: str) -> str:
    return (
        "$imagegen Generate exactly one image. "
        f"{prompt.strip()} "
        "Then reply with only the absolute path of the generated PNG file, nothing else."
    )


def find_path(text: str) -> Path | None:
    """The last line of Codex's reply that is an existing .png path."""
    for line in reversed([ln.strip().strip("`\"'") for ln in text.splitlines()]):
        if line.lower().endswith(".png") and Path(line).is_file():
            return Path(line)
    return None


def generate(prompt: str, out: Path, exe: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="burn-img-") as tmp:
        last = Path(tmp) / "last-message.txt"
        cmd = [exe, "exec", "--skip-git-repo-check", "-s", "read-only", "-C", tmp,
               "-o", str(last), build_prompt(prompt)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S,
                                  stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": f"codex took longer than {TIMEOUT_S}s"}
        reply = last.read_text(encoding="utf-8", errors="replace") if last.is_file() else ""
        src = find_path(reply) or find_path(proc.stdout or "")
        if proc.returncode != 0 or src is None:
            return {"ok": False, "reason": "codex didn't return a PNG path",
                    "exit_code": proc.returncode, "reply": reply[-500:]}
    # Only accept files Codex's image tool wrote, never an arbitrary path from the reply.
    try:
        src.resolve().relative_to((codex_home() / "generated_images").resolve())
    except ValueError:
        return {"ok": False, "reason": f"codex returned a path outside its generated_images folder: {src}"}
    size = png_size(src)
    if size is None:
        return {"ok": False, "reason": f"{src} isn't a valid PNG"}
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    return {"ok": True, "path": str(out), "source": str(src), "width": size[0], "height": size[1],
            "bytes": out.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", help="what to draw (no text in the image, no real people, no logos)")
    ap.add_argument("--out", help="where to save the PNG, e.g. public/og-image.png")
    ap.add_argument("--check", action="store_true", help="only check that Codex is usable")
    args = ap.parse_args(argv)

    avail = availability(load_assets_config())
    if args.check or not avail["ok"]:
        print(json.dumps(avail))
        return 0 if avail["ok"] else 2
    if not args.prompt or not args.out:
        ap.error("--prompt and --out are required")
    before = avail.get("codex_weekly_pct")
    result = generate(args.prompt, Path(args.out), avail["codex"])
    result["codex_weekly_pct_before"] = before
    result["codex_weekly_pct_after"] = codex_weekly_pct()
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
