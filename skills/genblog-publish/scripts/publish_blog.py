#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a ttwe77s-homepage blog post from one Markdown file and one SVG icon.

Steps: Markdown -> blog/<stem>.html -> page1.ini -> font subsets -> rss.xml.

HARD RULE: this script never runs git commit, git push, git add, or any other
git write command. All git invocations, if any, must be read-only and explicit.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def fail(message: str) -> "NoReturn":
    print(f"[错误] {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd, cwd: Path, input_text: str | None = None, dry_run: bool = False) -> None:
    printable = " ".join(str(c) for c in cmd)
    print(f"[cmd] {printable}    (cwd={cwd})")
    if dry_run:
        return
    subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd),
        input=input_text,
        text=True,
        check=True,
    )


def parse_front_matter(text: str) -> tuple[dict, str]:
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if line.startswith((" ", "\t")):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1:])


def description_from_body(body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "```", ":::", "|", "<", "---")):
            continue
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"[*_`~\[\]]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            return s[:120]
    return ""


def normalize_icon(raw: str) -> str:
    raw = re.sub(r"<\?xml.*?\?>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"\s+", " ", raw).strip()
    low = raw.lower()
    if not low.startswith("<svg") or "</svg>" not in low:
        raise ValueError("图标必须是 <svg>...</svg> 文本或包含 SVG 的文件路径")
    # page1.ini uses "|" as the field separator.
    return raw.replace("|", "&#124;")


def ini_field(value) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "")).replace("|", "&#124;").strip()


def update_page_ini(path: Path, html_name: str, new_line: str) -> str:
    raw = path.read_text(encoding="utf-8-sig")
    had_newline = raw.endswith(("\n", "\r"))
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()

    found = None
    for i, line in enumerate(lines):
        if line.strip().startswith(("#", ";")):
            continue
        if line.split("|", 1)[0].strip() == html_name:
            found = i
            break

    if found is None:
        lines.append(new_line)
        action = "added"
    else:
        lines[found] = new_line
        action = "updated"

    out = newline.join(lines)
    if had_newline:
        out += newline
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(out)
    return action


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a blog post into blog/ without any git commit/push"
    )
    parser.add_argument("md", help="Markdown source path")
    parser.add_argument("icon", help="SVG file path or inline <svg>...</svg> text")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Project root")
    parser.add_argument("--skip-fonts", action="store_true", help="Skip subset_fonts.py")
    parser.add_argument("--skip-rss", action="store_true", help="Skip genrss.py")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan only")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    genblog = root / "tools" / "genblog"
    docs = genblog / "docs"
    parts = genblog / "parts"
    blog = root / "blog"
    blog_fonts = blog / "fonts"
    page_ini = blog / "pages" / "page1.ini"
    md2page = genblog / "md2page.py"
    split_page = genblog / "split_page.py"
    subset_fonts = genblog / "subset_fonts.py"
    genrss = root / "tools" / "rss" / "genrss.py"
    rss_path = root / "rss.xml"

    for required in (docs, blog, page_ini, md2page, genrss):
        if not required.exists():
            fail(f"缺少必需路径: {required}")

    # Resolve Markdown path: cwd-relative first, then project-root-relative.
    md_candidate = Path(args.md).expanduser()
    if not md_candidate.is_absolute() and not md_candidate.exists():
        md_candidate = root / md_candidate
    md_path = md_candidate.resolve()
    if not md_path.is_file():
        fail(f"找不到 Markdown 文件: {md_path}")

    raw_md = md_path.read_text(encoding="utf-8-sig")
    meta, body = parse_front_matter(raw_md)
    stem = md_path.stem
    html_name = stem + ".html"

    missing = [key for key in ("date", "updated") if not meta.get(key)]
    if missing:
        fail(f"{md_path.name} 的 front matter 缺少必需字段: {', '.join(missing)}")

    # Resolve icon: file path first, then inline SVG text.
    icon_candidate = Path(args.icon).expanduser()
    if icon_candidate.is_file():
        icon_raw = icon_candidate.read_text(encoding="utf-8-sig")
    else:
        root_icon = root / icon_candidate if not icon_candidate.is_absolute() else icon_candidate
        if root_icon.is_file():
            icon_raw = root_icon.read_text(encoding="utf-8-sig")
        else:
            icon_raw = args.icon
    try:
        icon = normalize_icon(icon_raw)
    except ValueError as exc:
        fail(str(exc))

    title = meta.get("title") or stem
    description = meta.get("description") or description_from_body(body)
    category = meta.get("category") or "未分类"
    tags = re.split(r"[,，]", meta.get("tags", ""))
    tags_text = ",".join(t.strip() for t in tags if t.strip())

    line = " | ".join(
        [
            ini_field(html_name),
            ini_field(title),
            ini_field(meta["date"]),
            ini_field(category),
            ini_field(tags_text),
            ini_field(description),
            ini_field(icon),
        ]
    )

    doc_for_rss = md_path
    try:
        md_path.relative_to(docs)
    except ValueError:
        doc_for_rss = docs / f"{stem}.md"
        if doc_for_rss.exists() and doc_for_rss.resolve() != md_path:
            fail(f"docs 中已存在同名文件，拒绝覆盖: {doc_for_rss}")
        print(f"[copy] {md_path} -> {doc_for_rss}")

    out_html = blog / html_name
    plan = [
        f"[plan] Markdown : {md_path}",
        f"[plan] RSS lookup: {doc_for_rss}",
        f"[plan] HTML out : {out_html}",
        f"[plan] INI line : {line[:400]}{'...' if len(line) > 400 else ''}",
    ]
    print("\n".join(plan))

    if args.dry_run:
        if not (parts / "style.css").is_file() or not (parts / "head.html").is_file():
            run([sys.executable, str(split_page), str(genblog / "sample.html"), "-o", str(parts)],
                cwd=genblog, dry_run=True)
        run([sys.executable, str(md2page), str(doc_for_rss), "-p", str(parts), "-o", str(out_html)],
            cwd=genblog, dry_run=True)
        if not args.skip_fonts:
            run([sys.executable, str(subset_fonts)], cwd=root, dry_run=True)
        if not args.skip_rss:
            run([sys.executable, str(genrss)], cwd=root, input_text="y\n", dry_run=True)
        print("[dry-run] 未写入任何文件；未执行任何 git 命令。")
        return 0

    if not doc_for_rss.parent.is_dir():
        doc_for_rss.parent.mkdir(parents=True, exist_ok=True)
    if doc_for_rss != md_path:
        shutil.copy2(md_path, doc_for_rss)

    if not (parts / "style.css").is_file() or not (parts / "head.html").is_file():
        run([sys.executable, str(split_page), str(genblog / "sample.html"), "-o", str(parts)],
            cwd=genblog)

    run([sys.executable, str(md2page), str(doc_for_rss), "-p", str(parts), "-o", str(out_html)],
        cwd=genblog)
    if not out_html.is_file():
        fail(f"md2page.py 未生成预期文件: {out_html}")

    action = update_page_ini(page_ini, html_name, line)
    print(f"[ini] {page_ini.name}: {action} -> {html_name}")

    if not args.skip_fonts:
        if not blog_fonts.is_dir():
            fail(f"缺少字体输出目录: {blog_fonts}")
        run([sys.executable, str(subset_fonts)], cwd=root)

    if not args.skip_rss:
        run([sys.executable, str(genrss)], cwd=root, input_text="y\n")
        if rss_path.is_file() and html_name not in rss_path.read_text(encoding="utf-8", errors="ignore"):
            print(f"[warn] {rss_path.name} 中未找到 {html_name}，请检查 front matter 与清单。",
                  file=sys.stderr)

    print(f"[done] 构建完成: {out_html}")
    print("[done] 未执行 git commit / git push / git add，改动仅保留在工作区。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
