# -*- coding: utf-8 -*-
"""
友链 & 特别鸣谢编辑器
------------------------------------------------
· 支持把 JSON 文件直接拖进窗口
· 可视化编辑 friends / thanks 两个数组
· 标签、颜色、头像等字段都有专门的小控件
· 每个字段下方都有编写提示
"""

import os
import re
import sys
import json
import datetime

from PyQt5.QtCore import Qt, QSize, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QToolButton, QListWidget, QSplitter,
    QTabWidget, QStackedWidget, QScrollArea, QFrame, QFileDialog, QMessageBox,
    QColorDialog, QLayout, QDialog, QTextEdit, QSizePolicy,
)

# ============================================================
#  字段定义（type: text / tags / color）
# ============================================================
FRIEND_FIELDS = [
    dict(key="name", label="名称", type="text", placeholder="秋刀鱼的小站",
         hint="站点名称，会显示在友链卡片的标题上"),
    dict(key="url", label="链接", type="text", placeholder="https://example.com",
         hint="完整网址，必须以 http:// 或 https:// 开头"),
    dict(key="desc", label="描述", type="text", placeholder="记录技术、折腾与生活的碎片",
         hint="一句话介绍，建议 10~30 个字，太长会被截断"),
    dict(key="tags", label="标签", type="tags",
         hint="回车或点「添加」加入；点标签上的 × 移除。建议 1~3 个"),
    dict(key="avatar", label="头像", type="text", placeholder="https://example.com/avatar.png",
         hint="头像图片直链；留空则用下面的「首字母 + 渐变色」生成占位头像"),
    dict(key="initial", label="首字母", type="text", placeholder="秋",
         hint="头像占位字符，通常取站点名首字，1 个汉字或字母"),
    dict(key="c1", label="渐变色 1", type="color",
         hint="占位头像渐变的起始颜色，点击色块选择"),
    dict(key="c2", label="渐变色 2", type="color",
         hint="占位头像渐变的结束颜色，建议和色 1 同色系"),
]

THANKS_FIELDS = [
    dict(key="name", label="名称", type="text", placeholder="张三",
         hint="要感谢的人/组织的名字"),
    dict(key="desc", label="鸣谢说明", type="text", placeholder="帮我排查了一个困扰三天的 bug",
         hint="说明感谢的原因，一句话即可"),
    dict(key="tags", label="标签", type="tags",
         hint="回车或点「添加」加入；点标签上的 × 移除"),
    dict(key="avatar", label="头像", type="text", placeholder="https://example.com/avatar.png",
         hint="头像图片直链，可留空"),
    dict(key="url", label="链接", type="text", placeholder="https://example.com",
         hint="对方主页，可留空"),
    dict(key="initial", label="首字母", type="text", placeholder="张",
         hint="头像占位字符，可留空"),
]

FRIEND_DEFAULTS = {
    "name": "", "url": "", "desc": "", "tags": [],
    "avatar": "", "initial": "", "c1": "#8AB4F8", "c2": "#5E8BFF",
}

THANKS_DEFAULTS = {
    "name": "", "desc": "", "tags": [],
    "avatar": "", "url": "", "initial": "",
}

# ============================================================
#  样式表
# ============================================================
STYLE = """
QWidget { font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
          font-size: 13px; color: #24292f; }
QWidget#root { background: #f6f8fa; }
QMainWindow { background: #f6f8fa; }

QPushButton { background: #ffffff; border: 1px solid #d0d7de; border-radius: 6px;
              padding: 6px 12px; }
QPushButton:hover { background: #f3f4f6; border-color: #b6bfc9; }
QPushButton:pressed { background: #ebecf0; }
QPushButton:disabled { color: #a0a6ad; background: #f6f8fa; }
QPushButton#primary { background: #1f6feb; border: 1px solid #1f6feb;
                      color: #ffffff; font-weight: 600; }
QPushButton#primary:hover { background: #1a63d4; }
QPushButton#danger { color: #cf222e; }
QPushButton#danger:hover { background: #ffebe9; border-color: #ffc1bc; }

QLineEdit { background: #ffffff; border: 1px solid #d0d7de; border-radius: 6px;
            padding: 6px 10px; selection-background-color: #b6d7ff; }
QLineEdit:focus { border: 1px solid #1f6feb; }

QListWidget { background: #ffffff; border: 1px solid #d0d7de; border-radius: 8px;
              padding: 4px; outline: none; }
QListWidget::item { padding: 9px 8px; border-radius: 6px; margin: 1px 2px; }
QListWidget::item:selected { background: #ddf4ff; color: #0a3069; }
QListWidget::item:hover { background: #f3f4f6; }

QTabWidget::pane { border: 1px solid #d0d7de; border-radius: 8px; background: #ffffff; }
QTabBar::tab { padding: 8px 20px; margin-right: 4px; border: 1px solid transparent;
               border-top-left-radius: 8px; border-top-right-radius: 8px; color: #57606a; }
QTabBar::tab:selected { background: #ffffff; border-color: #d0d7de; color: #1f6feb;
                        font-weight: 600; }
QTabBar::tab:hover:!selected { background: #eef1f4; }

QScrollArea { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c9d1d9; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #b1b9c1; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QStatusBar { color: #57606a; }
"""


# ============================================================
#  自动换行的流式布局（用于标签气泡）
# ============================================================
class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _do_layout(self, rect, test_only):
        x, y, line_h = rect.x(), rect.y(), 0
        space_x = space_y = self.spacing()
        for item in self._items:
            w = item.widget()
            if w is not None:
                space_x = self.spacing() + w.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
                space_y = self.spacing() + w.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_h > 0:
                x = rect.x()
                y = y + line_h + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_h = max(line_h, item.sizeHint().height())
        return y + line_h - rect.y()


# ============================================================
#  标签气泡
# ============================================================
class TagChip(QFrame):
    removed = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setObjectName("chip")
        self.setStyleSheet("#chip { background: #e8f0fe; border-radius: 11px; }")
        self.setFixedHeight(22)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(9, 0, 4, 0)
        lay.setSpacing(2)

        lbl = QLabel(text)
        lbl.setStyleSheet("color:#1f6feb; font-size:12px; background: transparent;")
        lay.addWidget(lbl)

        btn = QToolButton()
        btn.setText("×")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QToolButton { border:none; background: transparent; color:#1f6feb;"
            " font-weight:700; font-size:14px; padding:0 2px; }"
            "QToolButton:hover { color:#cf222e; }")
        btn.clicked.connect(lambda: self.removed.emit(self.text))
        lay.addWidget(btn)


class TagEditor(QWidget):
    """标签编辑控件：气泡展示 + 输入框回车添加"""
    changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = []

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        self.chip_host = QWidget()
        self.flow = FlowLayout(self.chip_host, spacing=6)
        self.chip_host.setVisible(False)
        v.addWidget(self.chip_host)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("输入标签后回车，可用逗号/空格分隔多个")
        self.input.returnPressed.connect(self._add_from_input)

        btn_add = QPushButton("＋ 添加")
        btn_add.setStyleSheet("padding: 5px 10px;")
        btn_add.clicked.connect(self._add_from_input)

        btn_clr = QPushButton("清空")
        btn_clr.setStyleSheet("padding: 5px 10px;")
        btn_clr.clicked.connect(self.clear_tags)

        row.addWidget(self.input, 1)
        row.addWidget(btn_add)
        row.addWidget(btn_clr)
        v.addLayout(row)

    # ---------- 对外接口 ----------
    def tags(self):
        return list(self._tags)

    def set_tags(self, tags, emit=False):
        new = [str(t).strip() for t in (tags or []) if str(t).strip()]
        if new == self._tags:
            return
        self._tags = new
        self._rebuild()
        if emit:
            self.changed.emit(list(self._tags))

    def clear_tags(self):
        if not self._tags:
            return
        self._tags = []
        self._rebuild()
        self.changed.emit(list(self._tags))

    # ---------- 内部 ----------
    def _add_from_input(self):
        raw = self.input.text().strip()
        if not raw:
            return
        parts = [p for p in re.split(r"[,，;；\s]+", raw) if p]
        added = False
        for p in parts:
            if p not in self._tags:
                self._tags.append(p)
                added = True
        self.input.clear()
        if added:
            self._rebuild()
            self.changed.emit(list(self._tags))

    def _remove_tag(self, text):
        if text in self._tags:
            self._tags.remove(text)
            self._rebuild()
            self.changed.emit(list(self._tags))

    def _rebuild(self):
        while self.flow.count():
            item = self.flow.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for t in self._tags:
            chip = TagChip(t)
            chip.removed.connect(self._remove_tag)
            self.flow.addWidget(chip)
        self.chip_host.setVisible(bool(self._tags))
        self.chip_host.updateGeometry()
        self.updateGeometry()


# ============================================================
#  颜色选择按钮
# ============================================================
class ColorButton(QPushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, color="#8AB4F8", parent=None):
        super().__init__(parent)
        self._color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(30)
        self.setToolTip("点击选择颜色")
        self.clicked.connect(self._pick)
        self._restyle()

    def color(self):
        return self._color

    def set_color(self, color, emit=True):
        text = (color or "#8ab4f8").strip()
        if not QColor(text).isValid():
            text = "#8ab4f8"
        self._color = text
        self._restyle()
        if emit:
            self.colorChanged.emit(self._color)

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, "选择颜色")
        if c.isValid():
            self.set_color(c.name())

    def _restyle(self):
        qc = QColor(self._color)
        lum = 0.299 * qc.red() + 0.587 * qc.green() + 0.114 * qc.blue()
        fg = "#1b1b1b" if lum > 150 else "#ffffff"
        self.setText(self._color.upper())
        self.setStyleSheet(
            f"QPushButton {{ background: {self._color}; color: {fg};"
            f" border: 1px solid rgba(0,0,0,0.18); border-radius: 6px;"
            f" padding: 4px 10px; font-weight: 600; letter-spacing: 0.5px; }}"
            f"QPushButton:hover {{ border: 1px solid #1f6feb; }}")


# ============================================================
#  一个区块的编辑器（友链 / 鸣谢 通用）
# ============================================================
class SectionEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, items, fields, defaults, title, parent=None):
        super().__init__(parent)
        self.items = items
        self.fields = fields
        self.defaults = defaults
        self.title = title
        self.current = -1
        self._loading = False
        self.widgets = {}
        self._build()
        self.refresh_list()

    # ---------------- 界面 ----------------
    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        # ---- 左：列表 + 按钮 ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        head = QLabel(f"{self.title}列表")
        head.setStyleSheet("font-weight:600; color:#57606a;")
        lv.addWidget(head)

        self.list = QListWidget()
        self.list.setMinimumWidth(190)
        self.list.currentRowChanged.connect(self._on_row_changed)
        lv.addWidget(self.list, 1)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.btn_add = QPushButton("＋ 添加")
        self.btn_add.setObjectName("primary")
        self.btn_del = QPushButton("－ 移除")
        self.btn_del.setObjectName("danger")
        row1.addWidget(self.btn_add)
        row1.addWidget(self.btn_del)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.btn_dup = QPushButton("⧉ 复制")
        self.btn_up = QPushButton("↑ 上移")
        self.btn_down = QPushButton("↓ 下移")
        row2.addWidget(self.btn_dup)
        row2.addWidget(self.btn_up)
        row2.addWidget(self.btn_down)

        lv.addLayout(row1)
        lv.addLayout(row2)

        self.btn_add.clicked.connect(self.add_item)
        self.btn_del.clicked.connect(self.remove_item)
        self.btn_dup.clicked.connect(self.duplicate_item)
        self.btn_up.clicked.connect(lambda: self.move_item(-1))
        self.btn_down.clicked.connect(lambda: self.move_item(1))

        splitter.addWidget(left)

        # ---- 右：表单 ----
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)

        # 空状态页
        empty_page = QWidget()
        ev = QVBoxLayout(empty_page)
        ev.addStretch(1)
        empty_lbl = QLabel("← 从左侧选择一个条目，或点击「＋ 添加」新建一个")
        empty_lbl.setAlignment(Qt.AlignCenter)
        empty_lbl.setStyleSheet("color:#8b949e; font-size:13px;")
        ev.addWidget(empty_lbl)
        ev.addStretch(1)

        # 表单页
        self.form_host = QWidget()
        fv = QVBoxLayout(self.form_host)
        fv.setContentsMargins(4, 4, 12, 4)
        fv.setSpacing(10)

        form_title = QLabel(f"{self.title}信息")
        form_title.setStyleSheet("font-weight:600; color:#57606a;")
        fv.addWidget(form_title)

        form_widget = QWidget()
        self.form = QFormLayout(form_widget)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(12)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        for f in self.fields:
            editor = self._make_editor(f)
            holder = QWidget()
            hv = QVBoxLayout(holder)
            hv.setContentsMargins(0, 0, 0, 0)
            hv.setSpacing(3)
            hv.addWidget(editor)

            hint = QLabel("💡 " + f["hint"])
            hint.setWordWrap(True)
            hint.setStyleSheet("color:#8b949e; font-size:11px;")
            hv.addWidget(hint)

            label = QLabel(f["label"] + "：")
            label.setStyleSheet("font-weight:600;")
            self.form.addRow(label, holder)
            self.widgets[f["key"]] = editor

        fv.addWidget(form_widget)
        fv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.form_host)

        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(empty_page)   # 0
        self.right_stack.addWidget(scroll)       # 1
        rv.addWidget(self.right_stack, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 700])

    def _make_editor(self, f):
        key = f["key"]
        t = f["type"]
        if t == "tags":
            w = TagEditor()
            w.changed.connect(lambda tags, k=key: self._set_value(k, tags))
        elif t == "color":
            w = ColorButton()
            w.colorChanged.connect(lambda c, k=key: self._set_value(k, c))
        else:
            w = QLineEdit()
            w.setPlaceholderText(f.get("placeholder", ""))
            w.setClearButtonEnabled(True)
            w.textEdited.connect(lambda text, k=key: self._set_value(k, text))
        return w

    # ---------------- 列表 ----------------
    @staticmethod
    def _row_text(item):
        name = (item.get("name") or "").strip()
        return name if name else "未命名"

    def refresh_list(self, select=None):
        target = self.current if select is None else select
        self.list.blockSignals(True)
        self.list.clear()
        for it in self.items:
            self.list.addItem(self._row_text(it))
        self.list.blockSignals(False)

        if not self.items:
            self.current = -1
            self._on_row_changed(-1)
            return

        target = max(0, min(target if target >= 0 else 0, len(self.items) - 1))
        self.list.setCurrentRow(target)
        self._on_row_changed(target)

    def set_items(self, items):
        self.items = items
        self.current = 0 if items else -1
        self.refresh_list()

    def _refresh_current_row(self):
        if 0 <= self.current < len(self.items) and self.list.item(self.current):
            self.list.blockSignals(True)
            self.list.item(self.current).setText(self._row_text(self.items[self.current]))
            self.list.blockSignals(False)

    def _on_row_changed(self, row):
        self.current = row
        has = 0 <= row < len(self.items)
        self._update_buttons(has)
        self.right_stack.setCurrentIndex(1 if has else 0)
        if has:
            self.load_form(row)

    def _update_buttons(self, has):
        for b in (self.btn_del, self.btn_dup, self.btn_up, self.btn_down):
            b.setEnabled(has)

    # ---------------- 表单读写 ----------------
    def _default_for(self, key):
        return self.defaults.get(key, "")

    def load_form(self, index):
        self._loading = True
        item = self.items[index]
        for f in self.fields:
            self._set_widget(f["key"], item.get(f["key"], self._default_for(f["key"])))
        self._loading = False

    def _set_widget(self, key, value):
        w = self.widgets.get(key)
        if w is None:
            return
        if isinstance(w, TagEditor):
            w.set_tags(value if isinstance(value, list) else [])
        elif isinstance(w, ColorButton):
            w.set_color(value if isinstance(value, str) and value
                        else self._default_for(key), emit=False)
        elif isinstance(w, QLineEdit):
            w.setText("" if value is None else str(value))

    def _set_value(self, key, value):
        if self._loading or not (0 <= self.current < len(self.items)):
            return
        self.items[self.current][key] = value
        if key == "name":
            self._refresh_current_row()
        self.changed.emit()

    # ---------------- 条目操作 ----------------
    def add_item(self):
        item = json.loads(json.dumps(self.defaults))
        self.items.append(item)
        self.current = len(self.items) - 1
        self.refresh_list(select=self.current)
        self.changed.emit()
        w = self.widgets.get("name")
        if w is not None:
            w.setFocus()

    def remove_item(self):
        if not (0 <= self.current < len(self.items)):
            return
        name = self._row_text(self.items[self.current])
        ret = QMessageBox.question(
            self, "移除确认", f"确定要移除「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        idx = self.current
        del self.items[idx]
        self.current = min(idx, len(self.items) - 1)
        self.refresh_list(select=self.current)
        self.changed.emit()

    def duplicate_item(self):
        if not (0 <= self.current < len(self.items)):
            return
        copy = json.loads(json.dumps(self.items[self.current]))
        copy["name"] = (copy.get("name") or "未命名") + "（副本）"
        self.items.insert(self.current + 1, copy)
        self.current += 1
        self.refresh_list(select=self.current)
        self.changed.emit()

    def move_item(self, delta):
        i = self.current
        j = i + delta
        if not (0 <= i < len(self.items)) or not (0 <= j < len(self.items)):
            return
        self.items[i], self.items[j] = self.items[j], self.items[i]
        self.current = j
        self.refresh_list(select=j)
        self.changed.emit()


# ============================================================
#  欢迎页（拖拽提示）
# ============================================================
class WelcomeWidget(QWidget):
    openRequested = pyqtSignal()
    sampleRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(12)

        icon = QLabel("📄")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:56px;")
        v.addWidget(icon)

        t1 = QLabel("把 JSON 文件拖到这里")
        t1.setAlignment(Qt.AlignCenter)
        t1.setStyleSheet("font-size:19px; font-weight:700;")
        v.addWidget(t1)

        t2 = QLabel("也可以点击下方按钮选择文件，或先载入一份示例数据体验一下")
        t2.setAlignment(Qt.AlignCenter)
        t2.setStyleSheet("color:#8b949e;")
        v.addWidget(t2)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        row.setSpacing(10)

        b1 = QPushButton("📂 选择 JSON 文件")
        b1.setObjectName("primary")
        b1.setMinimumHeight(34)
        b1.clicked.connect(self.openRequested.emit)

        b2 = QPushButton("载入示例数据")
        b2.setMinimumHeight(34)
        b2.clicked.connect(self.sampleRequested.emit)

        row.addWidget(b1)
        row.addWidget(b2)
        v.addLayout(row)

        tip = QLabel("文件结构需包含 friends（友链）与 thanks（鸣谢）两个数组")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color:#b0b7c3; font-size:12px; margin-top:12px;")
        v.addWidget(tip)


# ============================================================
#  主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("友链 & 特别鸣谢编辑器")
        self.resize(1180, 780)
        self.setAcceptDrops(True)

        self.data = {"updated": "", "friends": [], "thanks": []}
        self.extra = {}
        self.path = None

        self._build_ui()
        self._update_header()

    # ---------------- 界面 ----------------
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        # 顶栏
        bar = QHBoxLayout()
        bar.setSpacing(8)

        title = QLabel("🔗 友链 & 特别鸣谢编辑器")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        bar.addWidget(title)
        bar.addStretch(1)

        self.btn_open = QPushButton("📂 打开")
        self.btn_save = QPushButton("💾 保存")
        self.btn_saveas = QPushButton("另存为…")
        self.btn_new = QPushButton("🗋 新建")
        self.btn_preview = QPushButton("{ } 预览 JSON")
        self.btn_help = QPushButton("? 格式示例")

        self.btn_open.clicked.connect(self.open_dialog)
        self.btn_save.clicked.connect(lambda: self.save_file())
        self.btn_saveas.clicked.connect(self.save_file_as)
        self.btn_new.clicked.connect(self.new_document)
        self.btn_preview.clicked.connect(self.preview_json)
        self.btn_help.clicked.connect(self.show_format_help)

        for b in (self.btn_open, self.btn_save, self.btn_saveas,
                  self.btn_new, self.btn_preview, self.btn_help):
            bar.addWidget(b)

        v.addLayout(bar)

        # 元信息行
        meta = QHBoxLayout()
        meta.setSpacing(8)

        meta.addWidget(QLabel("最后更新："))
        self.updated_edit = QLineEdit()
        self.updated_edit.setPlaceholderText("2026-10-22")
        self.updated_edit.setFixedWidth(150)
        self.updated_edit.textEdited.connect(self._on_updated_edit)
        meta.addWidget(self.updated_edit)

        b_today = QPushButton("今天")
        b_today.clicked.connect(self._set_today)
        meta.addWidget(b_today)

        meta.addStretch(1)
        self.path_label = QLabel("未载入文件")
        self.path_label.setStyleSheet("color:#8b949e;")
        meta.addWidget(self.path_label)

        v.addLayout(meta)

        # 主体
        self.stack = QStackedWidget()

        self.welcome = WelcomeWidget()
        self.welcome.openRequested.connect(self.open_dialog)
        self.welcome.sampleRequested.connect(self.load_sample)
        self.stack.addWidget(self.welcome)

        self.tabs = QTabWidget()
        self.friends_editor = SectionEditor(
            self.data["friends"], FRIEND_FIELDS, FRIEND_DEFAULTS, "友链")
        self.thanks_editor = SectionEditor(
            self.data["thanks"], THANKS_FIELDS, THANKS_DEFAULTS, "特别鸣谢")
        self.tabs.addTab(self.friends_editor, "🔗 友链")
        self.tabs.addTab(self.thanks_editor, "🙏 特别鸣谢")
        self.stack.addWidget(self.tabs)

        v.addWidget(self.stack, 1)

        self.statusBar().showMessage("就绪 · 可以把 JSON 文件拖进窗口")

    # ---------------- 拖拽 ----------------
    @staticmethod
    def _json_path_from_mime(mime):
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            p = url.toLocalFile()
            if p and p.lower().endswith(".json"):
                return p
        return None

    def dragEnterEvent(self, event):
        if self._json_path_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._json_path_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        path = self._json_path_from_mime(event.mimeData())
        if path:
            event.acceptProposedAction()
            self.load_file(path)
        else:
            event.ignore()

    # ---------------- 数据加载 ----------------
    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 JSON", "", "JSON 文件 (*.json);;所有文件 (*)")
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                raw = json.load(fp)
        except Exception as exc:
            QMessageBox.critical(self, "无法读取",
                                 f"读取或解析 JSON 失败：\n{exc}")
            return
        if self._apply_data(raw, path):
            self.statusBar().showMessage(f"已载入：{path}", 6000)

    def _apply_data(self, raw, path=None):
        if not isinstance(raw, dict):
            QMessageBox.warning(self, "格式错误",
                                "顶层应该是一个 JSON 对象（以 { 开头）。")
            return False

        friends = raw.get("friends") or []
        thanks = raw.get("thanks") or []
        if not isinstance(friends, list) or not isinstance(thanks, list):
            QMessageBox.warning(self, "格式错误",
                                "friends / thanks 应该是数组（[ ... ]）。")
            return False

        self.data["updated"] = str(raw.get("updated") or "")
        self.data["friends"][:] = [x for x in friends if isinstance(x, dict)]
        self.data["thanks"][:] = [x for x in thanks if isinstance(x, dict)]
        self.extra = {k: val for k, val in raw.items()
                      if k not in ("updated", "friends", "thanks")}

        self.path = path
        self.updated_edit.setText(self.data["updated"])
        self.friends_editor.set_items(self.data["friends"])
        self.thanks_editor.set_items(self.data["thanks"])
        self.stack.setCurrentWidget(self.tabs)
        self._update_header()
        return True

    def load_sample(self):
        sample = {
            "updated": datetime.date.today().isoformat(),
            "friends": [
                {
                    "name": "秋刀鱼的小站",
                    "url": "https://example.com",
                    "desc": "记录技术、折腾与生活的碎片",
                    "tags": ["技术", "生活"],
                    "avatar": "https://example.com/avatar-1.png",
                    "initial": "秋",
                    "c1": "#8AB4F8",
                    "c2": "#5E8BFF",
                },
                {
                    "name": "星屑实验室",
                    "url": "https://example.com",
                    "desc": "一个喜欢折腾开源项目的高中生",
                    "tags": ["开源", "前端"],
                    "avatar": "",
                    "initial": "星",
                    "c1": "#7FC4EA",
                    "c2": "#21a5e3",
                },
            ],
            "thanks": [
                {
                    "name": "张三",
                    "desc": "帮我排查了一个困扰三天的 bug",
                    "avatar": "",
                    "url": "https://example.com",
                    "tags": ["debug 救星"],
                    "initial": "张",
                },
                {
                    "name": "李四",
                    "desc": "给了很多设计上的建议",
                    "tags": ["设计", "建议"],
                },
            ],
        }
        if self._apply_data(sample, None):
            self.path = None
            self._update_header()
            self.statusBar().showMessage("已载入示例数据（尚未保存到文件）", 5000)

    def new_document(self):
        if self.data["friends"] or self.data["thanks"]:
            ret = QMessageBox.question(
                self, "新建", "确定要清空当前内容并新建吗？（未保存的修改会丢失）",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.path = None
        self.extra = {}
        self.data["updated"] = ""
        self.data["friends"].clear()
        self.data["thanks"].clear()
        self.updated_edit.setText("")
        self.friends_editor.set_items(self.data["friends"])
        self.thanks_editor.set_items(self.data["thanks"])
        self.stack.setCurrentWidget(self.tabs)
        self._update_header()

    # ---------------- 保存 ----------------
    def _build_output(self):
        out = {}
        out["updated"] = (self.updated_edit.text().strip()
                          or datetime.date.today().isoformat())
        out["friends"] = self.data["friends"]
        out["thanks"] = self.data["thanks"]
        for k, val in self.extra.items():
            out.setdefault(k, val)
        return out

    def save_file(self, path=None):
        if path is None:
            path = self.path
        if not path:
            return self.save_file_as()

        out = self._build_output()
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(out, fp, ensure_ascii=False, indent=2)
                fp.write("\n")
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return False

        self.path = path
        self.data["updated"] = out["updated"]
        self._update_header()
        self.statusBar().showMessage(f"已保存：{path}", 5000)
        return True

    def save_file_as(self):
        default = os.path.basename(self.path) if self.path else "friends.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", default, "JSON 文件 (*.json);;所有文件 (*)")
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".json"
        return self.save_file(path)

    # ---------------- 其他操作 ----------------
    def _on_updated_edit(self, text):
        self.data["updated"] = text

    def _set_today(self):
        today = datetime.date.today().isoformat()
        self.updated_edit.setText(today)
        self.data["updated"] = today

    def _update_header(self):
        if self.path:
            name = os.path.basename(self.path)
            self.path_label.setText(f"📄 {name}")
            self.setWindowTitle(f"{name} — 友链 & 特别鸣谢编辑器")
        else:
            self.path_label.setText("未载入文件")
            self.setWindowTitle("友链 & 特别鸣谢编辑器")

    def preview_json(self):
        text = json.dumps(self._build_output(), ensure_ascii=False, indent=2)

        dlg = QDialog(self)
        dlg.setWindowTitle("JSON 预览")
        dlg.resize(640, 640)
        v = QVBoxLayout(dlg)

        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text)
        te.setStyleSheet(
            "font-family: Consolas, Menlo, monospace; font-size:12px;"
            " background:#ffffff; border:1px solid #d0d7de; border-radius:6px;")
        v.addWidget(te, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        b_copy = QPushButton("复制到剪贴板")
        b_copy.clicked.connect(
            lambda: (QApplication.clipboard().setText(text),
                     self.statusBar().showMessage("已复制到剪贴板", 3000)))
        b_close = QPushButton("关闭")
        b_close.clicked.connect(dlg.accept)
        row.addWidget(b_copy)
        row.addWidget(b_close)
        v.addLayout(row)

        dlg.exec_()

    def show_format_help(self):
        example = json.dumps(self._build_output() if (
            self.data["friends"] or self.data["thanks"]) else {
                "updated": "2026-10-22",
                "friends": [{
                    "name": "秋刀鱼的小站",
                    "url": "https://example.com",
                    "desc": "记录技术、折腾与生活的碎片",
                    "tags": ["技术", "生活"],
                    "avatar": "https://example.com/avatar-1.png",
                    "initial": "秋",
                    "c1": "#8AB4F8",
                    "c2": "#5E8BFF",
                }],
                "thanks": [{
                    "name": "张三",
                    "desc": "帮我排查了一个困扰三天的 bug",
                    "avatar": "https://example.com/avatar.png",
                    "url": "https://example.com",
                    "tags": ["debug 救星"],
                    "initial": "张",
                }],
            }, ensure_ascii=False, indent=2)

        html = f"""
        <h3>文件结构</h3>
        <p>顶层是一个对象，包含三个字段：</p>
        <ul>
          <li><b>updated</b>：最后更新日期，字符串，如 <code>2026-10-22</code></li>
          <li><b>friends</b>：友链数组</li>
          <li><b>thanks</b>：特别鸣谢数组</li>
        </ul>
        <h3>友链字段</h3>
        <ul>
          <li><b>name</b> 站点名称</li>
          <li><b>url</b> 完整网址（http/https）</li>
          <li><b>desc</b> 一句话描述</li>
          <li><b>tags</b> 标签数组，如 <code>["技术","生活"]</code></li>
          <li><b>avatar</b> 头像直链，可留空</li>
          <li><b>initial</b> 头像占位字符</li>
          <li><b>c1 / c2</b> 占位头像的渐变起止色（#RRGGBB）</li>
        </ul>
        <h3>鸣谢字段</h3>
        <p>name、desc、tags、avatar、url、initial，均可选填。</p>
        <h3>示例</h3>
        <pre style="font-family:Consolas,Menlo,monospace;font-size:12px;
                    background:#f6f8fa;padding:10px;border-radius:6px;">{example}</pre>
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("格式示例 & 编写提示")
        dlg.resize(720, 640)
        v = QVBoxLayout(dlg)

        te = QTextEdit()
        te.setReadOnly(True)
        te.setHtml(html)
        v.addWidget(te, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        b = QPushButton("关闭")
        b.clicked.connect(dlg.accept)
        row.addWidget(b)
        v.addLayout(row)

        dlg.exec_()

    # ---------------- 关闭确认 ----------------
    def closeEvent(self, event):
        event.accept()


# ============================================================
def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()