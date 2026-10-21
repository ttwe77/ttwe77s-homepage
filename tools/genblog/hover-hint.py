#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 悬停提示（hover-hint）替换工具
- 拖入 .md 文件
- 输入：显示的文字 / 提示标题 / 提示内容
- 在编辑器中定位匹配 → 弹窗询问：替换 / 查找下一个 / 取消
- 支持撤销、保存、另存为
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QPlainTextEdit, QMessageBox,
    QFileDialog, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor

class ClickSelectAllLineEdit(QLineEdit):
    """点击时自动全选内容"""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Markdown 悬停提示替换工具")
        self.resize(1100, 850)
        self.setAcceptDrops(True)

        self.current_path = None
        self.modified = False

        # 搜索会话状态
        self.search_term = None        # None 表示当前没有活动会话
        self.next_search_start = 0     # 下一次查找的起始偏移
        self._session_start = 0        # 本轮会话起始偏移（用于检测绕一圈）

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ---------- 拖入区域 ----------
        self.path_label = QLabel("将 .md 文件拖入窗口任意位置")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setMinimumHeight(48)
        self._reset_label_style()
        root.addWidget(self.path_label)

        # ---------- 三个输入框 ----------
        form = QHBoxLayout()
        self.display_edit = ClickSelectAllLineEdit()
        self.display_edit.setPlaceholderText("显示的文字（必填）")
        self.title_edit = ClickSelectAllLineEdit()
        self.title_edit.setPlaceholderText("提示标题（留空则自动复制显示文字）")
        self.content_edit = ClickSelectAllLineEdit()
        self.content_edit.setPlaceholderText("提示内容")

        form.addWidget(QLabel("显示的文字:"))
        form.addWidget(self.display_edit, 2)
        form.addWidget(QLabel("提示标题:"))
        form.addWidget(self.title_edit, 2)
        form.addWidget(QLabel("提示内容:"))
        form.addWidget(self.content_edit, 3)
        root.addLayout(form)

        # ---------- 按钮 ----------
        btns = QHBoxLayout()
        self.replace_btn = QPushButton("查找 / 替换")
        self.replace_btn.setToolTip("从光标位置开始查找，并询问是否替换 (Ctrl+Enter)")
        self.replace_btn.clicked.connect(self.do_replace)
        self.undo_btn = QPushButton("撤销")
        self.undo_btn.setToolTip("撤销编辑 (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.do_undo)
        self.save_btn = QPushButton("保存")
        self.save_btn.setToolTip("保存 (Ctrl+S)")
        self.save_btn.clicked.connect(self.do_save)
        self.save_as_btn = QPushButton("另存为")
        self.save_as_btn.setToolTip("另存为 (Ctrl+Shift+S)")
        self.save_as_btn.clicked.connect(self.do_save_as)
        self.reload_btn = QPushButton("重新加载")
        self.reload_btn.clicked.connect(self.do_reload)

        for b in (self.replace_btn, self.undo_btn, self.save_btn,
                  self.save_as_btn, self.reload_btn):
            btns.addWidget(b)
        btns.addStretch()

        self.replace_btn.setShortcut("Ctrl+Return")
        self.undo_btn.setShortcut("Ctrl+Z")
        self.save_btn.setShortcut("Ctrl+S")
        self.save_as_btn.setShortcut("Ctrl+Shift+S")

        root.addLayout(btns)

        # ---------- 大编辑器 ----------
        self.editor = QPlainTextEdit()
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.editor.setFont(font)
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.editor, 1)

        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.undoAvailable.connect(self.undo_btn.setEnabled)

        self.undo_btn.setEnabled(False)
        self.update_buttons()

    # ---------------- 拖放 ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.path_label.setStyleSheet(
                "QLabel { border: 2px dashed #4a9; border-radius: 8px; "
                "color: #1a7; background: #eef9f4; padding: 6px; }"
            )

    def dragLeaveEvent(self, event):
        self._reset_label_style()

    def dropEvent(self, event):
        self._reset_label_style()
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path:
            return
        if not path.lower().endswith((".md", ".markdown", ".txt")):
            QMessageBox.warning(self, "提示", "请拖入 .md / .markdown 文件")
            return
        if self.modified:
            ret = QMessageBox.question(
                self, "确认", "当前内容尚未保存，是否继续加载新文件？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return
        self.load_file(path)

    def _reset_label_style(self):
        self.path_label.setStyleSheet(
            "QLabel { border: 2px dashed #9aa; border-radius: 8px; "
            "color: #666; background: #fafafa; padding: 6px; }"
        )

    # ---------------- 文件读写 ----------------
    def load_file(self, path):
        content = None
        for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取文件：\n{e}")
                return
        if content is None:
            QMessageBox.critical(self, "错误", "无法解码文件内容。")
            return

        self.current_path = path
        self.path_label.setText(path)
        self.editor.setPlainText(content)
        self.modified = False
        self.search_term = None
        self.update_buttons()
        self.statusBar().showMessage(f"已加载：{path}", 3000)

    def do_reload(self):
        if self.current_path:
            if self.modified:
                ret = QMessageBox.question(
                    self, "确认", "重新加载将丢弃当前修改，继续？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if ret != QMessageBox.Yes:
                    return
            self.load_file(self.current_path)

    def do_save(self):
        if not self.current_path:
            return self.do_save_as()
        try:
            with open(self.current_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：\n{e}")
            return
        self.modified = False
        self.update_buttons()
        self.statusBar().showMessage(f"已保存：{self.current_path}", 3000)

    def do_save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", self.current_path or "",
            "Markdown 文件 (*.md *.markdown);;所有文件 (*)"
        )
        if not path:
            return
        self.current_path = path
        self.path_label.setText(path)
        self.do_save()

    # ---------------- 查找 / 替换 ----------------
    def do_replace(self):
        """点击主界面按钮：从文档开头查找并询问是否替换。"""
        display = self.display_edit.text()
        if not display:
            QMessageBox.warning(self, "提示", "请先填写“显示的文字”。")
            self.display_edit.setFocus()
            return

        if not self.title_edit.text():
            self.title_edit.setText(display)

        # 新会话：每次都从文档开头查找
        self.search_term = display
        self.next_search_start = 0
        self._session_start = 0

        self._find_and_prompt()

    def _find_and_prompt(self):
        """查找下一处匹配 → 定位选中 → 弹窗询问用户。"""
        display = self.search_term
        text = self.editor.toPlainText()

        idx = text.find(display, self.next_search_start)
        wrapped = False

        if idx < 0:
            # 尝试从头循环
            idx = text.find(display, 0)
            wrapped = True
            if idx < 0:
                QMessageBox.information(self, "未找到",
                                        f"文档中未找到“{display}”。")
                self.search_term = None
                return
            if idx >= self._session_start:
                QMessageBox.information(self, "已完成",
                                        f"已完成一轮搜索，未找到更多“{display}”。")
                self.search_term = None
                return

        # 在编辑器中选中并滚动到目标位置
        cursor = self.editor.textCursor()
        cursor.setPosition(idx)
        cursor.setPosition(idx + len(display), QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.editor.setFocus()

        line_no = text[:idx].count("\n") + 1

        # 询问用户
        box = QMessageBox(self)
        box.setWindowTitle("找到匹配")
        extra = "（已从头开始搜索）" if wrapped else ""
        box.setText(f"第 {line_no} 行找到“{display}”{extra}\n\n是否执行替换？")
        box.setInformativeText("选择“查找下一个”可继续定位后续匹配。")
        btn_replace = box.addButton("替换", QMessageBox.AcceptRole)
        btn_next = box.addButton("查找下一个", QMessageBox.ActionRole)
        btn_cancel = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(btn_replace)
        box.exec_()

        clicked = box.clickedButton()
        if clicked == btn_replace:
            self._perform_replace(idx, display)
        elif clicked == btn_next:
            self.next_search_start = idx + len(display)
            self._find_and_prompt()
        else:
            # 取消 / 关闭对话框：光标折叠到选区末尾，方便下次从那里继续
            cur = self.editor.textCursor()
            if cur.hasSelection():
                cur.setPosition(cur.selectionEnd())
                self.editor.setTextCursor(cur)
            self.search_term = None

    def _perform_replace(self, idx, display):
        title = self.title_edit.text() or display
        content = self.content_edit.text()

        replacement = (
            f'<span class="hover-hint">{display}'
            f'<span class="hover-hint__tooltip">'
            f'<span class="hint-title">{title}</span>{content}'
            f'</span></span>'
        )

        cursor = self.editor.textCursor()
        cursor.setPosition(idx)
        cursor.setPosition(idx + len(display), QTextCursor.KeepAnchor)
        cursor.insertText(replacement)
        self.editor.setTextCursor(cursor)          # 光标落在替换内容末尾
        self.editor.ensureCursorVisible()

        self.search_term = None                    # 结束会话
        line_no = self.editor.toPlainText()[:cursor.position()].count("\n") + 1
        self.statusBar().showMessage(f"已替换（第 {line_no} 行）", 4000)

    def do_undo(self):
        if self.editor.document().isUndoAvailable():
            self.editor.undo()
            self.statusBar().showMessage("已撤销", 2000)

    # ---------------- 状态更新 ----------------
    def on_text_changed(self):
        self.modified = True
        self.update_buttons()

    def update_buttons(self):
        self.save_btn.setEnabled(self.current_path is not None and self.modified)
        self.undo_btn.setEnabled(self.editor.document().isUndoAvailable())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()