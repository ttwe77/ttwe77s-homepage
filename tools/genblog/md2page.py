#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二步：把 Markdown 渲染成与 parts/ 模板一致的博客页面。

用法：
    python md2page.py post.md -p parts -o out.html

Markdown 约定（front matter 用 --- 包起来）：
    ---
    title: CSS 变量：从设计令牌到主题切换
    description: 一句话摘要，支持 `行内代码` 和 **加粗**
    eyebrow: Front-end · Design System
    date: 2026-03-18
    category: 前端
    readtime: 8
    author: 77
    tags: CSS, 设计系统, 主题切换, 重构
    license: CC BY-NC 4.0
    license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
    updated: 2026-03-18
    ---

正文里额外支持：
    ```css / ```js / ```html   围栏代码块（自带语法着色 + 复制按钮）
    :::callout ... :::         黄色提示框
    [[文字|标题|详细说明]]      hover 提示气泡
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
import sys
from pathlib import Path

# ==========================================================================
# 转义工具
# ==========================================================================

def esc(s) -> str:
    """正文用转义：不碰引号，方便后续正则再处理。"""
    return html_mod.escape(str(s), quote=False)


def esc_attr(s) -> str:
    """属性值用转义。"""
    return html_mod.escape(str(s), quote=True)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def replace_between(html: str, start: str, end: str, new: str) -> str:
    """把 html 中 start…end 之间的内容换成 new（保留两端的标记）。"""
    i = html.find(start)
    if i < 0:
        return html
    j = html.find(end, i + len(start))
    if j < 0:
        return html
    return html[: i + len(start)] + new + html[j:]


# ==========================================================================
# 语法着色
# ==========================================================================

CSS_TOKEN_RE = re.compile(
    r"(?P<comment>/\*[\s\S]*?\*/)"
    r"|(?P<str>\"[^\"\n]*\"|'[^'\n]*')"
    r"|(?P<at>@[a-zA-Z-]+)"
    r"|(?P<prop>--[a-zA-Z0-9_-]+)"
    r"|(?P<hex>#[0-9a-fA-F]{3,8}\b)"
    r"|(?P<num>-?(?:\d+\.?\d*|\.\d+)"
    r"(?:px|em|rem|%|s|ms|vh|vw|vmin|vmax|deg|fr|ch|ex|pt)?)"
    r"|(?P<word>[a-zA-Z-]+(?=\s*:))"
)

JS_TOKEN_RE = re.compile(
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)"
    r"|(?P<str>\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)"
    r"|(?P<kw>\b(?:const|let|var|function|return|if|else|for|while|do|new|class"
    r"|extends|import|export|from|default|await|async|try|catch|finally|throw"
    r"|typeof|instanceof|in|of|this|super|null|undefined|true|false|break"
    r"|continue|switch|case|delete|void|yield)\b)"
    r"|(?P<obj>\b(?:document|window|localStorage|sessionStorage|console|Math|JSON"
    r"|Object|Array|String|Number|Boolean|Promise|Date|RegExp|Error|navigator"
    r"|location|history|setTimeout|setInterval|requestAnimationFrame"
    r"|getElementById|querySelector|querySelectorAll|addEventListener"
    r"|classList|dataset|closest|innerHTML|innerText|textContent|style)\b)"
    r"|(?P<num>\b\d+(?:\.\d+)?\b)"
)

_CSS_CLS = {"comment": "tok-com", "str": "tok-str", "at": "tok-at",
            "prop": "tok-prop", "hex": "tok-val", "num": "tok-val",
            "word": "tok-prop"}

_JS_CLS = {"comment": "tok-com", "str": "tok-str", "kw": "tok-sel",
           "obj": "tok-prop", "num": "tok-val"}


def _tokenize(src: str, pattern: re.Pattern, mapping: dict) -> str:
    def repl(m):
        return f'<span class="{mapping[m.lastgroup]}">{m.group(0)}</span>'
    return pattern.sub(repl, src)


def highlight_css(src: str) -> str:
    return _tokenize(esc(src), CSS_TOKEN_RE, _CSS_CLS)


def highlight_js(src: str) -> str:
    return _tokenize(esc(src), JS_TOKEN_RE, _JS_CLS)


def highlight_plain(src: str) -> str:
    return esc(src)


HIGHLIGHTERS = {
    "css": highlight_css,
    "js": highlight_js,
    "javascript": highlight_js,
    "mjs": highlight_js,
    "html": highlight_plain,
    "xml": highlight_plain,
    "svg": highlight_plain,
    "json": highlight_plain,
    "bash": highlight_plain,
    "sh": highlight_plain,
    "shell": highlight_plain,
    "text": highlight_plain,
    "": highlight_plain,
}

LANG_LABEL = {"js": "javascript", "sh": "bash", "": "text"}


# ==========================================================================
# 行内渲染
# ==========================================================================

def hint_html(text: str, title: str, content: str) -> str:
    return (
        f'<span class="hover-hint">{esc(text)}\n'
        f'    <span class="hover-hint__tooltip">\n'
        f'        <span class="hint-title">{esc(title)}</span>\n'
        f'        {esc(content)}\n'
        f'    </span>\n'
        f'</span>'
    )


def _link_repl(m: re.Match) -> str:
    label = m.group(1)
    url = m.group(2).replace('"', "%22")
    attrs = ""
    if re.match(r"^https?://", url):
        attrs = ' target="_blank" rel="noopener noreferrer"'
    return f'<a href="{url}"{attrs}>{label}</a>'


# 新增与更新的正则
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
HINT_RE = re.compile(r"\[\[([^|\]]+)\|([^|\]]+)\|([^\]]+)\]\]")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

# 粗体、斜体、粗斜体
BOLD_ITALIC_RE = re.compile(r"\*\*\*(.+?)\*\*\*|___(.+?)___")
BOLD_STAR_RE = re.compile(r"\*\*(.+?)\*\*")
BOLD_UNDER_RE = re.compile(r"__(.+?)__")
EM_STAR_RE = re.compile(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)")
EM_UNDER_RE = re.compile(r"(?<![\w_])_([^_\n]+)_(?![\w_])")

# 删除线、高亮、上下标
DEL_RE = re.compile(r"~~(.+?)~~")
MARK_RE = re.compile(r"==([^=\n]+)==")
SUB_RE = re.compile(r"~([^~\n]+)~")
SUP_RE = re.compile(r"\^([^\^\n]+)\^")

# HTML 标签与实体保护
HTML_TAG_RE = re.compile(r"<(/?)(u|ins|del|mark|sub|sup|small|abbr|cite|kbd)\b([^>]*?)>", re.I)
HTML_ENTITY_RE = re.compile(r"&[a-zA-Z0-9#]+;")

# Emoji 扩展
EMOJI_MAP = {
    "smile": "😄", "rocket": "🚀", "+1": "👍", 
    "heart": "❤️", "fire": "🔥", "tada": "🎉"
}
EMOJI_RE = re.compile(r":([a-zA-Z0-9_+-]+):")


def render_inline(text) -> str:
    if text is None:
        return ""
    text = str(text)

    stash: list[str] = []

    def put(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    # 1) 保护 HTML 实体 (必须在转义前)
    text = HTML_ENTITY_RE.sub(lambda m: put(m.group(0)), text)

    # 2) 行内代码（最先，避免其中的符号被后续规则吃掉）
    text = INLINE_CODE_RE.sub(lambda m: put(f"<code>{esc(m.group(1))}</code>"), text)

    # 3) 保护允许的 HTML 标签
    text = HTML_TAG_RE.sub(lambda m: put(m.group(0)), text)

    # 4) 行内换行标签 <br> / <br/> / <br />
    text = re.sub(r"<br\s*/?>", lambda m: put("<br>"), text, flags=re.I)

    # 5) hover 提示
    text = HINT_RE.sub(
        lambda m: put(hint_html(m.group(1), m.group(2), m.group(3))), text
    )

    # 6) 转义剩下的纯文本
    text = esc(text)

    # 7) 强调（粗斜体 -> 粗体 -> 斜体，顺序不能乱）
    text = BOLD_ITALIC_RE.sub(
        lambda m: f"<strong><em>{m.group(1) or m.group(2)}</em></strong>", text
    )
    text = BOLD_STAR_RE.sub(r"<strong>\1</strong>", text)
    text = BOLD_UNDER_RE.sub(r"<strong>\1</strong>", text)
    text = EM_STAR_RE.sub(r"<em>\1</em>", text)
    text = EM_UNDER_RE.sub(r"<em>\1</em>", text)

    # 8) 其他扩展语法
    text = DEL_RE.sub(r"<del>\1</del>", text)
    text = MARK_RE.sub(r"<mark>\1</mark>", text)
    text = SUB_RE.sub(r"<sub>\1</sub>", text)
    text = SUP_RE.sub(r"<sup>\1</sup>", text)

    # 9) Emoji 替换
    text = EMOJI_RE.sub(lambda m: EMOJI_MAP.get(m.group(1), m.group(0)), text)

    # 10) 链接
    text = LINK_RE.sub(_link_repl, text)

    # 11) 还原占位
    text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)

    # 12) 硬换行哨兵 -> <br>
    text = text.replace("\x01", "<br>\n")

    return text


# ==========================================================================
# 块级渲染
# ==========================================================================

BLOCK_START_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s"                 # 标题
    r"|```"                      # 围栏
    r"|:::"                      # callout
    r"|>"                        # 引用
    r"|-{3,}\s*$|\*{3,}\s*$|_{3,}\s*$"   # 分隔线
    r")"
)

#UL_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
#OL_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_OPEN_RE = re.compile(r"^```([^\s`]*)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
FENCE_OPEN_RE = re.compile(r"^```([^\s`]*)\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
SETEXT_RE = re.compile(r"^\s*(=+|-+)\s*$")
ALERT_RE = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)", re.I)
LIST_ITEM_RE = re.compile(r"^([ \t]*)([-*+]|\d+[.)])[ \t]+(.*)$")
TASK_ITEM_RE = re.compile(r"^\[([ xX])\][ \t]+(.*)$")


def _is_block_start(lines: list[str], i: int) -> bool:
    s = lines[i].strip()
    if not s:
        return True
    if BLOCK_START_RE.match(s):
        return True
    if LIST_ITEM_RE.match(lines[i]):
        return True
    return False


def _split_table_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def _parse_table(lines: list[str], i: int):
    header = _split_table_row(lines[i])
    i += 2  # 跳过表头行与分隔行
    rows = []
    while i < len(lines) and lines[i].strip() and "|" in lines[i]:
        rows.append(_split_table_row(lines[i]))
        i += 1

    thead = (
        "<thead><tr>"
        + "".join(f"<th>{render_inline(c)}</th>" for c in header)
        + "</tr></thead>"
    )
    tbody = (
        "<tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in r) + "</tr>"
            for r in rows
        )
        + "</tbody>"
    )
    return f'<div class="table-wrap"><table>{thead}{tbody}</table></div>', i


def _parse_list_item(line: str):
    """解析单行列表项，返回 dict 或 None。"""
    m = LIST_ITEM_RE.match(line)
    if not m:
        return None
    indent = len(m.group(1).replace("\t", "    "))
    marker = m.group(2)
    content = m.group(3)
    ordered = marker[0].isdigit()
    # ★ 关键：提取起始序号，比如 "3." → 3，"12)" → 12
    start = int(marker.rstrip(".)")) if ordered else None
    return {
        "indent": indent,
        "ordered": ordered,
        "content": content,
        "start": start,          # ← 无序列表是 None
    }


def _parse_list(lines, i, base_indent=None):
    """递归解析列表：支持嵌套 / 任务列表 / 指定起始序号。"""
    n = len(lines)
    first = _parse_list_item(lines[i])
    if first is None:
        return "", i

    if base_indent is None:
        base_indent = first["indent"]

    ordered = first["ordered"]
    # ★ 关键：把第一项的 start 记下来，用于输出 <ol start="N">
    start_num = first["start"] if ordered else None
    items = []

    while i < n:
        info = _parse_list_item(lines[i])
        if info is None:
            break
        # 必须是同级、同类型的项
        if info["indent"] != base_indent:
            break
        if info["ordered"] != ordered:
            break

        text_buf = [info["content"]]
        i += 1
        nested_html = []

        # 处理续行 / 嵌套 / 空行
        while i < n:
            line = lines[i]

            # 空行：向后窥探，看是否仍属于本列表
            if not line.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n:
                    nxt = _parse_list_item(lines[j])
                    if nxt and nxt["indent"] >= base_indent:
                        i = j
                        continue
                break

            nxt = _parse_list_item(line)
            if nxt is not None:
                if nxt["indent"] > base_indent:
                    # 缩进更深 → 递归成子列表
                    sub, i = _parse_list(lines, i)
                    nested_html.append(sub)
                    continue
                break   # 同级/更浅 → 本项结束

            # 普通续行
            stripped = line.lstrip()
            if len(line) - len(stripped) > base_indent:
                text_buf.append(stripped)
                i += 1
            else:
                break

        text = " ".join(text_buf)

        # 任务列表
        task = TASK_ITEM_RE.match(text)
        if task:
            checked = task.group(1).lower() == "x"
            body = (
                f'<input class="task-checkbox" type="checkbox" disabled'
                f'{" checked" if checked else ""}> '
                + render_inline(task.group(2))
            )
            li_class = ' class="task-list-item"'
        else:
            body = render_inline(text)
            li_class = ""

        if nested_html:
            body += "\n" + "\n".join(nested_html)

        items.append(f"<li{li_class}>{body}</li>")

    # ★ 关键：把 start 输出到 <ol>
    tag = "ol" if ordered else "ul"
    attrs = ""
    if ordered and start_num and start_num != 1:
        attrs = f' start="{start_num}"'

    return f"<{tag}{attrs}>\n" + "\n".join(items) + f"\n</{tag}>", i


def _parse_list(lines: list[str], i: int, base_indent: int | None = None):
    """递归解析列表，支持：嵌套 / 任务列表 / 自定义起始序号。

    返回 (html, next_i)。
    """
    n = len(lines)
    first = _parse_list_item(lines[i])
    if first is None:
        return "", i
    if base_indent is None:
        base_indent = first["indent"]

    ordered = first["ordered"]
    start_num = first["start"]
    items: list[str] = []

    while i < n:
        info = _parse_list_item(lines[i])
        if info is None:
            break
        if info["indent"] < base_indent:
            break
        if info["indent"] > base_indent:
            # 同级突然变深：交给上面内层循环处理，这里不该出现
            break
        if info["ordered"] != ordered:
            break

        # ---- 当前列表项的正文 ----
        text_buf = [info["content"]]
        i += 1
        nested_html: list[str] = []

        # 收集续行 / 嵌套列表
        while i < n:
            line = lines[i]

            # 空行：窥探后面是否还属于本列表
            if not line.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n:
                    nxt = _parse_list_item(lines[j])
                    if nxt and nxt["indent"] >= base_indent:
                        i = j
                        continue
                break

            nxt = _parse_list_item(line)
            if nxt is not None:
                if nxt["indent"] > base_indent:
                    # 递归解析子列表
                    sub, i = _parse_list(lines, i)
                    nested_html.append(sub)
                    continue
                break  # 同级/更浅 —— 当前项结束

            # 普通续行：必须比当前项缩进更深
            stripped = line.lstrip()
            cur_indent = len(line) - len(stripped)
            if cur_indent > base_indent:
                text_buf.append(stripped)
                i += 1
            else:
                break

        text = " ".join(text_buf)

        # ---- 任务列表 ----
        task = TASK_ITEM_RE.match(text)
        if task:
            checked = task.group(1).lower() == "x"
            body = (
                f'<input class="task-checkbox" type="checkbox" disabled'
                f'{" checked" if checked else ""}> '
                + render_inline(task.group(2))
            )
            li_class = ' class="task-list-item"'
        else:
            body = render_inline(text)
            li_class = ""

        if nested_html:
            body += "\n" + "\n".join(nested_html)

        items.append(f"<li{li_class}>{body}</li>")

    tag = "ol" if ordered else "ul"
    attrs = ""
    if ordered and start_num and start_num != 1:
        attrs = f' start="{start_num}"'
    return f"<{tag}{attrs}>\n" + "\n".join(items) + f"\n</{tag}>", i


def render_code_block(code: str, lang: str) -> str:
    lang = (lang or "").lower()
    hl = HIGHLIGHTERS.get(lang, highlight_plain)(code)
    label = LANG_LABEL.get(lang, lang or "text")

    return (
        '<div class="code-block">\n'
        '    <div class="code-block__bar">\n'
        '        <span class="code-block__dots"><i></i><i></i><i></i></span>\n'
        f'        <span class="code-block__lang">{esc(label)}</span>\n'
        '        <button class="code-block__copy" type="button" data-copy>\n'
        '            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
        'stroke-linejoin="round">\n'
        '                <rect x="9" y="9" width="11" height="11" rx="2" />\n'
        '                <path d="M5 15V5a2 2 0 0 1 2-2h10" />\n'
        "            </svg>\n"
        "            复制\n"
        "        </button>\n"
        "    </div>\n"
        f"    <pre><code>{hl}</code></pre>\n"
        "</div>"
    )

# ==========================================================================
# 提示框图标 (SVG)
# ==========================================================================
CALLOUT_ICONS = {
    "note": '<svg class="callout__icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
    "tip": '<svg class="callout__icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"></path><path d="M10 22h4"></path><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"></path></svg>',
    "important": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="#8250df" aria-hidden="true"><path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.573 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.25v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Zm7 2.25v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 9a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/></svg>',
    "warning": '<svg class="callout__icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "caution": '<svg class="callout__icon" viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
}

def render_callout(buf: list[str], c_type: str = "warning") -> str:
    body = " ".join(x.strip() for x in buf if x.strip())
    icon_svg = CALLOUT_ICONS.get(c_type, CALLOUT_ICONS["warning"])
    return (
        f'<div class="callout callout--{c_type}">\n'
        f'    <div class="callout__title">{icon_svg} {c_type.upper()}</div>\n'
        f'    <div class="callout__body">{render_inline(body)}</div>\n'
        f'</div>'
    )


def make_slug(text: str, seen: dict) -> str:
    s = re.sub(r"^[\s\u3000]*[一二三四五六七八九十百千\d]+\s*[、.．,)）:：]\s*", "", text)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s, flags=re.UNICODE).strip("-").lower()
    base = "h-" + (s or "sec")

    if base in seen:
        seen[base] += 1
        return f"{base}-{seen[base]}"
    seen[base] = 0
    return base


def render_markdown(md: str, seen_slugs: dict | None = None, headings: list | None = None):
    """返回 (html, headings)。headings = [(level, id, text), ...]"""
    if seen_slugs is None:
        seen_slugs = {}
    if headings is None:
        headings = []

    lines = md.split("\n")
    out: list[str] = []

    i, n = 0, len(lines)

    while i < n:
        raw = lines[i]
        s = raw.strip()

        if not s:
            i += 1
            continue

        # ---------- 围栏代码块 ----------
        fence = FENCE_OPEN_RE.match(s)
        if fence:
            lang = fence.group(1)
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过收尾 ```
            out.append(render_code_block("\n".join(buf), lang))
            continue

        # ---------- callout ----------
        if s.startswith(":::"):
            parts = s.split(maxsplit=1)
            c_type = "warning"  # 默认类型
            if len(parts) > 1:
                t = parts[1].strip().lower()
                if t in ("note", "tip", "important", "warning", "caution"):
                    c_type = t
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith(":::"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(render_callout(buf, c_type))
            continue

        # ---------- 标题 ----------
        h = HEADING_RE.match(s)
        if h:
            level = len(h.group(1))
            text = h.group(2).strip()
            hid = make_slug(text, seen_slugs)
            headings.append((level, hid, text))
            out.append(f'<h{level} id="{hid}">{render_inline(text)}</h{level}>')
            i += 1
            continue

        # ---------- Setext 标题（=== / ---） ----------
        # 条件：当前行是普通文本（不是块起始），下一行是 === 或 ---
        if (
            i + 1 < n
            and not _is_block_start(lines, i)
            and SETEXT_RE.match(lines[i + 1])
        ):
            marker = lines[i + 1].strip()[0]
            level = 1 if marker == "=" else 2
            hid = make_slug(s, seen_slugs)
            headings.append((level, hid, s))
            out.append(f'<h{level} id="{hid}">{render_inline(s)}</h{level}>')
            i += 2
            continue

        # ---------- 分隔线 ----------
        if HR_RE.match(s):
            out.append("<hr>")
            i += 1
            continue

        # ---------- 表格 ----------
        if (
            "|" in raw
            and i + 1 < n
            and TABLE_SEP_RE.match(lines[i + 1])
            and "|" in lines[i + 1]
        ):
            tbl, i = _parse_table(lines, i)
            out.append(tbl)
            continue

        # ---------- 引用 / GFM Alert ----------
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                # 移除一层 > 和紧跟的一个空格（如果有）
                line = re.sub(r"^\s*>\s?", "", lines[i])
                buf.append(line)
                i += 1

            # 检查第一行是否包含 GFM Alert 语法
            first_line = buf[0].strip() if buf else ""
            alert_match = ALERT_RE.match(first_line)

            if alert_match:
                alert_type = alert_match.group(1).upper()
                c_type = alert_type.lower()
                icon_svg = CALLOUT_ICONS.get(c_type, CALLOUT_ICONS["note"])
                # 去掉第一行（标题行），将剩余内容递归渲染
                rest_md = "\n".join(buf[1:])
                inner_html, _ = render_markdown(rest_md, seen_slugs, headings)
                
                out.append(
                    f'<div class="callout callout--{c_type}">\n'
                    f'    <div class="callout__title">{icon_svg} {alert_type}</div>\n'
                    f'    <div class="callout__body">\n{inner_html}\n    </div>\n'
                    f'</div>'
                )
            else:
                # 普通引用块，将去掉一层 > 后的内容递归渲染，以支持嵌套引用
                inner_md = "\n".join(buf)
                inner_html, _ = render_markdown(inner_md, seen_slugs, headings)
                out.append(f"<blockquote>\n{inner_html}\n</blockquote>")
            continue
        # ---------- 列表（无序 / 有序 / 嵌套 / 任务列表）----------
        if LIST_ITEM_RE.match(raw):
            block, i = _parse_list(lines, i)
            out.append(block)
            continue

        # ---------- 段落 ----------
        buf = [raw]                      # ← 保留原始行（含行尾空格）
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines, i):
            buf.append(lines[i])         # ← 不再 .strip()
            i += 1

        parts = []
        for idx, line in enumerate(buf):
            if idx:
                prev = buf[idx - 1]
                # 行尾两个及以上空格，或行尾反斜杠 => 硬换行
                hard = bool(re.search(r" {2,}$", prev) or re.search(r"\\$", prev))
                parts.append("\x01" if hard else " ")
            parts.append(line.strip())   # 单行收尾空格在这里丢掉

        out.append("<p>" + render_inline("".join(parts)) + "</p>")

    return "\n\n".join(out), headings


# ==========================================================================
# Front Matter
# ==========================================================================

def parse_front_matter(text: str):
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end < 0:
        return {}, text

    fm = text[3:end].strip()
    body = text[end + 4:]

    meta: dict = {}
    for line in fm.split("\n"):
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()

        if key in ("tags", "keywords") and val and not val.startswith("["):
            val = [x.strip() for x in val.split(",") if x.strip()]
        elif val.startswith("[") and val.endswith("]"):
            val = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]

        meta[key] = val

    return meta, body.lstrip("\n")


# ==========================================================================
# 组装页面
# ==========================================================================

def fill_head(head: str, css: str, meta: dict) -> str:
    """把 <style> 填回去，并替换 title / description。"""
    title = meta.get("title", "未命名")
    desc = meta.get("description", "")

    # 把分离阶段留下的注释占位换回 <style>
    head = re.sub(
        r"<!--[^\n]*?parts/style\.css[^\n]*?-->",
        lambda _: "<style>\n" + css + "\n    </style>",
        head,
    )

    # 兜底：如果没找到占位注释
    if "<style" not in head:
        head = head.replace("</head>", f"    <style>\n{css}\n    </style>\n</head>")

    # 去掉 <head> 里的 script（script 统一放到 body 底部）
    head = re.sub(r"\s*<script\b[\s\S]*?</script>\s*", "\n", head)

    # 标题
    head = re.sub(
        r"<title>[\s\S]*?</title>",
        f"<title>{esc(title)} · 七七的折腾笔记</title>",
        head,
        count=1,
    )

    # description
    head = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        f'<meta name="description" content="{esc_attr(desc)}">',
        head,
        count=1,
    )

    # og:title / og:description
    head = re.sub(
        r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:title" content="{esc_attr(title)}">',
        head,
        count=1,
    )
    head = re.sub(
        r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:description" content="{esc_attr(desc)}">',
        head,
        count=1,
    )

    return head


def build_meta_spans(meta: dict) -> str:
    items = []
    if meta.get("date"):
        items.append(esc(meta["date"]))
    if meta.get("category"):
        items.append(esc(meta["category"]))
    if meta.get("readtime"):
        items.append(f"约 {esc(meta['readtime'])} 分钟")
    if meta.get("author"):
        items.append(esc(meta["author"]))

    if not items:
        return "\n        "

    inner = "\n        ".join(f"<span>{x}</span>" for x in items)
    return "\n        " + inner + "\n    "


def build_tag_spans(meta: dict) -> str:
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not tags:
        return '\n        <span class="chip">随笔</span>\n    '

    inner = "\n        ".join(f'<span class="chip">{esc(t)}</span>' for t in tags)
    return "\n        " + inner + "\n    "


def fill_article_head(tpl: str, meta: dict) -> str:
    out = replace_between(
        tpl,
        '<div class="article-head__eyebrow">',
        "</div>",
        esc(meta.get("eyebrow", "Blog · Note")),
    )
    out = replace_between(
        out,
        '<h1 class="article-head__title">',
        "</h1>",
        esc(meta.get("title", "未命名")),
    )
    out = replace_between(
        out,
        '<p class="article-head__desc">',
        "</p>",
        "\n                            "
        + render_inline(meta.get("description", ""))
        + "\n                        ",
    )
    out = replace_between(
        out,
        '<div class="article-head__meta">',
        "</div>",
        build_meta_spans(meta),
    )
    out = replace_between(
        out,
        '<div class="article-head__tags">',
        "</div>",
        build_tag_spans(meta),
    )
    return out


def build_toc(headings: list[tuple[int, str, str]]) -> str:
    """构建目录，支持 Markdown h1–h6。

    类名约定：
        toc__link            基础样式
        toc__link--h{N}      标题级别专属类（N = 1..6）
        toc__link--sub       h3 及更深层级的通用子级样式（兼容旧 CSS）
    另外附带 data-level 属性，方便 CSS / JS 按层级自定义缩进或字号。
    """
    if not headings:
        return '<a class="toc__link" href="#top">正文</a>'

    rows = []
    for level, hid, text in headings:
        # 防御性钳制：即使输入异常也不会生成 h7/h0 这类类名
        level = max(1, min(6, int(level)))

        classes = ["toc__link", f"toc__link--h{level}"]
        if level >= 3:
            classes.append("toc__link--sub")

        rows.append(
            f'<a class="{" ".join(classes)}" data-level="{level}" '
            f'href="#{hid}">{esc(text)}</a>'
        )

    return "\n                        ".join(rows)


def build_article_foot(meta: dict) -> str:
    if not meta.get("license") and not meta.get("updated"):
        return ""

    lic_name = meta.get("license", "")
    lic_url = meta.get("license_url", "#")
    updated = meta.get("updated") or meta.get("date", "")

    left = ""
    if lic_name:
        left = (
            "本文采用 "
            f'<a class="article-foot__link" href="{esc_attr(lic_url)}" '
            f'target="_blank" rel="noopener noreferrer">{esc(lic_name)}</a> '
            "许可协议，转载请注明出处，禁止用于商业目的。"
        )

    right = f"<span>最后更新于 {esc(updated)}</span>" if updated else ""

    return (
        '\n\n<div class="article-foot">\n'
        f'    <span class="article-foot__license">\n        {left}\n    </span>\n'
        f"    {right}\n"
        "</div>"
    )


def rebuild_scripts(scripts_html: str) -> str:
    """
    parts/scripts.html 里每个脚本被写成：
        <!-- script #1 · <script type="module"> -->
        脚本正文
    这里把它还原成真正的 <script> 标签。
    """
    chunks = re.split(r"\n(?=<!--\s*script\s*#)", scripts_html)
    out = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        m = re.match(
            r"<!--[^\n]*?(<script\b[^>]*>)[^\n]*?-->\s*\n?(.*)",
            chunk,
            re.S,
        )
        if m:
            open_tag = m.group(1)
            body = m.group(2).strip("\n")
            out.append(f"{open_tag}\n{body}\n</script>")
        else:
            # 已经是完整 <script>…</script> 的情况
            if chunk.startswith("<script"):
                out.append(chunk)
            else:
                out.append(f"<script>\n{chunk}\n</script>")

    return "\n\n".join(out)


def build_page(meta: dict, content: str, headings, parts_dir: Path) -> str:
    head_tpl = read(parts_dir / "head.html")
    css = read(parts_dir / "style.css")
    topbar = read(parts_dir / "topbar.html").strip()
    progress = read(parts_dir / "read_progress.html").strip()
    article_head_tpl = read(parts_dir / "article_head.html").strip()
    toc_tpl = read(parts_dir / "toc.html").strip()
    to_top = read(parts_dir / "to_top.html").strip()
    footer = read(parts_dir / "footer.html").strip()
    scripts_raw = read(parts_dir / "scripts.html")

    head = fill_head(head_tpl, css, meta)
    article_head = fill_article_head(article_head_tpl, meta)
    toc = replace_between(
        toc_tpl,
        '<nav class="toc__list" id="toc-list">',
        "</nav>",
        "\n                        " + build_toc(headings) + "\n                    ",
    )
    scripts = rebuild_scripts(scripts_raw)

    article_body = (
        '<div class="card article-body" id="article-body">\n\n'
        + content
        + build_article_foot(meta)
        + "\n\n</div>"
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n\n'
        f"{head}\n\n"
        "<body>\n\n"
        f"{topbar}\n\n"
        f"{progress}\n\n"
        '<div class="wrap">\n'
        '    <div class="article-layout">\n\n'
        "        <main>\n"
        "            <article>\n\n"
        f"{indent(article_head, 12)}\n\n"
        f"{indent(article_body, 12)}\n\n"
        "            </article>\n\n"
        f"{indent(footer, 8)}\n"
        "        </main>\n\n"
        f"{indent(toc, 8)}\n\n"
        "    </div>\n"
        "</div>\n\n"
        f"{to_top}\n\n"
        f"{scripts}\n\n"
        "</body>\n\n"
        "</html>\n"
    )


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.split("\n"))


# ==========================================================================
# CLI
# ==========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="把 Markdown 渲染成与 parts/ 一致的页面")
    ap.add_argument("md_file", help="Markdown 源文件")
    ap.add_argument("-p", "--parts", default="parts", help="parts 目录（默认 parts）")
    ap.add_argument("-o", "--out", default=None, help="输出 HTML（默认同名 .html）")
    args = ap.parse_args(argv)

    md_path = Path(args.md_file)
    if not md_path.is_file():
        print(f"找不到文件：{md_path}", file=sys.stderr)
        return 1

    parts_dir = Path(args.parts)
    if not parts_dir.is_dir():
        print(f"找不到 parts 目录：{parts_dir}", file=sys.stderr)
        return 1

    raw = md_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)

    if "title" not in meta:
        meta["title"] = md_path.stem

    content, headings = render_markdown(body)
    page = build_page(meta, content, headings, parts_dir)

    out_path = Path(args.out) if args.out else md_path.with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")

    print(f"输入：{md_path}")
    print(f"模板：{parts_dir}/")
    print(f"标题：{meta.get('title')}")
    print(f"标题数：{len(headings)}  正文字符：{len(content):,}")
    print(f"输出：{out_path.resolve()}  ({len(page):,} 字符)")
    return 0


if __name__ == "__main__":
    sys.exit(main())