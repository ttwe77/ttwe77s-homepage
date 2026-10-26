#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
genrss.py —— 依据 blog/index.ini + MD front-matter 生成 RSS 2.0 订阅文件

用法:
    python genrss.py                          # 交互式输入项目目录
    python genrss.py ttwe77s-homepage         # 项目根目录（自动找 blog/index.ini）
    python genrss.py /path/to/project         # 绝对路径
    python genrss.py ttwe77s-homepage -o ../rss.xml

输出:
    rss.xml —— 默认生成在【脚本所在目录】，可用 -o 覆盖

强制规则（缺一律报错退出）:
    · 每篇文章必须在 <project>/tools/genblog/docs/ 下有同名 .md
    · MD 的 YAML front-matter 必须含 date 与 updated
    · MD 的 date 只有年月日 → 补成当天 11:45:14 +08:00
    · item <pubDate>   ← MD date
    · item <atom:updated> ← MD updated（RFC 3339 / isoformat）
    · channel <pubDate>   ← 所有 item pubDate 的最大值
    · channel <lastBuildDate> ← 所有 item atom:updated 的最大值

MD front-matter 读取字段:
    title / description / date / category / tags / author / updated
    （readtime 已废弃，不再输出 <reading:minutes>）

频道级元数据 → 本文件顶部常量。
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import quote

# ════════════════════════════════════════════════════════════
#  站点配置 —— 换域名 / 换站名，只改这一段
# ════════════════════════════════════════════════════════════
SITE_URL    = 'https://www.ttwe77.cn'
SITE_NAME   = '七七的折腾笔记'
SITE_DESC   = '学计算机的，最大的爱好就是闲着没事瞎折腾。记录服务器、网络、系统配置的实践与踩坑记录。'
SITE_LANG   = 'zh-CN'
SITE_AUTHOR = 'ttwe77'
POST_BASE   = 'blog/'        # 文章所在目录（相对站点根）
FEED_PATH   = 'rss.xml'      # 订阅文件在站点上的路径
TZ          = timezone(timedelta(hours=8))   # 东八区

# ── 频道级常量（原需求里「设为常量」的那一组）──────────────
CHANNEL_COPYRIGHT = '© 2026 ttwe77 · 内容采用 CC BY-NC 4.0 许可'
MANAGING_EDITOR   = 'ttwe77@yeah.net (ttwe77)'   # 责编邮箱
WEBMASTER         = 'ttwe77@ttwe77.cn (ttwe77)'   # 网站管理员邮箱
TTL_MINUTES       = 180                              # 缓存分钟数
IMAGE_URL         = 'https://www.ttwe77.cn/src/head.jpg'
IMAGE_TITLE       = SITE_NAME
IMAGE_LINK        = SITE_URL
DOCS_URL          = 'https://www.rssboard.org/rss-specification'
CHANNEL_CATEGORY  = '技术'

# ── category domain ─────────────────────────────────────
CATEGORY_DOMAIN = 'urn:ttwe77:category'
TAG_DOMAIN      = 'urn:ttwe77:tag'

# ── 项目布局 ──────────────────────────────────────────────
BLOG_SUBDIR = 'blog'
DOCS_SUBDIR = 'tools/genblog/docs'

# ════════════════════════════════════════════════════════════
#  其它常量
# ════════════════════════════════════════════════════════════
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_NAME = 'index.ini'
MAX_ITEMS  = 0            # 0 表示不限制条数
DEFAULT_TIME_OF_DAY = (11, 45, 14)   # 纯日期补全的时分秒

HINT_OPEN  = '<span class="hover-hint">'
TIP_OPEN   = '<span class="hover-hint__tooltip">'
SPAN_CLOSE = '</span>'

INCLUDE_RE  = re.compile(r'^#\s*include\s+(.+?)\s*$', re.IGNORECASE)
ILLEGAL_XML = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
PURE_DATE_RE = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')


# ════════════════════════════════════════════════════════════
#  基础工具
# ════════════════════════════════════════════════════════════
def fail(msg):
    print(f'[错误] {msg}', file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f'[提示] {msg}', file=sys.stderr)


def xesc(s):
    s = ILLEGAL_XML.sub('', '' if s is None else str(s))
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;')
             .replace("'", '&apos;'))


def title_from_file(file):
    name = re.sub(r'\.html?$', '', file.replace('\\', '/').rsplit('/', 1)[-1],
                  flags=re.IGNORECASE)
    name = re.sub(r'[-_]+', ' ', name)
    return re.sub(r'\b[a-z]', lambda m: m.group(0).upper(), name)


def strip_hover_hint(raw):
    src = '' if raw is None else str(raw)
    out, pos = [], 0
    while pos < len(src):
        start = src.find(HINT_OPEN, pos)
        if start == -1:
            out.append(src[pos:])
            break
        out.append(src[pos:start])
        label_start = start + len(HINT_OPEN)
        tip_start = src.find(TIP_OPEN, label_start)
        if tip_start == -1:
            out.append(src[start:])
            break
        label = src[label_start:tip_start]
        inner_start = tip_start + len(TIP_OPEN)
        inner_end = src.find(SPAN_CLOSE + SPAN_CLOSE, inner_start)
        if inner_end == -1:
            out.append(src[start:])
            break
        out.append(label)
        pos = inner_end + len(SPAN_CLOSE) * 2
    return ''.join(out)


def parse_dt(s):
    """
    '2026-10-17'                     → 2026-10-17 11:45:14 +08:00（纯日期补全）
    '2026-10-17 20:00:00'            → 原样，+08:00
    '2026-10-17T20:00:00+08:00'      → ISO，转 +08:00
    '2026年10月17日'                  → 同纯日期
    解析失败返回 None。
    """
    s = (s or '').strip()
    if not s:
        return None

    s2 = (s.replace('/', '-').replace('年', '-')
           .replace('月', '-').replace('日', '')).strip()

    # 纯日期 → 补 11:45:14
    if PURE_DATE_RE.match(s2):
        try:
            d = datetime.strptime(s2, '%Y-%m-%d')
            return d.replace(tzinfo=TZ,
                             hour=DEFAULT_TIME_OF_DAY[0],
                             minute=DEFAULT_TIME_OF_DAY[1],
                             second=DEFAULT_TIME_OF_DAY[2])
        except ValueError:
            return None

    # 带时间：先按无时区
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(s2, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue

    # 带时区的 ISO
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except ValueError:
        return None


# ════════════════════════════════════════════════════════════
#  ini 解析
# ════════════════════════════════════════════════════════════
def parse_includes(text):
    out = []
    for line in text.splitlines():
        m = INCLUDE_RE.match(line.strip())
        if not m:
            continue
        name = m.group(1).strip().strip('"').strip("'")
        if name:
            out.append(name)
    out.reverse()
    return out


def parse_ini(text):
    """一行一篇；字段: 文件名 | 标题 | 日期 | 分类 | 标签,标签 | 摘要 | <svg …>"""
    items = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw[0] in '#;':
            continue
        parts = [p.strip() for p in raw.split('|')]
        file = parts[0]
        if not file or not re.search(r'\.html?$', file, re.IGNORECASE):
            continue
        title    = parts[1] if len(parts) > 1 and parts[1] else ''
        category = parts[3] if len(parts) > 3 and parts[3] else ''
        raw_tags = parts[4] if len(parts) > 4 else ''
        desc     = parts[5] if len(parts) > 5 else ''
        tags = [t.strip() for t in re.split(r'[,，]', raw_tags) if t.strip()]
        items.append({
            'file': file, 'title': title,
            'category': category, 'tags': tags, 'desc': desc,
        })
    items.reverse()
    return items


# ════════════════════════════════════════════════════════════
#  MD front-matter
# ════════════════════════════════════════════════════════════
def parse_yaml_frontmatter(text):
    """极简 YAML：key: value / "value"；跳过缩进的嵌套字段。"""
    result = {}
    text = (text or '').lstrip('\ufeff')
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return result
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    if end_idx == -1:
        return result
    for line in lines[1:end_idx]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line.startswith((' ', '\t')):
            continue
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
            v = v[1:-1]
        result[k] = v
    return result


def find_md_for_html(html_file, docs_dir):
    rel = re.sub(r'\.html?$', '', html_file, flags=re.IGNORECASE).replace('\\', '/')
    cand = os.path.join(docs_dir, *rel.split('/')) + '.md'
    if os.path.isfile(cand):
        return cand
    base = rel.rsplit('/', 1)[-1] + '.md'
    cand = os.path.join(docs_dir, base)
    if os.path.isfile(cand):
        return cand
    for root, _, files in os.walk(docs_dir):
        if base in files:
            return os.path.join(root, base)
    return None


# ════════════════════════════════════════════════════════════
#  汇总
# ════════════════════════════════════════════════════════════
def collect_items(blog_dir, docs_dir):
    index_path = os.path.join(blog_dir, INDEX_NAME)
    with open(index_path, encoding='utf-8-sig') as f:
        index_text = f.read()

    includes = parse_includes(index_text)
    if not includes:
        items = parse_ini(index_text)
    else:
        items = []
        for name in includes:
            page_path = os.path.join(blog_dir, *name.replace('\\', '/').split('/'))
            if not os.path.isfile(page_path):
                fail(f'找不到分页文件: {page_path}')
            with open(page_path, encoding='utf-8-sig') as f:
                items.extend(parse_ini(f.read()))

    if not items:
        fail('没有解析到任何文章，请检查 index.ini / 分页文件格式。')

    merged = []
    for it in items:
        md_path = find_md_for_html(it['file'], docs_dir)
        if not md_path:
            fail(f'{it["file"]} 找不到对应的 MD 文件（docs 目录: {docs_dir}）')

        try:
            with open(md_path, encoding='utf-8-sig') as f:
                yaml = parse_yaml_frontmatter(f.read())
        except OSError as e:
            fail(f'读取 {md_path} 失败: {e}')

        if not yaml.get('date'):
            fail(f'{md_path} 缺少 date 字段')
        if not yaml.get('updated'):
            fail(f'{md_path} 缺少 updated 字段')

        pub_dt = parse_dt(yaml['date'])
        if pub_dt is None:
            fail(f'{md_path} 的 date 无法解析: {yaml["date"]!r}')
        upd_dt = parse_dt(yaml['updated'])
        if upd_dt is None:
            fail(f'{md_path} 的 updated 无法解析: {yaml["updated"]!r}')

        # 字段覆盖：md 优先，ini 回落
        title = yaml.get('title') or it['title'] or title_from_file(it['file'])
        desc  = yaml.get('description') if 'description' in yaml else it['desc']
        if desc is None:
            desc = it['desc']
        category = yaml.get('category') or it['category']
        if 'tags' in yaml and yaml['tags']:
            tags = [t.strip() for t in re.split(r'[,，]', yaml['tags']) if t.strip()]
        else:
            tags = it['tags']
        author = yaml.get('author') or SITE_AUTHOR

        merged.append({
            'file':      it['file'],
            'title':     title,
            'desc':      desc,
            'category':  category,
            'tags':      tags,
            'author':    author,
            'md_path':   md_path,
            '_pub_dt':   pub_dt,
            '_upd_dt':   upd_dt,
        })

    return merged


# ════════════════════════════════════════════════════════════
#  生成 RSS
# ════════════════════════════════════════════════════════════
def post_url(file):
    base = SITE_URL.rstrip('/')
    prefix = POST_BASE.strip('/')
    path = quote(file.replace('\\', '/'), safe='/')
    return f'{base}/{prefix}/{path}' if prefix else f'{base}/{path}'


def build_xml(items):
    feed_url = SITE_URL.rstrip('/') + '/' + FEED_PATH.lstrip('/')

    channel_pub   = max(it['_pub_dt'] for it in items)
    channel_build = max(it['_upd_dt'] for it in items)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '     xmlns:atom="http://www.w3.org/2005/Atom"',
        '     xmlns:dc="http://purl.org/dc/elements/1.1/">',
        '  <channel>',
        f'    <title>{xesc(SITE_NAME)}</title>',
        f'    <link>{xesc(SITE_URL)}</link>',
        f'    <description>{xesc(SITE_DESC)}</description>',
        f'    <language>{xesc(SITE_LANG)}</language>',
        f'    <copyright>{xesc(CHANNEL_COPYRIGHT)}</copyright>',
        f'    <managingEditor>{xesc(MANAGING_EDITOR)}</managingEditor>',
        f'    <webMaster>{xesc(WEBMASTER)}</webMaster>',
        f'    <ttl>{int(TTL_MINUTES)}</ttl>',
        f'    <docs>{xesc(DOCS_URL)}</docs>',
        f'    <category>{xesc(CHANNEL_CATEGORY)}</category>',
        '    <image>',
        f'      <url>{xesc(IMAGE_URL)}</url>',
        f'      <title>{xesc(IMAGE_TITLE)}</title>',
        f'      <link>{xesc(IMAGE_LINK)}</link>',
        '    </image>',
        f'    <pubDate>{format_datetime(channel_pub)}</pubDate>',
        f'    <lastBuildDate>{format_datetime(channel_build)}</lastBuildDate>',
        '    <generator>genrss.py</generator>',
        f'    <atom:link href="{xesc(feed_url)}" rel="self" type="application/rss+xml"/>',
    ]

    for it in items:
        link  = post_url(it['file'])
        title = strip_hover_hint(it['title']).strip() or title_from_file(it['file'])
        desc  = strip_hover_hint(it['desc']).strip()

        lines.append('    <item>')
        lines.append(f'      <title>{xesc(title)}</title>')
        lines.append(f'      <link>{xesc(link)}</link>')
        lines.append(f'      <guid isPermaLink="true">{xesc(link)}</guid>')
        lines.append(f'      <pubDate>{format_datetime(it["_pub_dt"])}</pubDate>')
        lines.append(f'      <atom:updated>{it["_upd_dt"].isoformat()}</atom:updated>')

        if it['category']:
            lines.append(f'      <category domain="{xesc(CATEGORY_DOMAIN)}">'
                         f'{xesc(it["category"])}</category>')
        for tag in it['tags']:
            lines.append(f'      <category domain="{xesc(TAG_DOMAIN)}">'
                         f'{xesc(tag)}</category>')

        lines.append(f'      <description>{xesc(desc)}</description>')
        lines.append(f'      <dc:creator>{xesc(it["author"])}</dc:creator>')
        lines.append('    </item>')

    lines += ['  </channel>', '</rss>', '']
    return '\n'.join(lines)


# ════════════════════════════════════════════════════════════
#  路径解析
# ════════════════════════════════════════════════════════════
def _find_docs(project_dir):
    cand = os.path.join(project_dir, *DOCS_SUBDIR.split('/'))
    return cand


def resolve_paths(user_input):
    """返回 (project_dir, blog_dir, docs_dir)；失败 None, None, None"""
    p = os.path.expanduser(str(user_input).strip().strip('"').strip("'"))
    if not p:
        return None, None, None

    if os.path.isfile(p) and p.lower().endswith(INDEX_NAME):
        blog_dir = os.path.dirname(os.path.abspath(p))
        project_dir = os.path.dirname(blog_dir)
        return project_dir, blog_dir, _find_docs(project_dir)

    p = os.path.abspath(p)
    if not os.path.isdir(p):
        alt = os.path.join(SCRIPT_DIR, p)
        if os.path.isdir(alt):
            p = alt
        else:
            return None, None, None

    # A：项目根目录
    if os.path.isfile(os.path.join(p, BLOG_SUBDIR, INDEX_NAME)):
        return p, os.path.join(p, BLOG_SUBDIR), _find_docs(p)

    # B：直接给 blog 目录
    if os.path.isfile(os.path.join(p, INDEX_NAME)):
        project_dir = os.path.dirname(p)
        return project_dir, p, _find_docs(project_dir)

    return None, None, None


# ════════════════════════════════════════════════════════════
#  主流程
# ════════════════════════════════════════════════════════════
def main():
    argv = sys.argv[1:]
    user_input = None
    out_path = os.path.join(SCRIPT_DIR, 'rss.xml')

    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('-h', '--help'):
            print(__doc__)
            return 0
        if a in ('-o', '--output') and i + 1 < len(argv):
            out_path = os.path.abspath(os.path.expanduser(argv[i + 1]))
            i += 2
            continue
        if user_input is None:
            user_input = a
        i += 1

    if not user_input:
        try:
            user_input = input('请输入项目目录（包含 blog/index.ini）: ')
        except (EOFError, KeyboardInterrupt):
            print('\n已取消。')
            return 1

    project_dir, blog_dir, docs_dir = resolve_paths(user_input)
    if not blog_dir:
        fail(f'找不到项目目录或 blog/index.ini: {user_input}')

    if not os.path.isfile(os.path.join(blog_dir, INDEX_NAME)):
        fail(f'缺少 {INDEX_NAME}: {os.path.join(blog_dir, INDEX_NAME)}')

    if not os.path.isdir(docs_dir):
        fail(f'docs 目录不存在: {docs_dir}')

    print(f'[*] 项目目录: {project_dir}')
    print(f'[*] blog 目录: {blog_dir}')
    print(f'[*] docs 目录: {docs_dir}')

    items = collect_items(blog_dir, docs_dir)

    # 按 pubDate 倒序
    items.sort(key=lambda it: it['_pub_dt'], reverse=True)

    if MAX_ITEMS and len(items) > MAX_ITEMS:
        items = items[:MAX_ITEMS]

    xml = build_xml(items)

    try:
        with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(xml)
    except OSError as e:
        fail(f'写入失败: {e}')

    print(f'[√] 已生成 {len(items)} 条文章')
    print(f'[√] 输出文件: {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())