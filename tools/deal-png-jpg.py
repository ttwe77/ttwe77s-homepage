#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式输入 PNG / JPG 路径，在相同目录下生成同名 .webp 与 .avif 文件。
统计每个转换任务的耗时、总用时，并输出原始图片大小。

依赖 ImageMagick 7（magick 命令）：
    magick input.png -quality 50 -define webp:method=6 output.webp
    magick input.png -quality 50 -define heic:speed=0  output.avif
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg"}


def run_magick(cmd: list[str]) -> bool:
    """执行一条 magick 命令，返回是否成功。"""
    printable = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    print(f"  $ {printable}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("  ✗ 找不到 magick 命令，请确认已安装 ImageMagick 7 并加入 PATH。")
        return False

    if result.returncode != 0:
        print("  ✗ 失败：")
        print("   ", (result.stderr or result.stdout).strip())
        return False

    print("  ✓ 成功")
    return True


def ask_input_path() -> Path | None:
    """交互式获取并校验输入文件路径。"""
    raw = input("请输入 PNG / JPG 文件路径（可直接把文件拖进终端）：").strip()
    raw = raw.strip('"').strip("'")          # 去掉拖拽产生的引号
    if not raw:
        print("没有输入任何路径，已退出。")
        return None

    src = Path(raw).expanduser()
    try:
        src = src.resolve(strict=True)
    except FileNotFoundError:
        print(f"文件不存在：{src}")
        return None

    if not src.is_file():
        print(f"这不是一个文件：{src}")
        return None

    if src.suffix.lower() not in SUPPORTED_SUFFIXES:
        print(f"只支持 {'/'.join(sorted(SUPPORTED_SUFFIXES))}，当前后缀为：{src.suffix or '(无)'}")
        return None

    return src


def main() -> int:
    if shutil.which("magick") is None:
        print("警告：在 PATH 中未找到 magick，后续命令可能无法执行。\n")

    src = ask_input_path()
    if src is None:
        return 1

    # 同目录、同文件名，只换扩展名
    webp_out = src.with_suffix(".webp")
    avif_out = src.with_suffix(".avif")

    jobs = [
        ("WebP", [
            "magick", str(src),
            "-quality", "50",
            "-define", "webp:method=6",
            str(webp_out),
        ]),
        ("AVIF", [
            "magick", str(src),
            "-quality", "50",
            "-define", "heic:speed=0",
            str(avif_out),
        ]),
    ]

    total_start = time.time()
    all_ok = True

    for name, cmd in jobs:
        print(f"\n[{name}] 正在生成 …")
        job_start = time.time()
        ok = run_magick(cmd)
        job_elapsed = time.time() - job_start
        print(f"  ⏱ 耗时: {job_elapsed:.2f} 秒")
        if not ok:
            all_ok = False

    total_elapsed = time.time() - total_start
    print(f"\n⏱ 总用时: {total_elapsed:.2f} 秒")

    print("\n处理结束，输出目录：", src.parent)

    # 输出原始图片大小
    orig_size_kb = src.stat().st_size / 1024
    print(f"原图 ({src.name}) 大小: {orig_size_kb:.1f} KB")

    # 输出生成文件大小
    for out in (webp_out, avif_out):
        if out.exists():
            print(f"  - {out.name}  ({out.stat().st_size / 1024:.1f} KB)")
        else:
            print(f"  - {out.name}  (未生成)")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())