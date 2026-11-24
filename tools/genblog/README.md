# tools/genblog

把 Markdown 渲染成博客文章页面的工具链。**模板的唯一源头是 `sample.html`**，
`parts/` 是它切出来的中间产物，`blog/*.html` 是最终产物 —— 三层不要搞混。

```
sample.html ──split_page.py──▶ parts/ ──md2page.py──▶ blog/<stem>.html
   (模板源)                     (中间产物)   ▲              │
                                            │              ├─ subset_fonts.py ─▶ blog/fonts/
                                     docs/*.md             └─ tools/rss/genrss.py ─▶ rss.xml
                                      (正文源)
```

## 目录说明

| 路径 | 作用 | 能否手改 |
| --- | --- | --- |
| `sample.html` | 整页模板：`<head>`、`<style>`、顶栏、目录、字体弹窗、全部 `<script>` | ✅ 改样式/脚本只改这里 |
| `parts/` | `split_page.py` 切出来的零件，`md2page.py` 读它拼页面 | ❌ 生成物（已被 .gitignore 忽略） |
| `split_page.py` | 按 `TARGETS` 选择器从 `sample.html` 抽零件 | ✅ 新增零件类型时要改 |
| `md2page.py` | Markdown → HTML，负责组装；**不含任何样式** | ✅ 改渲染逻辑 |
| `docs/*.md` | 文章源文件，含 YAML front matter | ✅ |
| `parts/manifest.json` | 每个零件在 `sample.html` 里的行号与大小，重切后对差异用 | 自动生成 |
| `subset_fonts.py` | 字体子集化，输出 `blog/fonts/`，兜底字体在 `src/ttf/` | 一般不动 |
| `hover-hint.py` | PyQt5 小工具，交互式插 hover-hint，不是构建步骤 | 一般不动 |
| `data/charset-8105.txt` | 兜底字体用的《通用规范汉字表》8105 字 | 一般不动 |
| `build.bat` | 两步快捷方式：重切 parts + 渲染 `docs\MDTest.md` | ✅ |

## 常用命令

统一用这个解释器（**别用 WorkBuddy 自带的 python**，缺 `pygments` 会中途炸）：

```bash
PY="E:/Windows11/0Tools/Python/python.exe"
```

```bash
# 1. 改了 sample.html 之后，必须重切 parts
"$PY" tools/genblog/split_page.py tools/genblog/sample.html -o tools/genblog/parts

# 2. 渲染单篇（默认输出到「与 .md 同目录」）
"$PY" tools/genblog/md2page.py tools/genblog/docs/xxx.md

# 3. 渲染到指定位置（想进博客就显式指到 blog/）
"$PY" tools/genblog/md2page.py tools/genblog/docs/xxx.md -o blog/xxx.html

# 4. 渲染到临时目录做预览，不碰 blog/
"$PY" tools/genblog/md2page.py tools/genblog/docs/xxx.md -o tools/genblog/.tmp/xxx.html

# 5. 整链发布（front matter 校验 → 渲染 → page1.ini → 字体子集 → rss）
"$PY" skills/genblog-publish/scripts/publish_blog.py <md路径> <svg图标或路径>
```

`build.bat` 就是第 1 步 + `md2page.py docs\MDTest.md`，**它的输出落在 `docs/MDTest.html`**，
不会覆盖线上文章 —— 这点别自己吓自己。

## 坑（按被坑频率排序）

### 1. 改 `parts/` 等于没改

`parts/*` 是 `split_page.py` 的产物且在 .gitignore 里。直接改 `parts/style.css` 或
`parts/scripts.html`，下次有人跑一次 `split_page.py`（或删了 `parts/` 让
`publish_blog.py` 自动重切）就全部蒸发。**永远改 `sample.html`，然后重切。**

重切后请 diff 一下其它零件，确认没漂移：

```bash
diff -u <备份>/topbar.html tools/genblog/parts/topbar.html   # 除 style.css / scripts.html 外都应为空
```

`publish_blog.py` 只在 `parts/style.css` 或 `parts/head.html` **缺失**时才重切，
所以现有的 parts 不会被它偷偷覆盖。

### 2. `split_page.py` 只认 `TARGETS` 里登记的选择器

它会导出：`head` / `style` / `topbar` / `read_progress` / `article_head` / `article_body` /
`toc` / `toc_toggle` / `to_top` / `font_modal` / `footer`，外加**全部 `<script>`
（`id="theme-init"`、`id="font-init"` 除外 —— 它们必须留在 `<head>` 里提前执行，防止刷新闪白）**。

其余 body 元素（新增的浮层、弹窗、提示条）**不会被导出**。两种正确做法：

- 在 `split_page.py` 的 `TARGETS` 里加一行（`font_modal` 就是这么来的，按 `id` 认）；
- 或者像「SVG 全屏放大层」那样，DOM 交给 JS 首次点击时动态创建，`sample.html` 里只放样式和脚本。

### 3. `scripts.html` 的注释是语法，不是装饰

格式必须是 `<!-- script #N · <script ...> -->` 紧跟脚本正文，`rebuild_scripts()` 靠它还原
`<script>` 标签。手写脚本时照抄格式；**脚本正文里不能出现 `</script>` 字面量**，否则页面在
那里就被截断。

### 4. 默认输出不是 `blog/`

`md2page.py` 不给 `-o` 时写到「`.md` 同目录」。想要线上页面必须显式
`-o blog/<stem>.html`，且别忘了 `page1.ini` 和 rss 那两步（用 `publish_blog.py` 最省事）。

### 5. 条件注入的脚本：改判断要同步

`build_page()` 里两处按内容特征注入：

- `class="mermaid"` 出现在正文 → 注入 mermaid 渲染脚本；
- `class="math-block"` / `class="math-inline"` → 注入 MathJax。

如果你改了渲染器输出的类名，却忘了同步这两个判断，页面看起来「样式对了但图不渲染」，
而且控制台一片安静。

### 6. 深色模式会反色正文 SVG

```css
:root[data-theme="dark"] .article-body svg { filter: invert(1) hue-rotate(180deg); }
:root[data-theme="dark"] .mermaid-wrap svg { filter: none; }   /* mermaid 自带深色主题 */
```

任何新的 SVG 容器要么自带深色配色并把自己排除掉，要么老实吃这条反色。放大层里克隆的
原生 SVG **故意**沿用反色（与正文一致），mermaid 用 `.is-mermaid` 排除 —— 别「优化」掉。

### 7. 原生 HTML 块必须从行首开始

`HTML_BLOCK_START_RE` 只匹配 `^\s*<div|<svg|...`：行首（允许缩进）必须是标签本身，
前面**不能有文字**，否则整块被当成普通段落转义，页面上会看到一堆源码。单行写完整个
`<svg>…</svg>` 是允许的（`docs/AI-Roasts-My-Playlist.md` 就是一行一个图）。

块的**结束**位置由 `scan_html_tags()` 维护的标签栈决定，自闭合标签（`<path/>`）和
void 标签（`<br>`）都不入栈。别改回「开标签数 − 闭标签数 − 自闭合数」那套算法：开标签
正则本来就不统计自闭合标签，再减一次等于倒扣一层深度，`<defs>` 里的第一个 `<path/>`
就会让 `</defs>` 被误判成块结束 —— 整张图的剩余部分会掉进一个 `<p>` 里，页面上看不到
图，只看到一行源码。

### 8. 脚注状态是模块级全局

`_footnote_defs` / `_footnote_order` 在 `process_one()` 开头被清空。新加批处理入口时
别绕过它，否则上一篇的脚注会串到下一篇。

### 9. 解释器与依赖

- `md2page.py` → `pygments`
- `subset_fonts.py` → `fonttools` + `brotli`
- `hover-hint.py` → `PyQt5`

`publish_blog.py` 用 `sys.executable` 串起所有子步骤，**启动它的解释器就是全链路用的解释器**，
所以一开始就用对，别指望中途换。

### 10. mermaid / MathJax 走 CDN

`MERMAID_SCRIPT` 从 `cdn.jsdelivr.net` 拉 `mermaid@11`，`MATH_SCRIPT` 拉 `mathjax@3`。
断网或 CDN 不通时，`<pre class="mermaid">` 会保持源码形态（这是设计好的兜底，不是 bug），
放大功能自然也点不出来 —— 因为压根没有 svg。要离线可用就把 CDN 地址换成 `libs/` 下的本地文件。

## 已实现：SVG / Mermaid 单击全屏放大

代码位置（都在 `sample.html`，`md2page.py` 未改）：

- `<style>` 末尾的「SVG / Mermaid 单击全屏放大」样式块（约 260 行）；
- `</body>` 前一个独立 `<script>`（IIFE，约 450 行）。

行为：

- **命中**：`.mermaid-wrap` 容器；正文里宽 ≥160px、高 ≥64px 的独立 `<svg>`。
  提示框图标、按钮图标、链接里的 svg 一律排除。
- **打开**：克隆 SVG 到全屏层，按视口适配居中；不移动原节点，所以不干扰 mermaid 重渲染。
- **操作**：滚轮/双指缩放（40%–800%）、拖动平移（越界回弹）、双击「适配 ⇄ 2 倍」、
  `+` / `-` / `0` 快捷键；Esc、点空白、右上角 × 关闭。
- **深色**：原生 SVG 继续反色，mermaid 不反色。
- **清晰度**：`.svg-zoom__canvas` **不要**加 `will-change: transform`。加上之后 Chrome
  会把这一层锁在打开时的栅格比例（约 1x），`scale(2)` 以上等于位图拉伸，8 倍时中文直接
  糊成一片；去掉后每次缩放停稳都会按当前比例重新栅格，矢量文字保持清晰。`sample.html`
  里那段注释别删。
- **主题切换**：若当前是 mermaid 放大层则自动收起（mermaid 会按新主题重渲染，旧克隆配色过期）。
- **竞态**：`close()` 有 240ms 清理定时器，与再次 `open()` 用 `cleanTimer` 互斥，别删。

## 验证方式（无浏览器插件也能测）

用 headless Chrome 注入断言脚本，`--dump-dom` 把结果抓出来：

```bash
CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe"
"$CHROME" --headless=new --disable-gpu --ignore-certificate-errors --no-sandbox \
  --window-size=1440,900 --virtual-time-budget=25000 --dump-dom \
  "https://100.99.88.77/tools/genblog/.tmp/test.html"
```

两个已踩过的坑：

1. **虚拟时钟不推进 CSS transition**：`opacity` 会停在 0，截出来的图看不到浮层。
   测试页里先注入 `*{transition:none!important;animation:none!important}`。
2. **`--window-size` 有最小宽度限制**（约 500px）：写 `390` 会按 518 布局再裁图，
   看起来像「内容溢出」。窄屏断点用 `520` 测。

截图存 `.screenshots/` 即可，别往 `blog/` 或 `docs/` 塞。

## 不要做的事

- 不要提交 `parts/`（已 ignore），也不要把它当「源文件」写进别处的文档。
- 不要为了看一眼效果去重建 `blog/` 全部文章 —— 单篇 `-o` 到临时目录就行。
- 不要在 `blog/` 里手改 HTML：下次重建就没了，要改就改 `sample.html`。
- `.tmp/` 只是验证用的草稿区，测完删掉，别让它变成第二个 `parts/`。
