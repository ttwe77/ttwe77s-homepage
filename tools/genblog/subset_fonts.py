#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「七七柔和圆体」（CSS 别名 Blog-WenYuan）子集，供 blog/*.html 使用。

两层结构：
    1. 主字体 Blog-WenYuan          —— 全站博客实际用字（自动重建，体积最小）
       输出到 blog/fonts/（不走 /src 的长缓存）
    2. 兜底 Blog-WenYuan-Fallback   —— 《通用规范汉字表》8105 字（只建一次）
       输出到 src/ttf/fonts/standard-round/subset/fallback/（/src 长缓存，基本不变）

CSS 字体栈为：
    'Blog-WenYuan', 'Blog-WenYuan-Fallback', var(--font-fallback)
浏览器按字符回退：主字体缺字时才去下载兜底字体，所以日常页面不会碰它。
即“忘了重新生成子集”也不会出现豆腐块，只是那几个字慢一点。

只处理页面真正用到的三个字重：Regular(400)、SemiBold(500-600)、Bold(700-900)。

依赖：
    pip install fonttools brotli

用法：
    python tools/genblog/subset_fonts.py          # 增量生成（字集没变就跳过）
    python tools/genblog/subset_fonts.py -j 3     # 限制并行进程数（默认 CPU 核数）
    python tools/genblog/subset_fonts.py -f       # 全部强制重建
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "src" / "ttf" / "fonts" / "standard-round"
# /src 配了长缓存，会随文章更新的主字体放在 blog/fonts；兜底字体基本不变，留在 /src
SITE_DIR = ROOT / "blog" / "fonts"
FALLBACK_DIR = FONT_DIR / "subset" / "fallback"
CHARS_8105 = ROOT / "tools" / "genblog" / "data" / "charset-8105.txt"
BLOG_DIR = ROOT / "blog"

# 字重 -> CSS font-weight（与 parts/style.css 保持一致）
WEIGHTS = {
    "Regular": "400",
    "SemiBold": "500 600",
    "Bold": "700 900",
}

# 字体选择弹窗里的预览文案，避免预览时缺字
EXTRA_TEXT = "永字八法，天地玄黄。汉字排版预览 AaBbCc 0123456789"

ASCII = "".join(chr(c) for c in range(0x20, 0x7F))


def _printable(chars):
    return {c for c in chars if c.isprintable() or c == "\u3000"}


def site_charset() -> set:
    """全站博客实际用字（去标签后的正文 + 预览文案 + ASCII）。"""
    chars = set(EXTRA_TEXT) | set(ASCII)
    html_files = sorted(BLOG_DIR.glob("*.html"))
    if not html_files:
        sys.exit(f"在 {BLOG_DIR} 下没有找到 html 文件")
    for p in html_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        chars.update(re.sub(r"<[^>]+>", " ", text))
    return _printable(chars)


def tghz_charset() -> set:
    """《通用规范汉字表》8105 字 + 预览文案 + ASCII。"""
    if not CHARS_8105.is_file():
        sys.exit(f"缺少字表文件：{CHARS_8105}")
    chars = set(CHARS_8105.read_text(encoding="utf-8"))
    chars.update(EXTRA_TEXT)
    chars.update(ASCII)
    return _printable(chars)


def build_job(args):
    """顶层函数，便于多进程。返回 (mode, weight, status, size_kb, seconds, message)"""
    mode, weight, chars_file, out_dir, force = args
    src = FONT_DIR / f"77StandardRound-{weight}.woff2"
    dst = out_dir / f"77StandardRound-{weight}.woff2"

    if dst.exists() and not force:
        return mode, weight, "skip", dst.stat().st_size / 1024, 0.0, ""

    t0 = time.time()
    try:
        proc = subprocess.run(
            [
                "pyftsubset", str(src),
                f"--text-file={chars_file}",
                f"--output-file={dst}",
                "--flavor=woff2",
                "--layout-features=*",
                "--no-hinting",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return mode, weight, "fail", 0.0, time.time() - t0, f"{type(exc).__name__}: {exc}"
    dt = time.time() - t0
    if proc.returncode != 0:
        try:
            dst.unlink()
        except OSError:
            pass
        detail = (proc.stderr or proc.stdout or "").strip()[-400:]
        return mode, weight, "fail", 0.0, dt, detail or f"pyftsubset 退出码 {proc.returncode}"
    return mode, weight, "ok", dst.stat().st_size / 1024, dt, ""


def plan_mode(mode, charset, force, require_all, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    text = "".join(sorted(charset))
    digest = hashlib.sha1((text + "|" + ",".join(WEIGHTS)).encode("utf-8")).hexdigest()

    state_file = out_dir / "subset.json"
    old = {}
    if state_file.is_file():
        try:
            old = json.loads(state_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            old = {}

    changed = old.get("charset_sha1") != digest
    missing = [w for w in WEIGHTS if not (out_dir / f"77StandardRound-{w}.woff2").is_file()]
    # 主字体：字集变化就重建；兜底字体：不存在才建，避免每次改文章都重算 8105
    rebuild = force or (changed if require_all else bool(missing))

    if rebuild:
        (out_dir / "charset-used.txt").write_text(text, encoding="utf-8")
        note = "字集变化" if changed else ("强制" if force else "缺少产物")
        print(f"  {mode:<8} {len(charset):>5} 字  → 需生成（{note}）")
    else:
        print(f"  {mode:<8} {len(charset):>5} 字  → 已是最新，跳过")

    return {
        "mode": mode,
        "dir": out_dir,
        "state_file": state_file,
        "digest": digest,
        "chars": len(charset),
        "rebuild": rebuild,
        "chars_file": str(out_dir / "charset-used.txt"),
    }


def main():
    ap = argparse.ArgumentParser(description="生成七七柔和圆体子集（主字体 + 兜底字体）")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1,
                    help="并行进程数（默认 CPU 核数）")
    ap.add_argument("-f", "--force", action="store_true", help="忽略状态，全部强制重建")
    args = ap.parse_args()

    if not FONT_DIR.is_dir():
        sys.exit(f"字体目录不存在：{FONT_DIR}")
    missing_src = [w for w in WEIGHTS if not (FONT_DIR / f"77StandardRound-{w}.woff2").is_file()]
    if missing_src:
        sys.exit("缺少源字体：" + "、".join(f"77StandardRound-{w}.woff2" for w in missing_src))

    print("收集字符集…")
    plans = [
        plan_mode("site", site_charset(), args.force, True, SITE_DIR),
        plan_mode("fallback", tghz_charset(), args.force, False, FALLBACK_DIR),
    ]

    tasks = []
    for p in plans:
        if p["rebuild"]:
            tasks += [(p["mode"], w, p["chars_file"], p["dir"], args.force) for w in WEIGHTS]

    results = {}
    if tasks:
        print(f"\n开始生成 {len(tasks)} 个文件（{min(args.jobs, len(tasks))} 并行）…\n")
        with ProcessPoolExecutor(max_workers=max(1, min(args.jobs, len(tasks)))) as pool:
            futures = [pool.submit(build_job, t) for t in tasks]
            for fut in as_completed(futures):
                mode, weight, status, kb, dt, msg = fut.result()
                results[(mode, weight)] = status
                if status == "ok":
                    print(f"  ✓ {mode:<8} {weight:<9} {kb:>8.0f} KB   {dt:5.1f}s")
                else:
                    print(f"  ✗ {mode:<8} {weight:<9} 失败：{msg}")
    else:
        print("\n所有字体均为最新，无需生成。")

    if any(s == "fail" for s in results.values()):
        print("\n存在失败项，未写入状态文件。")
        sys.exit(1)

    total = 0
    for p in plans:
        files = sorted(p["dir"].glob("77StandardRound-*.woff2"))
        sub = sum(f.stat().st_size for f in files) / 1024
        total += sub
        print(f"\n{p['mode']}: {len(files)} 个文件，合计 {sub:.0f} KB")
        p["state_file"].write_text(json.dumps({
            "charset_sha1": p["digest"],
            "chars": p["chars"],
            "files": {w: f"77StandardRound-{w}.woff2" for w in WEIGHTS},
            "weights": WEIGHTS,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n合计 {total:.0f} KB")
    print(f"  主字体：{SITE_DIR}")
    print(f"  兜底：  {FALLBACK_DIR}")


if __name__ == "__main__":
    main()
