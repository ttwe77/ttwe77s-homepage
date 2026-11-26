# 构建流程说明

## 入口

调用方只需给出两项：

1. Markdown 文件路径（建议已在 `tools/genblog/docs/` 下）。
2. SVG 图标：可以是文件路径，也可以是内联 `<svg>...</svg>` 字符串。

调用前先检查 Markdown 顶部的 YAML 块：没有 `---` 包裹的 front matter，或字段不全时，由 AI 先补全再执行下面的命令。完整规则见 `references/front-matter.md`。时间字段必须用系统命令 `date '+%Y-%m-%d %H:%M:%S'` 获取，精确到秒，禁止编造。

统一执行（从项目根 `<current working directory>`）：

```powershell
$py = (cmd /c where python 2>$null | Select-Object -First 1); if (-not $py) { throw "python not found" }; & $py "skills/genblog-publish/scripts/publish_blog.py" "<md>" "<svg-or-svg-path>"
```

注意这里**不能**直接用 `python`——它指向 WorkBuddy 自带的 Python（无 `pygments`），会在渲染阶段失败。详见下方「踩坑记录」。

若 Markdown 不在 `tools/genblog/docs/`，脚本会复制到该目录后再构建，因为 RSS 生成器靠“HTML 文件名 -> docs 同名 md”回查 front matter。

## 各步骤职责

| 步骤 | 脚本 / 文件 | 作用 |
| --- | --- | --- |
| -1 | AI 检查 / 生成 front matter | 读取 Markdown，没有 YAML 块就生成完整 10 字段（`title/description/date/category/readtime/author/tags/license/license_url/updated`），有块但缺字段就只补缺失项。`date`/`updated` 用系统时间，格式 `YYYY-MM-DD HH:MM:SS`，精确到秒。规则见 `references/front-matter.md`。 |
| 0 | `tools/genblog/split_page.py sample.html -o parts` | 从样例页拆出可复用模板到 `parts/`；仅当 `parts/head.html` 或 `parts/style.css` 缺失时自动补跑。`parts/` 被 git 忽略。 |
| 1 | `tools/genblog/docs/<stem>.md` | 源文件。front matter 至少要有 `date` 与 `updated`，否则 RSS 生成会失败。`title/description/category/tags/author` 用于页面和清单。 |
| 2 | `tools/genblog/md2page.py` | 解析 front matter，渲染 Markdown，套用 `parts/` 模板，输出 `blog/<stem>.html`。 |
| 3 | 最新页码 `blog/pages/pageN.ini` | 每行一篇文章：`文件 \| 标题 \| 日期 \| 分类 \| 标签 \| 描述 \| SVG`。目标文件由 `blog/index.ini` **最底部那条 `#include`** 决定（前端与 `genrss.py` 都按下往上读，最底下的分页最新）。脚本按文件名匹配，存在则替换整行，不存在则追加到文件**末尾**（页内越靠下越新）。`blog/index.ini` 本身不参与写入，脚本也绝不新建 `pageN.ini`。 |
| 4 | `tools/genblog/subset_fonts.py` | 扫描 `blog/*.html` 的实际用字，重建 `blog/fonts/` 下的字体子集与 `charset-used.txt` / `subset.json`。新文章引入新汉字时必须跑。 |
| 5 | `tools/rss/genrss.py` | 读 `blog/index.ini` 及其全部 `#include` 分页文件，用 HTML 文件名回查 `tools/genblog/docs/<stem>.md`，MD front matter 覆盖 INI 字段，先写 `tools/rss/rss.xml` 预览，确认 `y` 后覆盖根目录 `rss.xml`。构建脚本已自动确认。 |

## 踩坑记录（2026-11-21 实测，务必先看）

这一节记录真实构建中踩过的坑。每条都对应一次失败或一次误判，照做可避免重复排查。

### 坑 1：用错 Python 解释器，`pygments` 导入失败

**现象**：构建在渲染阶段崩溃，报 `ModuleNotFoundError: No module named 'pygments'`（来自 `md2page.py`）。

**根因**：脚本内部所有子进程都用 `sys.executable` 派生（`publish_blog.py` 的 `run()` 全程 `[sys.executable, ...]`）。也就是说「用哪个解释器启动 `publish_blog.py`，整条链就用哪个」。直接敲 `python` 时，PATH 里的 `python` 是 WorkBuddy 自带的 3.13（`C:/Users/ttwe77/.workbuddy/binaries/python/...`），它没装项目依赖。

**正确做法**：用项目一直在用的系统 Python （3.12.4，已装 `pygments 2.20.0`）启动脚本。

**判断方法**：构建前先探测，别猜：

```powershell
$py = (cmd /c where python 2>$null | Select-Object -First 1); if (-not $py) { throw "python not found" }; & $py -c "import pygments, sys; print(sys.version.split()[0], pygments.__version__)"
```

**注意**：这是「换一个带依赖的解释器」，不是「把失败命令原样重试」。原命令重试一万次也不会成功。

### 坑 2：脚本位置决定 `--root`，用错副本就找不到项目路径

**现象**：不传 `--root` 时脚本报缺少必需路径（`tools/genblog/docs` 之类）。

**根因**：`publish_blog.py` 里 `DEFAULT_ROOT = Path(__file__).resolve().parents[3]`，项目根是从**脚本自身位置**往上推 3 级算出来的。历史上这个 skill 有两份内容相同的副本：

| 副本 | 脚本路径 | 默认 root（parents[3]） | 是否需要 `--root` |
| --- | --- | --- | --- |
| 项目内（**唯一真源**） | `<current working directory>/skills/genblog-publish/scripts/` | `<current working directory>` ✅ | 不需要 |
| 用户目录（**可能不存在**） | `C:/Users/ttwe77/.workbuddy/skills/genblog-publish/scripts/` | `C:/Users/ttwe77/.workbuddy` ❌ | **必须**显式传 |

> 2026-11-26 复核：用户目录副本已被移除，只剩项目内这份。它属于项目级 skill，直接可用。

**正确做法**：一律用项目内那份脚本，从项目根执行，不用传 `--root`。若哪天用户目录副本又出现了，用之前务必显式加 `--root`；改规则时若它存在就两份同步，**不存在就只改项目内这份，别擅自重建**。

### 坑 3：内联 SVG 要用单引号包裹，否则双引号被 shell 吃掉

**现象**：dry-run 时图标解析失败，报「图标必须是 `<svg>...</svg>` 文本」。

**根因**：SVG 字符串内部全是双引号（`viewBox="..."`、`fill="..."`），如果再用双引号包裹整个参数，shell 会把内部引号截断，传给脚本的只剩半截。

**正确做法**：Git Bash 下用单引号包裹整个 SVG，再用 `"$SVG"` 传参：

```bash
SVG='<svg viewBox="0 0 1024 1024" ...><path d="..." fill="#fff"/></svg>'
".../publish_blog.py" "<md>" "$SVG" --root "<current working directory>"
```

### 坑 4：字体子集的 `✗ site 失败` 是假警报，别去修

**现象**：构建最后 `subset_fonts.py` 打印若干行 `✗ site 失败`，还伴随「site 需生成（字集变化）」，看着像字体没生成。

**真相**：这是并行生成子字体时的瞬时报错，实际文件是好的——`blog/fonts/` 下既有子集仍在，HTML 引用的 woff2 全部存在，字符覆盖完整，不影响显示。

**正确做法**：不要因为这几行就去改字体、重装工具链或重跑构建。要确认字体是否真的可用，用校验脚本核对 HTML 里**所有** woff2 引用是否都存在（见下方坑 5），而不是看这几行日志。

### 坑 5：校验字体引用要用绝对路径，别自己拼 `blog/fonts/...`

**现象**：自己写校验脚本，把 HTML 里的字体路径拼成 `blog/fonts/xxx.woff2`，结果一堆「文件缺失」的误报。

**根因**：HTML 里的字体 URL 是**站点绝对路径**，形如 `/blog/fonts/...` 和 `/src/ttf/fonts/...`，开头带 `/`。自己拼相对路径时会变成 `blog//blog/fonts/...` 之类，自然找不到。真实位置：site 字体在 `blog/fonts/` 顶层，fallback 字体在 `src/ttf/fonts/`。

**正确做法**：从正则里取出 URL 后先 `lstrip("/")` 再拼本地根：

```python
urls = set(re.findall(r'url\("([^"]+\.woff2)"\)', html))
missing = [u for u in urls if not Path(u.lstrip("/")).exists()]
```

### 坑 6：数悬浮提示气泡别数 `hover-hint__tooltip`

**现象**：插入 11 个悬浮提示后，在生成的 HTML 里数 `hover-hint__tooltip` 得到 31，以为插多了。

**根因**：CSS 选择器定义里也含这个类名字符串，被一起数进去了。实际气泡只有 11 个。

**正确做法**：数真正的气泡标记 `<span class="hint-title">` 或 `class="hover-hint"`，不要数类名字符串。校验 Markdown 侧同理：一次提示 = 3 个 `<span>` 开标签 + 3 个 `</span>`，11 个提示应对应 33 个闭合标签。

### 坑 7：构建前先记 git HEAD，构建后对比

**目的**：skill 的硬规则是「绝不 commit / push」。光看 `git status` 只能证明有改动，不能证明没动版本历史。

**做法**：构建前 `git rev-parse HEAD` 记下哈希，构建后再跑一次，两者一致才能明确向用户报告「HEAD 未变，无 commit、无 push」。

### 坑 8：页码方向是「倒着」的，别看反

**现象**：手动把新文章塞进 `page1.ini`，结果它出现在列表最底部；或者认定 `page1.ini` 就是最新页，于是新文章永远挤在第 1 页。

**根因**：这套分页索引是**从下往上**读的，两处都一样：

| 层级 | 读取顺序 | 结论 |
| --- | --- | --- |
| `blog/index.ini` | `parseIncludes()` 对 `#include` 列表 `reverse()` | **最底部**的 `#include` 是最新页 |
| `blog/pages/pageN.ini` | `parseIni()` 对行数组 `reverse()` | **最底部**的行是最新文章 |

所以「最新页码」不是编号最大的那个文件，而是 `index.ini` 最后一行 include 指向的那个文件——两者通常一致，但以 include 顺序为准（有人手动插页时可能不一致）。

**正确做法**：不要自己数页码、不要自己挑文件。直接跑脚本，它会打印两行确认目标：

```text
[plan] Newest page ini: <项目根>/blog/pages/page2.ini
[ini] blog/pages/page2.ini: added -> <stem>.html (最新页码)
```

目标文件已被 `index.ini` 引用但文件不存在时，脚本会建一个空文件再写入（否则前端 404）；`index.ini` 里一条 `#include` 都没有时，会退回写 `index.ini` 自身，与前端的兜底行为一致。

## 强制边界

- 禁止执行 `git commit`、`git push`、`git add`、`git tag` 等任何写操作。
- 只读 `git status` / `git log` 可以用于核对工作区状态，但不是必须。
- 构建脚本只改动：`tools/genblog/docs/`（必要时复制 md）、`tools/genblog/parts/`（必要时补模板）、`blog/<stem>.html`、**`blog/index.ini` 最底部 `#include` 指向的那一个分页文件**、`blog/fonts/*`、`rss.xml`。
- 绝不新建 `pageN.ini`，绝不增删或重排 `blog/index.ini` 的 `#include` 行。页数由人决定；若最新页看起来已满、或用户要求开新页，先问，再动手。
- AI 在步骤 -1 中可能改动 Markdown 源文件本身（插入或补齐 front matter）；这只发生在调用构建脚本之前，且必须保留正文原样。
- 构建完成后向用户报告实际改动文件清单（含拿到条目的分页文件名），并明确说明未提交、未推送。

## 校验清单

- Markdown 顶部有 `---` 包裹的 YAML 块，包含完整 10 个字段；`date` 与 `updated` 存在且为 `YYYY-MM-DD HH:MM:SS` 格式（精确到秒）。
- `blog/<stem>.html` 存在，页面 `<title>` 含 front matter 的 `title`。
- `blog/index.ini` **最底部 `#include`** 指向的分页文件中，存在且仅存在一条首列为 `<stem>.html` 的记录，且该行位于文件末尾；其余分页文件行数未变。
- `blog/index.ini` 内容未变（无新增 `#include`，无重排）。
- `rss.xml` 中存在 `https://www.ttwe77.cn/blog/<stem>.html`。
- 工作区有改动，但 HEAD 未变化。
