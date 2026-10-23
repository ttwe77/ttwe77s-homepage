#!/usr/bin/env python3
"""读取 links/links.json，把友链与鸣谢卡片注入 sample.html，输出 output/links.html"""

import html
import json
import re
import sys
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "links.json"
TEMPLATE_FILE = BASE_DIR / "sample.html"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "links.html"

FRIENDS_START = "<!-- FRIENDS:START -->"
FRIENDS_END = "<!-- FRIENDS:END -->"
THANKS_START = "<!-- THANKS:START -->"
THANKS_END = "<!-- THANKS:END -->"

PALETTE = [
    ("#8AB4F8", "#5E8BFF"),
    ("#7FC4EA", "#21a5e3"),
    ("#BEC0EC", "#4454F8"),
    ("#7BE0B8", "#34C79F"),
    ("#E39BEA", "#A97CE6"),
    ("#FFD84D", "#FB7B44"),
    ("#9BA4B5", "#6C7A9F"),
    ("#F4756A", "#EA3462"),
]

GO_SVG = (
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>'
)


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _avatar_and_tags(item: dict, index: int):
    initial = esc(item.get("initial") or item.get("name", "?").strip()[:1] or "?")
    c1, c2 = item.get("c1"), item.get("c2")
    if not c1 or not c2:
        p1, p2 = PALETTE[index % len(PALETTE)]
        c1, c2 = c1 or p1, c2 or p2

    avatar = item.get("avatar")
    img = (
        f'<img src="{esc(avatar)}" alt="" width="50" height="50" '
        f'loading="lazy" onerror="this.remove()">'
        if avatar else ""
    )
    tags = "".join(
        f'<span class="chip">{esc(t)}</span>' for t in (item.get("tags") or [])
    )
    return initial, c1, c2, img, tags


def render_card(item: dict, index: int) -> str:
    """友链卡片：必须有 url，整卡 <a>"""
    name = esc(item.get("name"))
    url = esc(item.get("url"))
    desc = esc(item.get("desc"))
    if not name or not url:
        raise ValueError(f"第 {index + 1} 条友链缺少 name 或 url：{item!r}")

    initial, c1, c2, img, tags = _avatar_and_tags(item, index)

    return (
        f'<a class="friend" href="{url}" target="_blank" rel="noopener noreferrer"\n'
        f'        style="--c1:{esc(c1)};--c2:{esc(c2)};--i:{index}">\n'
        f'        <span class="friend__avatar">{img}<span>{initial}</span></span>\n'
        f'        <span class="friend__main">\n'
        f'          <span class="friend__top">\n'
        f'            <span class="friend__name">{name}</span>\n'
        f'          </span>\n'
        f'          <span class="friend__desc">{desc}</span>\n'
        f'          <span class="friend__tags">{tags}</span>\n'
        f'        </span>\n'
        f'        <span class="friend__go" aria-hidden="true">{GO_SVG}</span>\n'
        f'      </a>'
    )


def render_person_card(item: dict, index: int) -> str:
    """鸣谢卡片：url 可选；无 url 时用 <div> 渲染且不显示箭头"""
    name = esc(item.get("name"))
    if not name:
        raise ValueError(f"第 {index + 1} 位鸣谢对象缺少 name：{item!r}")

    desc = esc(item.get("desc"))
    url = item.get("url")
    initial, c1, c2, img, tags = _avatar_and_tags(item, index)
    style = f'style="--c1:{esc(c1)};--c2:{esc(c2)};--i:{index}"'

    if url:
        open_tag = (
            f'<a class="friend" href="{esc(url)}" target="_blank" '
            f'rel="noopener noreferrer" {style}>'
        )
        close_tag = "</a>"
        go = f'<span class="friend__go" aria-hidden="true">{GO_SVG}</span>'
    else:
        open_tag = f'<div class="friend friend--static" {style}>'
        close_tag = "</div>"
        go = ""

    return (
        f'{open_tag}\n'
        f'        <span class="friend__avatar">{img}<span>{initial}</span></span>\n'
        f'        <span class="friend__main">\n'
        f'          <span class="friend__top">\n'
        f'            <span class="friend__name">{name}</span>\n'
        f'          </span>\n'
        f'          <span class="friend__desc">{desc}</span>\n'
        f'          <span class="friend__tags">{tags}</span>\n'
        f'        </span>\n'
        f'        {go}\n'
        f'      {close_tag}'
    )


def indent_cards(cards) -> str:
    return textwrap.indent("\n".join(cards), "      ")


def replace_block(page: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(page):
        sys.exit(f"✗ 在模板中找不到 {start} / {end} 标记")
    inner = f"{start}\n{body}\n      {end}" if body.strip() else f"{start}\n      {end}"
    return pattern.sub(lambda _: inner, page, count=1)


def set_time(page: str, elem_id: str, value: str) -> str:
    pattern = re.compile(rf'(<time id="{re.escape(elem_id)}">).*?(</time>)', re.S)
    return pattern.sub(lambda m: f"{m.group(1)}{esc(value)}{m.group(2)}", page, count=1)


def set_total(page: str, elem_id: str, n: int) -> str:
    pattern = re.compile(rf'(<b id="{re.escape(elem_id)}">).*?(</b>)', re.S)
    return pattern.sub(lambda m: f"{m.group(1)}{n}{m.group(2)}", page, count=1)


def main() -> None:
    if not DATA_FILE.exists():
        sys.exit(f"✗ 找不到数据文件: {DATA_FILE}")
    if not TEMPLATE_FILE.exists():
        sys.exit(f"✗ 找不到模板文件: {TEMPLATE_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    friends = data.get("friends") or []
    thanks = data.get("thanks") or []
    updated = data.get("updated") or ""

    page = TEMPLATE_FILE.read_text(encoding="utf-8")

    # 友链区块
    page = replace_block(
        page, FRIENDS_START, FRIENDS_END,
        indent_cards(render_card(item, i) for i, item in enumerate(friends)),
    )
    page = set_time(page, "friend-updated", updated)
    page = set_total(page, "friend-total", len(friends))

    # 鸣谢区块
    page = replace_block(
        page, THANKS_START, THANKS_END,
        indent_cards(render_person_card(item, i) for i, item in enumerate(thanks)),
    )
    page = set_time(page, "thanks-updated", updated)
    page = set_total(page, "thanks-total", len(thanks))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists() and page == OUTPUT_FILE.read_text(encoding="utf-8"):
        print("• 内容无变化，跳过写入")
        return

    OUTPUT_FILE.write_text(page, encoding="utf-8")
    print(
        f"✓ 已生成 {len(friends)} 条友链 + {len(thanks)} 条鸣谢 → "
        f"{OUTPUT_FILE.relative_to(BASE_DIR)}"
    )


if __name__ == "__main__":
    main()