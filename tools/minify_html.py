#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minify_html.py —— 压缩 HTML，并同时压缩内联的 <style> / <script>

依赖：
    pip install htmlmin2 rcssmin rjsmin

用法：
    python minify_html.py index.html             # 就地覆盖（会先询问确认）
    python minify_html.py index.html -y          # 就地覆盖，不再询问
    python minify_html.py index.html -o out.html # 输出到指定文件
    python minify_html.py index.html -o -        # 输出到 stdout
    cat index.html | python minify_html.py       # 从 stdin 读，写到 stdout
    python minify_html.py ./public -y            # 递归压缩目录下所有 HTML（就地覆盖）
    python minify_html.py index.html --no-inline # 只压缩 HTML 结构
"""

from __future__ import annotations

import argparse
import inspect
import os
import re
import sys
from pathlib import Path

try:
    import htmlmin
    import rcssmin
    import rjsmin
except ImportError as exc:  # pragma: no cover
    sys.exit(f"缺少依赖：{exc}\n请先安装：pip install htmlmin2 rcssmin rjsmin")


# --------------------------------------------------------------------------- #
# 内联标签处理
# --------------------------------------------------------------------------- #

_STYLE_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.IGNORECASE | re.DOTALL)
_SCRIPT_RE = re.compile(
    r"(<script\b(?P<attrs>[^>]*)>)(?P<body>.*?)(</script\s*>)",
    re.IGNORECASE | re.DOTALL,
)
_TYPE_RE = re.compile(r"""\btype\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)

#: 这些 type 的 <script> 内容才是 JS，可以交给 rjsmin
_JS_TYPES = {
    "",
    "module",
    "text/javascript",
    "application/javascript",
    "text/ecmascript",
    "application/ecmascript",
    "text/jscript",
    "text/livescript",
    "text/x-javascript",
    "application/x-javascript",
}


def _is_js_script(attrs: str) -> bool:
    """判断 <script ...> 的内容是不是 JavaScript（JSON-LD / importmap 等要跳过）。"""
    match = _TYPE_RE.search(attrs)
    if not match:
        return True  # 没写 type，默认就是 JS
    value = (match.group(1) or match.group(2) or match.group(3) or "").strip().lower()
    return value in _JS_TYPES


def _minify_style_tags(html: str) -> str:
    """压缩所有 <style> 标签里的 CSS。"""

    def _replace(match: re.Match) -> str:
        opening, body, closing = match.group(1), match.group(2), match.group(3)
        if not body.strip():
            return opening + closing
        try:
            return opening + rcssmin.cssmin(body) + closing
        except Exception as exc:
            print(f"[warn] CSS 压缩失败，已跳过：{exc}", file=sys.stderr)
            return match.group(0)

    return _STYLE_RE.sub(_replace, html)


def _minify_script_tags(html: str) -> str:
    """压缩所有内联 <script> 里的 JS（带 src 或非 JS 类型的会跳过）。"""

    def _replace(match: re.Match) -> str:
        opening, attrs = match.group(1), match.group("attrs")
        body, closing = match.group("body"), match.group(4)

        if not body.strip() or not _is_js_script(attrs):
            return match.group(0)
        try:
            return opening + rjsmin.jsmin(body) + closing
        except Exception as exc:
            print(f"[warn] JS 压缩失败，已跳过：{exc}", file=sys.stderr)
            return match.group(0)

    return _SCRIPT_RE.sub(_replace, html)


# --------------------------------------------------------------------------- #
# 主压缩函数
# --------------------------------------------------------------------------- #

def _filter_supported_kwargs(func, kwargs: dict) -> dict:
    """把 kwargs 里当前版本 htmlmin.minify 不认识的键剔除掉。

    htmlmin 与 htmlmin2 的参数集不一样（例如 htmlmin2 去掉了 minify_css /
    minify_js），直接传过去会抛 TypeError。这里用签名自省做一层过滤，
    既兼容旧版也兼容新版。
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return kwargs

    params = sig.parameters
    # 如果函数带 **kwargs，就全部保留
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return kwargs

    return {k: v for k, v in kwargs.items() if k in params}


def minify_html_string(html: str, *, inline: bool = True) -> str:
    """压缩 HTML 字符串。

    :param inline: 是否压缩内联的 <style> / <script>
    """
    if inline:
        html = _minify_style_tags(html)
        html = _minify_script_tags(html)

    kwargs = {
        "remove_comments": True,                 # 去掉 HTML 注释
        "remove_empty_space": True,              # 去掉标签间多余空白
        "remove_all_empty_space": False,
        "reduce_boolean_attributes": True,       # checked="checked" -> checked
        "remove_optional_attribute_quotes": True,
        "keep_pre": True,                        # 保留 <pre> 内格式
        "pre_tags": ("pre", "textarea"),
        # 下面两项只有旧版 htmlmin 支持；htmlmin2 已移除。
        # 内联内容在上面已经手动压过，这里关掉即可。不支持的版本会自动忽略。
        "minify_css": False,
        "minify_js": False,
    }

    supported = _filter_supported_kwargs(htmlmin.minify, kwargs)
    dropped = sorted(set(kwargs) - set(supported))
    if dropped:
        print(
            f"[info] 当前 htmlmin 版本不支持参数：{', '.join(dropped)}，已自动忽略",
            file=sys.stderr,
        )

    try:
        return htmlmin.minify(html, **supported)
    except Exception as exc:
        print(f"[warn] HTML 压缩失败，返回内联压缩后的结果：{exc}", file=sys.stderr)
        return html


# --------------------------------------------------------------------------- #
# 文件 / 目录辅助
# --------------------------------------------------------------------------- #

_HTML_EXTS = {".html", ".htm", ".xhtml"}


def _confirm(prompt: str, assume_yes: bool) -> bool:
    """询问用户是否继续。assume_yes 为 True 时直接放行。

    提示写到 stderr，避免污染 stdout（例如 `> out.html` 重定向时）。
    """
    if assume_yes:
        return True
    sys.stderr.write(f"{prompt} [y/N] ")
    sys.stderr.flush()
    try:
        answer = sys.stdin.readline()
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        return False
    if not answer:  # EOF（例如 stdin 被重定向且没有输入）
        sys.stderr.write("\n")
        return False
    return answer.strip().lower() in ("y", "yes")


def _print_stats(label: str | None, before: int, after: int) -> None:
    ratio = (1 - after / before) * 100 if before else 0.0
    prefix = f"{label}: " if label else ""
    print(f"{prefix}{before} -> {after} bytes  (-{ratio:.1f}%)", file=sys.stderr)


def _collect_html_files(root: Path) -> list[Path]:
    """递归收集目录下所有 HTML 文件（跳过以 . 开头的隐藏目录）。"""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if Path(name).suffix.lower() in _HTML_EXTS:
                found.append(Path(dirpath) / name)
    return found


def _process_directory(root: Path, *, inline: bool, assume_yes: bool, quiet: bool) -> int:
    """递归压缩目录下的所有 HTML（就地覆盖）。"""
    files = _collect_html_files(root)
    if not files:
        print(f"[info] {root} 下没有找到 HTML 文件", file=sys.stderr)
        return 0

    if not _confirm(
        f"将就地压缩 {root} 下的 {len(files)} 个 HTML 文件（会覆盖原文件），是否继续？",
        assume_yes,
    ):
        print("已取消，未修改任何文件。", file=sys.stderr)
        return 1

    total_before = 0
    total_after = 0
    ok = 0
    failed = 0

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[warn] 读取失败，已跳过 {path}：{exc}", file=sys.stderr)
            failed += 1
            continue

        result = minify_html_string(source, inline=inline)

        try:
            path.write_text(result, encoding="utf-8")
        except OSError as exc:
            print(f"[warn] 写入失败，已跳过 {path}：{exc}", file=sys.stderr)
            failed += 1
            continue

        before = len(source.encode("utf-8"))
        after = len(result.encode("utf-8"))
        total_before += before
        total_after += after
        ok += 1

        if not quiet:
            _print_stats(str(path), before, after)

    if not quiet:
        ratio = (1 - total_after / total_before) * 100 if total_before else 0.0
        tail = f"，{failed} 个失败" if failed else ""
        print(
            f"完成：{ok} 个文件，{total_before} -> {total_after} bytes  (-{ratio:.1f}%){tail}",
            file=sys.stderr,
        )

    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# 命令行
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="压缩 HTML，并同时压缩其中的内联 CSS / JavaScript。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input", nargs="?", default=None,
        help="输入 HTML 文件或目录（省略或用 - 表示从 stdin 读取）",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="输出文件；省略时覆盖原文件，用 - 表示写到 stdout（目录输入时不可用）",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="覆盖原文件时不再询问确认",
    )
    parser.add_argument(
        "--no-inline", action="store_true",
        help="不压缩内联的 <style>/<script>",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="不打印统计信息",
    )
    args = parser.parse_args(argv)

    inline = not args.no_inline

    # ---------- 1) 从 stdin 读取，写到 stdout ----------
    if args.input in (None, "-"):
        source = sys.stdin.read()
        result = minify_html_string(source, inline=inline)
        sys.stdout.write(result)
        if not args.quiet:
            _print_stats(None, len(source.encode("utf-8")), len(result.encode("utf-8")))
        return 0

    target = Path(args.input)
    if not target.exists():
        print(f"[error] 找不到路径：{target}", file=sys.stderr)
        return 2

    # ---------- 2) 目录：递归就地压缩 ----------
    if target.is_dir():
        if args.output is not None:
            print(
                "[error] 输入是目录时不能使用 -o/--output；目录模式会就地覆盖原文件。",
                file=sys.stderr,
            )
            return 2
        return _process_directory(
            target, inline=inline, assume_yes=args.yes, quiet=args.quiet
        )

    # ---------- 3) 单个文件 ----------
    if args.output is None:
        # 未指定输出 -> 就地覆盖，需要确认
        if not _confirm(f"是否覆盖原文件 {target}？", args.yes):
            print("已取消，未修改任何文件。", file=sys.stderr)
            return 1
        out_path: Path | None = target
    elif args.output == "-":
        out_path = None  # 写 stdout
    else:
        out_path = Path(args.output)

    try:
        source = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[error] 读取失败 {target}：{exc}", file=sys.stderr)
        return 2

    result = minify_html_string(source, inline=inline)

    try:
        if out_path is None:
            sys.stdout.write(result)
        else:
            out_path.write_text(result, encoding="utf-8")
    except OSError as exc:
        print(f"[error] 写入失败 {out_path}：{exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        _print_stats(
            str(target),
            len(source.encode("utf-8")),
            len(result.encode("utf-8")),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())