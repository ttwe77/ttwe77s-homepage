---
name: genblog-publish
description: Build a ttwe77s-homepage blog article from a Markdown file and an SVG icon. This skill should be used when the user supplies a Markdown path plus an SVG icon (file path or inline SVG) and asks to build/publish/generate the article into this repository's blog directory. It checks and generates the full YAML front matter block when missing, renders HTML, registers the entry into the newest page list declared by the last `#include` in `blog/index.ini`, rebuilds font subsets and RSS, and never runs git commit or git push.
agent_created: true
---

# Genblog Publish

## Purpose

Turn one Markdown article and one SVG card icon into a fully wired blog page in `ttwe77s-homepage`: a complete YAML front matter block at the top of the Markdown, HTML under `blog/`, an entry in the **newest page ini** (`blog/pages/pageN.ini`), refreshed font subsets, and an updated `rss.xml`.

## Which page list to write (最新页码规则)

`blog/index.ini` is only a pagination order — it holds nothing but `#include` lines:

```ini
#include pages/page1.ini
#include pages/page2.ini
; ↑ 最底部那条 = 最新页码
```

- **最新页码 = `blog/index.ini` 最后一条 `#include` 指向的文件。** Both the frontend (`parseIncludes`) and `genrss.py` read includes bottom-up, so the last include is the newest page, and the bottom line of a page ini is its newest article.
- The script resolves this automatically. Never hardcode `page1.ini`, and never decide the page number yourself.
- **Never create a new `pageN.ini` and never add `#include` to `index.ini`.** The page count is a human decision. If the newest page looks full, or the user wants a new page, ask before touching `index.ini`.
- The entry always goes to the **bottom** of that page file. The frontend reverses each page list, so the bottom line is what shows first.
- Do not reorder or rewrite other lines.

## Hard rules

- Never run `git commit`, `git push`, `git add`, `git tag`, or any other git write command.
- Do not stage changes. Do not create commits. Do not push.
- Read-only git commands such as `git status` are allowed only for verification.
- Report every changed file at the end and explicitly state: no commit, no push.
- The page ini target is derived from `blog/index.ini` — the last `#include` wins. Never hand-pick a page number, never create `pageN.ini`, never edit the `#include` list. At the end, report which page file received the entry.
- Never invent `date` or `updated`. Obtain them from the system clock with `date '+%Y-%m-%d %H:%M:%S'`; both must include time to the second. See `references/front-matter.md`.
- Before building, insert hover hints into the Markdown yourself according to `references/hover-hint.md`. Use search tools for unfamiliar terms; never guess an explanation. Do not open `hover-hint.py` for this.
- After every successful build, report which explanations you inserted (term / hint title / summary / whether verified by search), or state explicitly that no hints were needed. This explanation is mandatory. See `references/hover-hint.md`.
- Before building, verify the chosen Python interpreter can import `pygments`. The builder spawns every sub-step with `sys.executable`, so the interpreter that launches the script is the interpreter used for the whole chain. A missing dependency here breaks the build at the render stage — this is an environment switch, not a command to retry. See `references/WORKFLOW.md` → 踩坑记录.
- The project copy (`<current working directory>/skills/genblog-publish/`) is the source of truth; its default root resolves correctly on its own. If a user-directory copy (`~/.workbuddy/skills/genblog-publish/`) also exists, keep both in sync when editing rules — but that copy may be absent, in which case change only the project one and do not recreate it unasked. If you do use the user-directory copy, you MUST pass `--root "<current working directory>"` explicitly. See `references/WORKFLOW.md` → 踩坑记录.

## Required inputs

Ask the user for both items if either is missing. Do not guess them.

1. Markdown article path. Prefer files already in `tools/genblog/docs/`.
2. SVG icon. Accept either a file path or an inline `<svg>...</svg>` string.

The Markdown does not need a pre-existing front matter block. If one is missing or incomplete, this skill generates it in step 0 below.

## Workflow

### 0. Check and generate YAML front matter

Before anything else, read the Markdown and check for a `---` ... `---` YAML block at the top.

- If the block is absent, generate the full 10 fields and insert them at the top of the file, preserving the body verbatim.
- If the block exists but fields are missing, keep the existing values and add only the missing ones. Never overwrite user-provided values without an explicit request.
- `date` and `updated` must be obtained from `date '+%Y-%m-%d %H:%M:%S'` — never guessed — and must include time to the second.
- Fixed values: `author: ttwe77`, `license: CC BY-NC 4.0`, `license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans`.
- Re-read the file after writing to confirm the block is well-formed.

The full field table, format rules, and example live in `references/front-matter.md`. Follow them exactly — the builder fails if `date` or `updated` is missing.

### 1. Run the deterministic builder

From the project root `<current working directory>`, execute with the **system Python that has the build dependencies** (see 踩坑记录 in `references/WORKFLOW.md` — plain `python` resolves to WorkBuddy's bundled interpreter and will fail on `pygments`):

```powershell
$py = (cmd /c where python 2>$null | Select-Object -First 1); if (-not $py) { throw "python not found" }; & $py "skills/genblog-publish/scripts/publish_blog.py" "<md-path>" "<svg-path-or-inline-svg>"
```

If you instead invoke the user-directory copy of this skill, add `--root` (its `DEFAULT_ROOT` points at `~/.workbuddy`, not the project):

```powershell
$py = (cmd /c where python 2>$null | Select-Object -First 1); if (-not $py) { throw "python not found" }; & $py "skills/genblog-publish/scripts/publish_blog.py" "<md-path>" "<svg>" --root "<current working directory>"
```

The script performs, in order:

1. Copy the Markdown into `tools/genblog/docs/` if it is not already there.
2. Rebuild `tools/genblog/parts/` from `tools/genblog/sample.html` if the template parts are missing.
3. Invoke `tools/genblog/md2page.py` to write `blog/<stem>.html`.
4. Resolve the newest page ini from the last `#include` in `blog/index.ini`, then add or replace the `<stem>.html` line at the **bottom** of that file (`[plan] Newest page ini:` and `[ini] ... (最新页码)` print the resolved target).
5. Invoke `tools/genblog/subset_fonts.py` to refresh `blog/fonts/`.
6. Invoke `tools/rss/genrss.py`, automatically confirming `y`, to refresh root `rss.xml`.

Use `--dry-run` first when uncertain about inputs (same interpreter and `--root` rules apply):

```powershell
$py = (cmd /c where python 2>$null | Select-Object -First 1); if (-not $py) { throw "python not found" }; & $py "skills/genblog-publish/scripts/publish_blog.py" "<md>" "<svg>" --dry-run
```

Use `--skip-fonts` or `--skip-rss` only when the user explicitly asks to skip those stages.

Detailed responsibilities and verification checklist live in `references/WORKFLOW.md`.

### 2. Verify the build

Confirm all of the following:

- The Markdown starts with a 10-field YAML block; `date` and `updated` are present and formatted `YYYY-MM-DD HH:MM:SS`.
- `blog/<stem>.html` exists.
- The newest page ini — the file named by the **last** `#include` in `blog/index.ini` — contains exactly one line whose first field (before the first `|`) is `<stem>.html`, and that line is the last non-empty line of the file. Earlier pages keep their line counts unchanged.
- `blog/index.ini` is byte-for-byte unchanged (no new `#include`, no reordering).
- `rss.xml` contains `https://www.ttwe77.cn/blog/<stem>.html`.
- No git write command was executed.

Optionally run read-only `git status --short` to list changed files.

### 3. Report inserted hover hints

Report the produced HTML path, **which page ini received the entry** (quote the `[ini]` line, e.g. `blog/pages/page2.ini: added (最新页码)`), font/RSS updates, and the unchanged HEAD state.

Before the build, follow `references/hover-hint.md` to add inline `<span class="hover-hint">...</span>` HTML hints directly into the Markdown for terms readers may not know, searching the web when unsure. After the build, list every hint you inserted with its term, hint title, a short summary of the explanation, and whether it was verified by search. If nothing was inserted, say so explicitly. The PyQt5 `hover-hint.py` GUI is only a manual fallback for the user; do not launch it and do not give its tutorial unless asked.

## Resources

- `scripts/publish_blog.py` - the single-entry deterministic builder; contains the no-git-write guarantee.
- `references/WORKFLOW.md` - stage-by-stage file responsibilities and verification checklist.
- `references/front-matter.md` - YAML block generation rules: when to generate, 10 fields, second-precision timestamps, format example.
- `references/hover-hint.md` - rules for AI-inserted hover hints and the mandatory post-build report.
