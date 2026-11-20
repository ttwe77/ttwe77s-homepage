# 构建流程说明

## 入口

调用方只需给出两项：

1. Markdown 文件路径（建议已在 `tools/genblog/docs/` 下）。
2. SVG 图标：可以是文件路径，也可以是内联 `<svg>...</svg>` 字符串。

调用前先检查 Markdown 顶部的 YAML 块：没有 `---` 包裹的 front matter，或字段不全时，由 AI 先补全再执行下面的命令。完整规则见 `references/front-matter.md`。时间字段必须用系统命令 `date '+%Y-%m-%d %H:%M:%S'` 获取，精确到秒，禁止编造。

统一执行：

```bash
python skills/genblog-publish/scripts/publish_blog.py "<md>" "<svg-or-svg-path>"
```

若 Markdown 不在 `tools/genblog/docs/`，脚本会复制到该目录后再构建，因为 RSS 生成器靠“HTML 文件名 -> docs 同名 md”回查 front matter。

## 各步骤职责

| 步骤 | 脚本 / 文件 | 作用 |
| --- | --- | --- |
| -1 | AI 检查 / 生成 front matter | 读取 Markdown，没有 YAML 块就生成完整 10 字段（`title/description/date/category/readtime/author/tags/license/license_url/updated`），有块但缺字段就只补缺失项。`date`/`updated` 用系统时间，格式 `YYYY-MM-DD HH:MM:SS`，精确到秒。规则见 `references/front-matter.md`。 |
| 0 | `tools/genblog/split_page.py sample.html -o parts` | 从样例页拆出可复用模板到 `parts/`；仅当 `parts/head.html` 或 `parts/style.css` 缺失时自动补跑。`parts/` 被 git 忽略。 |
| 1 | `tools/genblog/docs/<stem>.md` | 源文件。front matter 至少要有 `date` 与 `updated`，否则 RSS 生成会失败。`title/description/category/tags/author` 用于页面和清单。 |
| 2 | `tools/genblog/md2page.py` | 解析 front matter，渲染 Markdown，套用 `parts/` 模板，输出 `blog/<stem>.html`。 |
| 3 | `blog/pages/page1.ini` | 每行一篇文章：`文件 | 标题 | 日期 | 分类 | 标签 | 描述 | SVG`。脚本按文件名匹配，存在则替换整行，不存在则追加到末尾。`blog/index.ini` 只需 `#include pages/page1.ini`，通常不用改。 |
| 4 | `tools/genblog/subset_fonts.py` | 扫描 `blog/*.html` 的实际用字，重建 `blog/fonts/` 下的字体子集与 `charset-used.txt` / `subset.json`。新文章引入新汉字时必须跑。 |
| 5 | `tools/rss/genrss.py` | 读 `blog/index.ini` -> `pages/page1.ini`，用 HTML 文件名回查 `tools/genblog/docs/<stem>.md`，MD front matter 覆盖 INI 字段，先写 `tools/rss/rss.xml` 预览，确认 `y` 后覆盖根目录 `rss.xml`。构建脚本已自动确认。 |

## 强制边界

- 禁止执行 `git commit`、`git push`、`git add`、`git tag` 等任何写操作。
- 只读 `git status` / `git log` 可以用于核对工作区状态，但不是必须。
- 构建脚本只改动：`tools/genblog/docs/`（必要时复制 md）、`tools/genblog/parts/`（必要时补模板）、`blog/<stem>.html`、`blog/pages/page1.ini`、`blog/fonts/*`、`rss.xml`。
- AI 在步骤 -1 中可能改动 Markdown 源文件本身（插入或补齐 front matter）；这只发生在调用构建脚本之前，且必须保留正文原样。
- 构建完成后向用户报告实际改动文件清单，并明确说明未提交、未推送。

## 校验清单

- Markdown 顶部有 `---` 包裹的 YAML 块，包含完整 10 个字段；`date` 与 `updated` 存在且为 `YYYY-MM-DD HH:MM:SS` 格式（精确到秒）。
- `blog/<stem>.html` 存在，页面 `<title>` 含 front matter 的 `title`。
- `blog/pages/page1.ini` 中存在且仅存在一条 `<stem>.html` 记录。
- `rss.xml` 中存在 `https://www.ttwe77.cn/blog/<stem>.html`。
- 工作区有改动，但 HEAD 未变化。
