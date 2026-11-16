#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
递归把文件夹（含子文件夹）里的 TTF 字体转换为 WOFF2。

依赖：
    pip install fonttools brotli

用法：
    python ttf2woff2.py                                  # 交互式输入路径
    python ttf2woff2.py <path>
    python ttf2woff2.py <path> -j 4            # 4 进程并行（CJK 字体较慢，推荐）
    python ttf2woff2.py <path> --otf           # 连 .otf 一起转
    python ttf2woff2.py <path> -f              # 覆盖已存在的 .woff2

输出：转换结果写在源文件同目录，文件名相同、后缀为 .woff2。
"""

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("缺少依赖 fonttools，请先执行：pip install fonttools brotli")

try:  # 避免个别中文文件名在旧控制台报编码错
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


# --------------------------------------------------------------------------- #
# 单个文件转换（顶层函数，便于多进程 pickle）
# --------------------------------------------------------------------------- #
def convert_one(src: str, force: bool = False):
    """返回 (src, status, message)，status ∈ {'ok', 'skip', 'fail'}"""
    src_path = Path(src)
    dst_path = src_path.with_suffix(".woff2")

    if dst_path.exists() and not force:
        return src, "skip", ""

    try:
        font = TTFont(src_path, lazy=False)
        font.flavor = "woff2"
        font.save(str(dst_path))
        font.close()
        return src, "ok", ""
    except Exception as e:  # 字体损坏 / 表不兼容 / 磁盘错误等
        try:
            if dst_path.exists():      # 清理写了一半的坏文件
                dst_path.unlink()
        except Exception:
            pass
        return src, "fail", f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
# 进度条
# --------------------------------------------------------------------------- #
def fmt_time(sec: float) -> str:
    sec = max(0.0, sec)
    if sec < 60:
        return f"{sec:4.1f}s"
    m, s = divmod(int(sec), 60)
    return f"{m:d}m{s:02d}s"


def draw_progress(done: int, total: int, start: float, current: str, width: int = 28):
    ratio = done / total if total else 1.0
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    elapsed = time.time() - start
    eta = elapsed / done * (total - done) if done else 0.0
    name = current if len(current) <= 34 else "…" + current[-33:]
    line = (f"\r[{bar}] {done}/{total} {ratio * 100:5.1f}%  "
            f"{fmt_time(elapsed)} / 剩 {fmt_time(eta)}  {name:<34}")
    sys.stdout.write(line + "\033[K")
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="递归把 TTF 转换成 WOFF2")
    ap.add_argument("path", nargs="?", default=None, help="字体文件夹路径")
    ap.add_argument("-f", "--force", action="store_true", help="覆盖已存在的 .woff2")
    ap.add_argument("-j", "--jobs", type=int, default=1, help="并行进程数（默认 1）")
    ap.add_argument("--otf", action="store_true", help="同时转换 .otf 文件")
    args = ap.parse_args()

    root = args.path
    if not root:
        root = input("请输入文件夹路径: ").strip().strip('"').strip("'")
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        sys.exit(f"路径不存在或不是文件夹：{root_path}")

    exts = {".ttf"}
    if args.otf:
        exts.add(".otf")

    files = sorted(
        str(p) for p in root_path.rglob("*")
        if p.is_file() and p.suffix.lower() in exts
    )
    total = len(files)
    if total == 0:
        sys.exit(f"在 {root_path} 下没有找到 {', '.join(sorted(exts))} 文件。")

    print(f"共找到 {total} 个字体文件，开始转换…\n")

    done = ok = skip = fail = 0
    errors = []
    start = time.time()
    draw_progress(0, total, start, "准备中…")

    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(convert_one, f, args.force): f for f in files}
            for fut in as_completed(futures):
                src, status, msg = fut.result()
                done += 1
                if status == "ok":
                    ok += 1
                elif status == "skip":
                    skip += 1
                else:
                    fail += 1
                    errors.append((src, msg))
                draw_progress(done, total, start, Path(src).name)
    else:
        for f in files:
            draw_progress(done, total, start, Path(f).name)   # 先显示当前文件名
            src, status, msg = convert_one(f, args.force)
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                errors.append((src, msg))
            draw_progress(done, total, start, Path(src).name)

    sys.stdout.write("\n")
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"完成：成功 {ok} 个 | 跳过 {skip} 个 | 失败 {fail} 个 | 耗时 {fmt_time(elapsed)}")
    if errors:
        print("\n失败列表：")
        for src, msg in errors:
            print(f"  ✗ {src}\n      {msg}")
    print("=" * 60)


if __name__ == "__main__":
    main()