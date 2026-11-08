#!/usr/bin/env python3
"""
为单文件 HTML 生成严格 CSP（hash 模式，去掉 unsafe-inline）
用法：
  python csp_hash.py input.html            # 原地更新
  python csp_hash.py input.html out.html   # 输出到新文件
"""
import base64, hashlib, re, sys
from pathlib import Path

SCRIPT_RE = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.I | re.S)
STYLE_RE  = re.compile(r'<style\b[^>]*>(.*?)</style\s*>',  re.I | re.S)
CSP_META_RE = re.compile(
    r'<meta\s+http-equiv=["\']Content-Security-Policy["\'][^>]*>', re.I
)

def b64_sha256(text: str) -> str:
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    return base64.b64encode(hashlib.sha256(normalized.encode('utf-8')).digest()).decode('ascii')

def collect(html: str):
    script_hashes, style_hashes = [], []
    for m in SCRIPT_RE.finditer(html):
        attrs, body = m.group(1), m.group(2)
        if re.search(r'\bsrc\s*=', attrs, re.I):   # 外链脚本不由 hash 管
            continue
        if not body.strip():
            continue
        h = "'sha256-%s'" % b64_sha256(body)
        if h not in script_hashes:
            script_hashes.append(h)
    for m in STYLE_RE.finditer(html):
        body = m.group(1)
        if not body.strip():
            continue
        h = "'sha256-%s'" % b64_sha256(body)
        if h not in style_hashes:
            style_hashes.append(h)
    return script_hashes, style_hashes

def build_csp(script_hashes, style_hashes) -> str:
    parts = [
        "default-src 'self'",
        "script-src 'self' " + " ".join(script_hashes),
        "worker-src 'self' blob:",  # 关键逻辑以 Blob 内联 Worker 启动
        "style-src 'self' "  + " ".join(style_hashes),
        "img-src 'self' data:",     # 水印层用 toDataURL 生成 base64 图
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    return "; ".join(p.strip() for p in parts)

def inject_meta(html: str, csp: str) -> str:
    tag = '<meta http-equiv="Content-Security-Policy" content="%s">' % csp
    if CSP_META_RE.search(html):
        return CSP_META_RE.sub(tag, html, count=1)
    m = re.search(r'<head\b[^>]*>', html, re.I)
    if not m:
        return html
    return html[:m.end()] + "\n    " + tag + html[m.end():]

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src

    # 关键：newline='' 必须保留，否则 CRLF 被转成 LF，hash 全错
    with open(src, 'r', encoding='utf-8', newline='') as f:
        html = f.read()

    sh, sth = collect(html)
    csp = build_csp(sh, sth)
    out = inject_meta(html, csp)

    with open(dst, 'w', encoding='utf-8', newline='') as f:
        f.write(out)

    print("已写入:", dst)
    print("脚本 hash 数:", len(sh), " 样式 hash 数:", len(sth))
    print("CSP:", csp)
    return 0

if __name__ == '__main__':
    sys.exit(main())