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
（`id="theme-init"`、`id="font-init"`、`id="plain-init"` 除外 —— 它们必须留在 `<head>` 里提前执行，
防止刷新闪白 / 闪花哨）**。

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

## 已实现：顶栏折叠菜单

字体 / 深色 / 简洁 / 分享 / 首页五个入口收进一个汉堡按键（全部在 `sample.html`）：

- **DOM**：`<header class="topbar">` → `.topbar__actions` → `#btn-menu`（静态 SVG 三条杠，展开时整体旋转 180°）+ `#topbar-menu`（卡片）。
  三条杠的间距必须是 4px：条高（2px）落在半设备像素上时，`175%×4=7`、`125%×4=5` 才能让三条同相位，
  否则中间那条会比上下两条整整多/少一个设备像素 —— 表现就是「三条杠宽度不一」。
  **别把 `.menu-bars` 改回三个 flex `<span>`**：盒模型的逐盒吸附会让这个问题在缩放时反复出现。
  五个条目仍是原来的 `#btn-font` / `#btn-theme` / `#btn-share` / 首页 `<a>`，另加一个 `#btn-plain`；
  **原有 ID 一个都没改**，所以字体弹窗、主题切换、复制链接那三段脚本不用动。
- **为什么塞在 header 里**：`split_page.py` 只导出 `topbar` 这一个 header 零件，面板跟着它一起走。
  挪到 header 外面就必须往 `TARGETS` 里加一行，否则整块面板在产物里凭空消失。
- **交互**：点空白 / `Esc` 收起（`Esc` 会把焦点还给按钮）；字体、分享、首页点完自动收起；
  深色与简洁两个开关**故意不收起**，方便连着切两次对比。上下方向键在条目间循环。
- **状态回填**：展开时读一次 `localStorage['blog-font']` 显示当前字体名；深色开关听 `themechange`
  事件（`apply()` 里派发的那个）；简洁开关读 `<html data-plain>`。
- **`#btn-font.is-active::after`** 那颗小圆点在菜单里被 `content: none` 顶掉了，右侧字体名比圆点信息量大。
- ≤480px 不再隐藏 `#btn-share`（它已经不在顶栏上了），只把面板收窄到 202px。

## 已实现：简洁模式（一键清理）

同样全在 `sample.html`，产物无需 `md2page.py` 配合：

- **入口**：菜单里的 `#btn-plain`，开关样式复用 `.topbar-menu__switch`；标签「简洁模式」，
  `title` / `aria-label` 写的「一键清理」。点一下把花哨样式换成黑白极简，再点一下恢复。
- **状态**：`<html data-plain="on">` + `localStorage['blog-plain']`（`'1'` / `'0'`），全站文章共用。
- **不闪**：`<script id="plain-init">` 放在 `<head>` 里、`<style>` 之前。这个 ID 在
  `split_page.py` 和 `md2page.py` 的「head 脚本白名单」里都登记了，**新增同类脚本记得两处一起加**，
  否则 `fill_head()` 会把它挪到 body 末尾，刷新时先闪一下彩色再变黑白。
- **实现方式**：`sample.html` 末尾追加一整段 `:root[data-plain="on"]` 覆盖，只盖不删；
  颜色令牌全部换成黑 / 白 / 灰，`--shadow-card` 等直接置 `none`，`--btn-skew` 归零。
- **清理范围**：背景光晕与网格、标题渐变、斜切标签、渐变竖条 / 进度条 / 分隔线、引用大引号、
  代码块红黄绿三点（语法高亮改用 `filter: grayscale(1)`，亮度不变所以可读性不掉）、
  五色提示框、表格深色表头、毛玻璃、投影、发光、Toast 圆点光晕、全屏放大层的模糊与投影、
  `BAClickFX` 点击粒子（调 `setPaused(true, { clear: true })`，别用 CSS 藏画布）、
  `/src/cursors/*.cur` 自定义鼠标、字体弹窗的蓝色胶囊与预览渐变、Mermaid 的淡黄 tooltip。
- **深色模式的两处暗坑**：深色主题把 `strong` 写死成 `#8FD8FF`，不补一条
  `:root[data-plain="on"] .article-body strong { color: var(--color-text-primary) }`
  的话，粗体、粗斜体、粗体提示文本会一起留在蓝色；`[!important]` 的图标是 GitHub 原图，
  `fill="#8250df"` 写在 SVG 标签里，只能靠 CSS `fill: currentColor` 覆盖，并顺手
  `filter: none` 挡掉深色模式对正文 SVG 的 `invert`。
- **不清理**：字体（`--font-sans` 一律不动）、正文里的图片 / SVG / Mermaid（属于内容，不是装饰）、
  圆角阶梯、布局与间距，以及作者在正文里手写的内联颜色（如 `style="color: red"`）。
- **深色**：保留，走 `:root[data-theme="dark"][data-plain="on"]` 那组令牌，同样是纯色黑白灰。
- **粒子**：`<head>` 的 module 脚本把实例挂到 `window.__baClickFx`，并在构造后检查一次
  `data-plain`，保证「刷新时简洁模式已开」也不会先放一发粒子。

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
