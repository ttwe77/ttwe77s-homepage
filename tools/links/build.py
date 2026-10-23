#!/usr/bin/env python3
"""读取 links/links.json，生成友链卡片 HTML，写入 output/links.html"""

import html
import json
import re
import sys
import textwrap
from pathlib import Path

# 获取当前脚本所在目录 (links/) 和项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 适配新的文件结构
DATA_FILE = BASE_DIR / "links.json"
TEMPLATE_FILE = BASE_DIR / "sample.html"

# 输出配置
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "links.html"

START_MARK = "<!-- FRIENDS:START -->"
END_MARK = "<!-- FRIENDS:END -->"

# 未指定 c1/c2 时的兜底配色（按卡片顺序循环）
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


def render_card(item: dict, index: int) -> str:
    name = esc(item.get("name"))
    url = esc(item.get("url"))
    desc = esc(item.get("desc"))
    if not name or not url:
        raise ValueError(f"第 {index + 1} 条友链缺少 name 或 url：{item!r}")

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


def main() -> None:
    # 1. 读取数据和模板
    if not DATA_FILE.exists():
        sys.exit(f"✗ 找不到数据文件: {DATA_FILE}")
    if not TEMPLATE_FILE.exists():
        sys.exit(f"✗ 找不到模板文件: {TEMPLATE_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    friends = data.get("friends") or []
    updated = esc(data.get("updated") or "")

    cards = textwrap.indent(
        "\n".join(render_card(item, i) for i, item in enumerate(friends)),
        "      ",
    )

    original = TEMPLATE_FILE.read_text(encoding="utf-8")
    page = original

    # 2. 替换卡片区块
    block_re = re.compile(
        re.escape(START_MARK) + r".*?" + re.escape(END_MARK), re.S
    )
    if not block_re.search(page):
        sys.exit(f"✗ 在 {TEMPLATE_FILE} 中找不到 {START_MARK} / {END_MARK} 标记")

    page = block_re.sub(
        lambda _: f"{START_MARK}\n{cards}\n      {END_MARK}", page, count=1
    )

    # 3. 替换“最后更新”日期
    page = re.sub(
        r'(<time id="friend-updated">).*?(</time>)',
        lambda m: f"{m.group(1)}{updated}{m.group(2)}",
        page,
        count=1,
        flags=re.S,
    )

    # 4. 确保 output 目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 5. 写入文件 (如果目标文件存在且内容无变化，则跳过)
    if OUTPUT_FILE.exists() and page == OUTPUT_FILE.read_text(encoding="utf-8"):
        print("• 内容无变化，跳过写入")
        return

    OUTPUT_FILE.write_text(page, encoding="utf-8")
    print(f"✓ 已生成 {len(friends)} 条友链 → {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()