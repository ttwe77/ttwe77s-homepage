# YAML front matter 生成规范

## 何时生成

每次发布前，AI 先读取 Markdown 全文（用 `utf-8-sig` 编码）：

- 文件开头第一行必须是 `---`，且在正文之前有第二个 `---` 作为结束标记。
- 如果两个 `---` 都不存在，或中间没有任何 `key: value` 字段，视为「没有 YAML 块」。
- 没有 YAML 块时，AI 必须生成完整的 10 字段 front matter，写入文件顶部；原有正文整体下移，内容保持不变。
- 已有 YAML 块但字段不全时：保留已有字段的值，只补齐缺失字段；不要擅自覆盖用户已经写好的值。
- 只有用户明确要求时，才允许重新生成或覆盖已有字段。

绝对不要跳过这一步直接调用构建脚本——脚本会因为缺少 `date` / `updated` 而失败。

## 时间字段（date / updated）

不要凭空编造时间。用系统命令获取：

```bash
date '+%Y-%m-%d %H:%M:%S'
```

- `date` = 当前系统时间，格式 `YYYY-MM-DD HH:MM:SS`，精确到秒。
- `updated` = 同一时间（首次生成时与 `date` 相同）。
- 若用户明确提供了发布时间，以用户提供的为准，但仍需精确到秒。

## 10 个字段

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| `title` | AI 根据正文生成 | 优先取正文第一个 `# ` 标题；没有则用 40 字以内概括 |
| `description` | AI 根据正文生成 | 60-120 字摘要，单行，不换行 |
| `date` | 系统时间 | `YYYY-MM-DD HH:MM:SS` |
| `category` | AI 根据正文判断 | 参考 docs 已有分类：编程 / 建站 / 安全 / 前端 / 生活 / 整活 等 |
| `readtime` | AI 估算 | 整数，按正文长度估算阅读分钟数 |
| `author` | 固定 | `ttwe77` |
| `tags` | AI 根据正文生成 | 3-6 个关键词，英文逗号 `,` 分隔，不加 `#` |
| `license` | 固定 | `CC BY-NC 4.0` |
| `license_url` | 固定 | `https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans` |
| `updated` | 系统时间 | `YYYY-MM-DD HH:MM:SS` |

## 格式示例

```yaml
---
title: 示例标题
description: 一句话说明这篇文章讲了什么，60 到 120 字之间，不要换行。
date: 2026-11-21 00:39:02
category: 编程
readtime: 5
author: ttwe77
tags: Python, 语法, 整活
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-11-21 00:39:02
---
```

## 写入注意事项

- 必须写在文件最顶部，前后各一个 `---`；字段顶格写，不要缩进，不要用嵌套结构。
- `description` 和 `tags` 里不要出现 `|`——它在分页 ini（`blog/pages/pageN.ini`）里是字段分隔符，虽然脚本会转义，但从源头避免更省事。
- 值里如果含 `:` 加空格，或含 `#`，用英文双引号把值包起来——脚本会剥离成对引号。
- 写完 front matter 后重新读一遍文件，确认 `date` 和 `updated` 都是精确到秒的格式。
- 不要修改 YAML 块之外的正文内容；原有正文原样保留。
