#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一步：从已有的 HTML 页面中把「可复用的页面元素」拆出来。

用法：
    python split_page.py index.html -o parts

产出（parts/ 目录）：
    style.css            全局设计令牌 + 全部样式
    head.html            <head>（已把 <style> 替换为占位注释）
    topbar.html          顶栏
    read_progress.html   阅读进度条
    article_head.html    文章头部（eyebrow / 标题 / 摘要 / 元信息 / 标签）
    article_body.html    正文卡片容器（<div id="article-body">）
    toc.html             侧栏目录
    to_top.html          回到顶部按钮
    footer.html          页脚
    scripts.html         页面底部全部 <script>
    manifest.json        清单（标签 / 类名 / 行号 / 大小）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# 标签扫描
# --------------------------------------------------------------------------

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# <  可选的/  标签名  属性区(可含引号内的 >)  可选的/  >
TAG_RE = re.compile(
    r'<(/?)([a-zA-Z][-\w:]*)((?:"[^"]*"|\'[^\']*\'|[^"\'>])*?)(/?)>',
    re.S,
)

ATTR_RE = re.compile(
    r'([-\w:.@]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+)))?'
)


def parse_attrs(raw: str) -> dict:
    """把标签里的属性字符串解析成 dict。"""
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        val = m.group(2)
        if val is None:
            val = m.group(3)
        if val is None:
            val = m.group(4)
        if val is None:
            val = ""
        out[m.group(1).lower()] = val
    return out


def compute_skip_spans(html: str):
    """注释、<script> 内部、<style> 内部的内容不参与标签扫描。"""
    spans = []
    for m in re.finditer(r"<!--.*?-->", html, re.S):
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"<(script|style)\b[^>]*>(.*?)</\1\s*>", html, re.S | re.I):
        spans.append((m.start(2), m.end(2)))
    spans.sort()
    return spans


def parse_elements(html: str):
    """
    用一个小型栈式扫描器找出所有元素的开闭位置。
    返回 [{tag, raw, attrs_raw, attrs, start, end}, ...]（按出现顺序）。
    """
    skips = compute_skip_spans(html)

    def skip_end(pos):
        for s, e in skips:
            if s <= pos < e:
                return e
        return None

    elements, stack = [], []
    i, n = 0, len(html)

    while i < n:
        lt = html.find("<", i)
        if lt < 0:
            break

        jump = skip_end(lt)
        if jump is not None:
            i = jump
            continue

        m = TAG_RE.match(html, lt)
        if not m:
            i = lt + 1
            continue

        closing = m.group(1)
        name = m.group(2).lower()
        attrs_raw = m.group(3)
        self_closing = m.group(4)

        # ---------- 闭合标签 ----------
        if closing:
            for k in range(len(stack) - 1, -1, -1):
                if stack[k]["tag"] == name:
                    el = stack[k]
                    el["end"] = m.end()
                    el["children"] = stack[k + 1:]
                    del stack[k:]
                    elements.append(el)
                    # 顺带把没闭合的子孙收尾，避免它们丢失
                    for child in el["children"]:
                        if child["end"] is None:
                            child["end"] = child["start"] + len(child["raw"])
                            elements.append(child)
                    break
            i = m.end()
            continue

        # ---------- 开始标签 ----------
        el = {
            "tag": name,
            "raw": m.group(0),
            "attrs_raw": attrs_raw,
            "attrs": parse_attrs(attrs_raw),
            "start": m.start(),
            "end": None,
        }

        if name in VOID_ELEMENTS or self_closing:
            el["end"] = m.end()
            elements.append(el)
        else:
            stack.append(el)

        i = m.end()

    # 栈里剩下的（文档截断 / 未闭合）
    for el in stack:
        el["end"] = el["start"] + len(el["raw"])
        elements.append(el)

    elements.sort(key=lambda e: (e["start"], e["end"]))
    return elements


# --------------------------------------------------------------------------
# 查找 & 切片
# --------------------------------------------------------------------------

def find_all(elements, tag=None, cls=None, eid=None, **attrs):
    hits = []
    for el in elements:
        if el.get("end") is None:
            continue
        if tag and el["tag"] != tag:
            continue
        if eid and el["attrs"].get("id") != eid:
            continue
        if cls and cls not in (el["attrs"].get("class") or "").split():
            continue
        if attrs and any(el["attrs"].get(k) != v for k, v in attrs.items()):
            continue
        hits.append(el)
    return hits


def outer(el, html: str) -> str:
    return html[el["start"]:el["end"]]


def inner(el, html: str) -> str:
    lt = html.find(">", el["start"])
    if lt < 0:
        return ""
    close = html.rindex("<", lt, el["end"])
    return html[lt + 1:close]


def line_range(html: str, el) -> tuple:
    return (html.count("\n", 0, el["start"]) + 1,
            html.count("\n", 0, el["end"]) + 1)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

TARGETS = [
    # key             输出文件                取法     查找条件
    ("head",          "head.html",           "outer", dict(tag="head")),
    ("style",         "style.css",           "inner", dict(tag="style")),
    ("topbar",        "topbar.html",         "outer", dict(tag="header", cls="topbar")),
    ("read_progress", "read_progress.html",  "outer", dict(tag="div", cls="read-progress")),
    ("article_head",  "article_head.html",   "outer", dict(tag="header", cls="article-head")),
    ("article_body",  "article_body.html",   "outer", dict(tag="div", eid="article-body")),
    ("toc",           "toc.html",            "outer", dict(tag="aside", cls="toc")),
    ("toc_toggle",    "toc_toggle.html",     "outer", dict(tag="button", eid="toc-toggle")),
    ("to_top",        "to_top.html",         "outer", dict(tag="button", eid="to-top")),
    ("footer",        "footer.html",         "outer", dict(tag="footer", cls="footer")),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="从 HTML 中分离可复用的页面元素")
    ap.add_argument("html_file", help="源 HTML 文件")
    ap.add_argument("-o", "--out", default="parts", help="输出目录（默认 parts）")
    args = ap.parse_args(argv)

    src = Path(args.html_file)
    if not src.is_file():
        print(f"找不到文件：{src}", file=sys.stderr)
        return 1

    html = src.read_text(encoding="utf-8")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    elements = parse_elements(html)
    manifest = {"source": str(src), "parts": {}}
    rows = []

    # ---------- 逐块抽取 ----------
    for key, filename, mode, cond in TARGETS:
        hits = find_all(elements, **cond)
        if not hits:
            print(f"  ! 未找到：{key}  ({cond})", file=sys.stderr)
            continue

        el = hits[0]
        text = outer(el, html) if mode == "outer" else inner(el, html)

        # <head> 里的 <style> 已被单独抽出，这里替换成占位注释
        if key == "head":
            style_hits = find_all(elements, tag="style")
            if style_hits:
                text = text.replace(
                    outer(style_hits[0], html),
                    "<!-- 样式已抽出 → parts/style.css -->",
                )

        if key == "style":
            text = text.strip() + "\n"

        (out_dir / filename).write_text(text, encoding="utf-8")

        l0, l1 = line_range(html, el)
        manifest["parts"][key] = {
            "file": filename,
            "tag": el["tag"],
            "class": el["attrs"].get("class", ""),
            "id": el["attrs"].get("id", ""),
            "line_start": l0,
            "line_end": l1,
            "chars": len(text),
        }
        rows.append((key, el["tag"], f"{l0}-{l1}", len(text), filename))

    # ---------- 脚本 ----------
    scripts = find_all(elements, tag="script")
    if scripts:
        chunks = []
        for idx, s in enumerate(scripts, 1):
            inline = inner(s, html).strip()
            head_tag = s["raw"]
            chunks.append(f"<!-- script #{idx} · {head_tag} -->\n" + inline)
        scripts_html = "\n\n".join(chunks) + "\n"
        (out_dir / "scripts.html").write_text(scripts_html, encoding="utf-8")

        l0, l1 = line_range(html, scripts[0])
        manifest["parts"]["scripts"] = {
            "file": "scripts.html",
            "tag": "script",
            "count": len(scripts),
            "line_start": l0,
            "line_end": line_range(html, scripts[-1])[1],
            "chars": len(scripts_html),
        }
        rows.append(("scripts", f"x{len(scripts)}", f"{l0}-{l1}", len(scripts_html), "scripts.html"))

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ---------- 报告 ----------
    print(f"源文件：{src}  ({len(html):,} 字符，{html.count(chr(10)) + 1} 行)")
    print(f"输出目录：{out_dir.resolve()}")
    print()
    print(f'{"KEY":<16}{"TAG":<9}{"LINES":<12}{"SIZE":>9}   FILE')
    print("-" * 66)
    for key, tag, lines, size, filename in rows:
        print(f"{key:<16}{tag:<9}{lines:<12}{size:>8,}B   {filename}")
    print("-" * 66)
    print(f"共 {len(rows)} 个元素 → {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())