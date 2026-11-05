#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网易云歌单 HTML 解析器（PyQt5）

依赖：
    pip install pyqt5 beautifulsoup4

用法：
    1. 在浏览器里打开网易云歌单页面，Ctrl+A / Ctrl+C 复制整页（或复制表格 HTML）
    2. 打开本程序，点击「读取剪贴板并解析」，或勾选「自动监视剪贴板」
    3. 结果形如：
           { id: '2093260104', name: 'Shooting Stars', artist: 'KARUT' },
"""

import re
import sys

from bs4 import BeautifulSoup

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QLabel, QCheckBox, QMessageBox, QSplitter,
)


# ----------------------------- 解析核心 -----------------------------

def _clean(text: str) -> str:
    """去掉 &nbsp; 转换后的 \\xa0、多余空白（歌名里可能有 <div class="soil"> 注入的脏字符）"""
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_song_list(html: str):
    """
    从歌单表格 HTML 中解析歌曲信息。
    返回: [{'id': str, 'name': str, 'artist': str}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    songs = []

    for tr in soup.find_all("tr"):
        # ---------- 1. 歌曲 ID ----------
        # 优先取播放按钮上的 data-res-id（这才是真正的歌曲 ID）
        song_id = ""
        ply = tr.find("span", class_="ply")
        if ply is not None and ply.get("data-res-id"):
            song_id = ply["data-res-id"].strip()

        # 兜底：从 /song?id=xxx 链接里取
        if not song_id:
            a = tr.find("a", href=re.compile(r"/song\?id=\d+"))
            if a is not None:
                m = re.search(r"/song\?id=(\d+)", a["href"])
                if m:
                    song_id = m.group(1)

        # ---------- 2. 歌名 ----------
        # <b title="深夕映繁星&nbsp;Nocturnal&nbsp;Illumination">...</b>
        # title 属性是最干净的（内部文本被 <div class="soil"> 插入了脏字符）
        name = ""
        b = tr.find("b")
        if b is not None:
            name = _clean(b.get("title") or b.get_text())
        if not name:
            txt = tr.find("span", class_="txt")
            if txt is not None:
                name = _clean(txt.get_text())

        # ---------- 3. 歌手 ----------
        # 第 4 个 td（索引 3）是歌手列，里面的 div.text 带 title 属性
        artist = ""
        tds = tr.find_all("td", recursive=False)
        if len(tds) >= 4:
            div = tds[3].find("div", class_="text")
            if div is not None:
                if div.get("title"):
                    artist = _clean(div["title"])
                else:
                    parts = [_clean(a.get_text()) for a in div.find_all("a")]
                    parts = [p for p in parts if p]
                    artist = "/".join(parts) if parts else _clean(div.get_text())

        if not song_id and not name:
            continue  # 表头行 / 空行

        songs.append({"id": song_id, "name": name, "artist": artist})

    return songs


def format_result(songs) -> str:
    """生成目标格式文本"""
    lines = []
    for s in songs:
        name = s["name"].replace("\\", "\\\\").replace("'", "\\'")
        artist = s["artist"].replace("\\", "\\\\").replace("'", "\\'")
        lines.append(
            f"        {{ id: '{s['id']}', name: '{name}', artist: '{artist}' }},"
        )
    return "\n".join(lines)


# ----------------------------- 界面 -----------------------------

class SongListParser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网易云歌单 HTML → 数组格式")
        self.resize(900, 660)
        self._last_clip_html = ""
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        bar = QHBoxLayout()
        self.btn_paste = QPushButton("读取剪贴板并解析")
        self.btn_parse = QPushButton("解析下方 HTML")
        self.btn_copy = QPushButton("复制结果")
        self.btn_clear = QPushButton("清空")
        self.chk_auto = QCheckBox("自动监视剪贴板")

        for w in (self.btn_paste, self.btn_parse, self.btn_copy, self.btn_clear):
            bar.addWidget(w)
        bar.addStretch(1)
        bar.addWidget(self.chk_auto)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText(
            "把从网易云歌单页面复制的 HTML 粘贴到这里，然后点「解析下方 HTML」……"
        )

        self.output_edit = QPlainTextEdit()
        self.output_edit.setPlaceholderText("解析结果会显示在这里")
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.output_edit.setFont(mono)

        splitter.addWidget(self.input_edit)
        splitter.addWidget(self.output_edit)
        splitter.setSizes([280, 340])
        root.addWidget(splitter, 1)

        self.status = QLabel("就绪：请先复制歌单页面，然后点击「读取剪贴板并解析」")
        root.addWidget(self.status)

        # 信号
        self.btn_paste.clicked.connect(self.parse_from_clipboard)
        self.btn_parse.clicked.connect(
            lambda: self._run_parse(self.input_edit.toPlainText())
        )
        self.btn_copy.clicked.connect(self.copy_result)
        self.btn_clear.clicked.connect(self.clear_all)
        self.chk_auto.toggled.connect(self._toggle_watch)

    # ---------- 剪贴板 ----------
    @staticmethod
    def _clipboard_html() -> str:
        cb = QApplication.clipboard()
        md = cb.mimeData()
        # 浏览器复制的是富文本，HTML 在 mimeData().html() 里
        if md is not None and md.hasHtml():
            return md.html()
        return cb.text()

    def parse_from_clipboard(self):
        html = self._clipboard_html()
        if not html or not html.strip():
            self.status.setText("剪贴板为空")
            return
        self.input_edit.setPlainText(html)
        self._run_parse(html)

    def _toggle_watch(self, checked: bool):
        cb = QApplication.clipboard()
        if checked:
            cb.dataChanged.connect(self._on_clip_changed)
            self.status.setText("已开启剪贴板监视，复制歌单页面即可自动解析")
        else:
            try:
                cb.dataChanged.disconnect(self._on_clip_changed)
            except (TypeError, RuntimeError):
                pass
            self.status.setText("已关闭剪贴板监视")

    def _on_clip_changed(self):
        html = self._clipboard_html()
        if not html or html == self._last_clip_html or "<tr" not in html:
            return
        self._last_clip_html = html
        self.input_edit.setPlainText(html)
        self._run_parse(html)

    # ---------- 解析 & 输出 ----------
    def _run_parse(self, html: str):
        if not html or not html.strip():
            self.status.setText("没有可解析的 HTML 内容")
            return

        try:
            songs = parse_song_list(html)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "解析失败", f"解析出错：\n{e}")
            self.status.setText("解析失败")
            return

        if not songs:
            self.output_edit.setPlainText("")
            self.status.setText("未解析到歌曲，请确认复制的是歌单表格所在的 HTML")
            return

        self.output_edit.setPlainText(format_result(songs))
        self.status.setText(f"解析完成：共 {len(songs)} 首歌曲")

    def copy_result(self):
        text = self.output_edit.toPlainText()
        if not text.strip():
            self.status.setText("没有可复制的结果")
            return
        QApplication.clipboard().setText(text)
        self.status.setText("结果已复制到剪贴板")

    def clear_all(self):
        self.input_edit.clear()
        self.output_edit.clear()
        self._last_clip_html = ""
        self.status.setText("已清空")


def main():
    app = QApplication(sys.argv)
    w = SongListParser()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()