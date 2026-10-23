# -*- coding: utf-8 -*-
"""
友链 JSON 编辑器 (PyQt5)
- 左侧：好友列表（支持新增 / 删除 / 上移 / 下移）
- 中间：字段编辑（名称、链接、描述、标签、头像、首字母、渐变色）
- 右侧：卡片实时预览
- 顶部：数据更新日期、打开 / 保存 / 另存为 / 构建 HTML（调用同目录 build.py）
"""

import sys
import os
import json
import copy
import re

from PyQt5.QtCore import (
    Qt, QSize, QDate, QRect, QProcess, pyqtSignal
)
from PyQt5.QtGui import QColor, QPainter, QLinearGradient, QBrush, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QSplitter,
    QScrollArea, QFrame, QColorDialog, QDateEdit, QMessageBox, QFileDialog,
    QSizePolicy, QAbstractItemView, QStyledItemDelegate, QStyle, QPlainTextEdit
)


# ---------------------------------------------------------------- 工具组件 ---

class AvatarWidget(QWidget):
    """渐变色圆形头像 + 首字母"""

    def __init__(self, initial="?", c1="#8AB4F8", c2="#5E8BFF", size=44, parent=None):
        super().__init__(parent)
        self._initial = initial or "?"
        self._c1 = c1 if QColor(c1).isValid() else "#8AB4F8"
        self._c2 = c2 if QColor(c2).isValid() else "#5E8BFF"
        self.setFixedSize(size, size)

    def set_data(self, initial, c1, c2):
        self._initial = initial or "?"
        self._c1 = c1 if QColor(c1).isValid() else "#8AB4F8"
        self._c2 = c2 if QColor(c2).isValid() else "#5E8BFF"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, QColor(self._c1))
        grad.setColorAt(1.0, QColor(self._c2))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(r)

        p.setPen(QColor("#FFFFFF"))
        f = QFont(self.font())
        f.setPointSizeF(max(8.0, self.width() * 0.36))
        f.setBold(True)
        p.setFont(f)
        p.drawText(r, Qt.AlignCenter, self._initial[:1])


class ColorButton(QPushButton):
    """点击弹出调色板的颜色块"""

    colorChanged = pyqtSignal(str)

    def __init__(self, color="#8AB4F8", parent=None):
        super().__init__(parent)
        self._color = color if QColor(color).isValid() else "#8AB4F8"
        self.setFixedSize(72, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick)
        self._apply()

    def color(self):
        return self._color

    def setColor(self, c):
        if QColor(c).isValid():
            self._color = c
            self._apply()

    def _apply(self):
        self.setStyleSheet(
            "QPushButton{background:%s;border:1px solid #D0D4DA;border-radius:7px;}"
            "QPushButton:hover{border:1px solid #5E8BFF;}" % self._color
        )

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, "选择颜色")
        if c.isValid():
            self._color = c.name()
            self._apply()
            self.colorChanged.emit(self._color)


class FriendDelegate(QStyledItemDelegate):
    """好友列表的自绘代理"""

    def sizeHint(self, option, index):
        return QSize(0, 62)

    def paint(self, painter, option, index):
        data = index.data(Qt.UserRole) or {}
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect.adjusted(4, 3, -4, -3)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#E8F0FE"))
            painter.drawRoundedRect(rect, 8, 8)
        elif hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#F5F6F8"))
            painter.drawRoundedRect(rect, 8, 8)

        # 头像
        av = QRect(rect.left() + 8, rect.center().y() - 19, 38, 38)
        c1 = data.get("c1") if QColor(data.get("c1", "")).isValid() else "#8AB4F8"
        c2 = data.get("c2") if QColor(data.get("c2", "")).isValid() else "#5E8BFF"
        grad = QLinearGradient(av.topLeft(), av.bottomRight())
        grad.setColorAt(0.0, QColor(c1))
        grad.setColorAt(1.0, QColor(c2))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(av)

        painter.setPen(QColor("#FFFFFF"))
        f = QFont(option.font)
        f.setPointSize(12)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(av, Qt.AlignCenter, (data.get("initial") or "?")[:1])

        # 文字
        tx = av.right() + 12
        tw = max(10, rect.right() - tx - 8)

        painter.setPen(QColor("#1F2328"))
        f2 = QFont(option.font)
        f2.setPointSize(10)
        f2.setBold(True)
        painter.setFont(f2)
        painter.drawText(
            QRect(tx, rect.top() + 9, tw, 18),
            Qt.AlignLeft | Qt.AlignVCenter,
            QFontMetrics(f2).elidedText(data.get("name", ""), Qt.ElideRight, tw),
        )

        painter.setPen(QColor("#8A8F98"))
        f3 = QFont(option.font)
        f3.setPointSize(9)
        painter.setFont(f3)
        painter.drawText(
            QRect(tx, rect.top() + 29, tw, 16),
            Qt.AlignLeft | Qt.AlignVCenter,
            QFontMetrics(f3).elidedText(data.get("desc", ""), Qt.ElideRight, tw),
        )
        painter.restore()


class PreviewCard(QFrame):
    """右侧卡片实时预览"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewCard")
        self.setMinimumHeight(230)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)

        self.avatar = AvatarWidget("?", "#8AB4F8", "#5E8BFF", 64)
        lay.addWidget(self.avatar, 0, Qt.AlignLeft)

        self.lbl_name = QLabel("—")
        self.lbl_name.setStyleSheet("font-size:17px; font-weight:600; color:#1F2328;")
        lay.addWidget(self.lbl_name)

        self.lbl_url = QLabel("")
        self.lbl_url.setStyleSheet("color:#5E8BFF; font-size:11px;")
        lay.addWidget(self.lbl_url)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color:#5A6270; font-size:12px;")
        lay.addWidget(self.lbl_desc)

        self.tags_box = QWidget()
        self.tags_lay = QHBoxLayout(self.tags_box)
        self.tags_lay.setContentsMargins(0, 0, 0, 0)
        self.tags_lay.setSpacing(6)
        lay.addWidget(self.tags_box)

        lay.addStretch()

    def _clear_tags(self):
        while self.tags_lay.count():
            item = self.tags_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_data(self, d):
        self._clear_tags()
        if not d:
            self.avatar.set_data("?", "#C9CDD4", "#AEB4BD")
            self.lbl_name.setText("—")
            self.lbl_url.setText("")
            self.lbl_desc.setText("请选择左侧的好友")
            return

        self.avatar.set_data(d.get("initial", "?"), d.get("c1", "#8AB4F8"), d.get("c2", "#5E8BFF"))
        self.lbl_name.setText(d.get("name", "未命名"))
        self.lbl_url.setText(d.get("url", ""))
        self.lbl_desc.setText(d.get("desc", ""))

        for t in (d.get("tags") or [])[:8]:
            chip = QLabel(str(t))
            chip.setStyleSheet(
                "background:#EEF2FF; color:#4454F8; border-radius:9px;"
                "padding:2px 9px; font-size:11px;"
            )
            self.tags_lay.addWidget(chip)
        self.tags_lay.addStretch()


# ---------------------------------------------------------------- 主窗口 ----

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("友链 JSON 编辑器")
        self.resize(1200, 740)

        self.data = {"updated": QDate.currentDate().toString("yyyy-MM-dd"), "friends": []}
        self.current = -1
        self.current_path = None
        self._loading = False

        # 构建进程状态
        self._build_proc = None
        self._build_output = []

        self._build_ui()
        self._apply_style()

        self.load_data(self._sample_data(), path=None)

    # ------------------------------------------------------------ UI 构建 --
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 6)
        root.setSpacing(10)

        # ---- 顶栏 ----
        bar = QHBoxLayout()
        bar.setSpacing(8)

        title = QLabel("友链 JSON 编辑器")
        title.setStyleSheet("font-size:16px; font-weight:600; color:#1F2328;")
        bar.addWidget(title)
        bar.addSpacing(24)

        bar.addWidget(QLabel("数据更新日期"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(130)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        bar.addWidget(self.date_edit)

        bar.addStretch()

        self.btn_open = QPushButton("打开 JSON")
        self.btn_save = QPushButton("保存")
        self.btn_save.setObjectName("primary")
        self.btn_save_as = QPushButton("另存为")
        self.btn_build = QPushButton("构建 HTML")
        self.btn_build.setObjectName("buildBtn")
        self.btn_build.setToolTip("执行同目录下的 build.py（自动使用当前 Python 解释器）")

        self.btn_open.clicked.connect(self.open_file)
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save_as.clicked.connect(self.save_file_as)
        self.btn_build.clicked.connect(self.build_html)

        bar.addWidget(self.btn_open)
        bar.addWidget(self.btn_save_as)
        bar.addWidget(self.btn_save)
        bar.addWidget(self.btn_build)
        root.addLayout(bar)

        # ---- 三栏 ----
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_middle())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([290, 500, 340])
        root.addWidget(splitter, 1)

        self.statusBar().showMessage("就绪")

    def _build_left(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel("好友列表")
        lbl.setStyleSheet("font-weight:600; color:#5A6270;")
        lay.addWidget(lbl)

        self.list = QListWidget()
        self.list.setItemDelegate(FriendDelegate(self.list))
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setMouseTracking(True)
        self.list.viewport().setAttribute(Qt.WA_Hover, True)
        self.list.currentRowChanged.connect(self._on_current_changed)
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.btn_add = QPushButton("新增")
        self.btn_del = QPushButton("删除")
        self.btn_up = QPushButton("上移")
        self.btn_down = QPushButton("下移")
        for b in (self.btn_add, self.btn_del, self.btn_up, self.btn_down):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(b)

        self.btn_add.clicked.connect(self.add_friend)
        self.btn_del.clicked.connect(self.remove_friend)
        self.btn_up.clicked.connect(lambda: self.move_friend(-1))
        self.btn_down.clicked.connect(lambda: self.move_friend(1))
        lay.addLayout(row)
        return panel

    def _build_middle(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel("详细信息")
        lbl.setStyleSheet("font-weight:600; color:#5A6270;")
        lay.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        inner.setObjectName("formPanel")
        form = QFormLayout(inner)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(13)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("站点名称，如：秋刀鱼的小站")
        form.addRow("名称", self.ed_name)

        self.ed_url = QLineEdit()
        self.ed_url.setPlaceholderText("https://example.com")
        form.addRow("链接", self.ed_url)

        self.ed_desc = QLineEdit()
        self.ed_desc.setPlaceholderText("一句话介绍")
        form.addRow("描述", self.ed_desc)

        self.ed_tags = QLineEdit()
        self.ed_tags.setPlaceholderText("用逗号分隔，如：技术, 生活")
        form.addRow("标签", self.ed_tags)

        self.ed_avatar = QLineEdit()
        self.ed_avatar.setPlaceholderText("https://example.com/avatar.png")
        form.addRow("头像 URL", self.ed_avatar)

        self.ed_initial = QLineEdit()
        self.ed_initial.setMaxLength(2)
        self.ed_initial.setPlaceholderText("头像上显示的字，留空自动取名称首字")
        form.addRow("首字母", self.ed_initial)

        color_box = QWidget()
        ch = QHBoxLayout(color_box)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(8)
        self.btn_c1 = ColorButton("#8AB4F8")
        self.btn_c2 = ColorButton("#5E8BFF")
        ch.addWidget(QLabel("起始"))
        ch.addWidget(self.btn_c1)
        ch.addWidget(QLabel("→"))
        ch.addWidget(self.btn_c2)
        ch.addStretch()
        form.addRow("头像渐变", color_box)

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        # 信号
        for w in (self.ed_name, self.ed_url, self.ed_desc,
                  self.ed_tags, self.ed_avatar, self.ed_initial):
            w.textChanged.connect(self._on_field_changed)
        self.btn_c1.colorChanged.connect(self._on_field_changed)
        self.btn_c2.colorChanged.connect(self._on_field_changed)

        self._form_widgets = [
            self.ed_name, self.ed_url, self.ed_desc, self.ed_tags,
            self.ed_avatar, self.ed_initial, self.btn_c1, self.btn_c2,
        ]
        return panel

    def _build_right(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel("卡片预览")
        lbl.setStyleSheet("font-weight:600; color:#5A6270;")
        lay.addWidget(lbl)

        self.preview = PreviewCard()
        lay.addWidget(self.preview)
        lay.addStretch()
        return panel

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget#central { background: #F5F6F8; }
            QLabel { color: #3A3F46; }
            QWidget#formPanel { background: #FFFFFF; }
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #DDE1E6;
                border-radius: 6px;
                padding: 7px 10px;
                color: #1F2328;
                selection-background-color: #5E8BFF;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #5E8BFF; }
            QLineEdit:disabled { background: #F2F3F5; color: #A8ADB5; }
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #E3E6EA;
                border-radius: 10px;
                outline: none;
            }
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #DDE1E6;
                border-radius: 6px;
                padding: 7px 14px;
                color: #3A3F46;
            }
            QPushButton:hover { background: #F0F4FF; border-color: #5E8BFF; }
            QPushButton:pressed { background: #E1E9FF; }
            QPushButton:disabled { background: #F2F3F5; color: #B4B9C0; border-color: #E6E8EB; }
            QPushButton#primary {
                background: #5E8BFF; color: #FFFFFF; border: 1px solid #5E8BFF;
                font-weight: 600;
            }
            QPushButton#primary:hover { background: #4A79F0; border-color: #4A79F0; }
            QPushButton#primary:pressed { background: #3D69DE; }
            QPushButton#buildBtn {
                background: #34C79F; color: #FFFFFF; border: 1px solid #34C79F;
                font-weight: 600;
            }
            QPushButton#buildBtn:hover { background: #2BB58F; border-color: #2BB58F; }
            QPushButton#buildBtn:pressed { background: #239C7B; }
            QPushButton#buildBtn:disabled { background: #B7E6D7; border-color: #B7E6D7; color:#FFFFFF; }
            QDateEdit {
                background: #FFFFFF;
                border: 1px solid #DDE1E6;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QDateEdit:focus { border: 1px solid #5E8BFF; }
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 10px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #D3D7DD; border-radius: 5px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #B7BCC4; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QFrame#previewCard {
                background: #FFFFFF;
                border: 1px solid #E3E6EA;
                border-radius: 12px;
            }
            QStatusBar { background: transparent; color: #7A808A; }
        """)

    # ------------------------------------------------------------ 数据流 ----
    def _sample_data(self):
        return {
            "updated": "2026-10-22",
            "friends": [
                {"name": "秋刀鱼的小站", "url": "https://example.com",
                 "desc": "记录技术、折腾与生活的碎片", "tags": ["技术", "生活"],
                 "avatar": "https://example.com/avatar-1.png", "initial": "秋",
                 "c1": "#8AB4F8", "c2": "#5E8BFF"},
                {"name": "星屑实验室", "url": "https://example.com",
                 "desc": "一个喜欢折腾开源项目的高中生", "tags": ["开源", "前端"],
                 "avatar": "https://example.com/avatar-2.png", "initial": "星",
                 "c1": "#7FC4EA", "c2": "#21a5e3"},
                {"name": "猫窝", "url": "https://example.com",
                 "desc": "一只猫的胡言乱语与深夜碎碎念", "tags": ["随笔", "日常"],
                 "avatar": "https://example.com/avatar-3.png", "initial": "猫",
                 "c1": "#BEC0EC", "c2": "#4454F8"},
                {"name": "云上小筑", "url": "https://example.com",
                 "desc": "云原生、运维，以及摸鱼的一百种姿势", "tags": ["运维", "Linux"],
                 "avatar": "https://example.com/avatar-4.png", "initial": "云",
                 "c1": "#7BE0B8", "c2": "#34C79F"},
                {"name": "拾光笔记", "url": "https://example.com",
                 "desc": "把时间存进文字里，偶尔拍点照片", "tags": ["随笔", "摄影"],
                 "avatar": "https://example.com/avatar-5.png", "initial": "拾",
                 "c1": "#E39BEA", "c2": "#A97CE6"},
                {"name": "木子の博客", "url": "https://example.com",
                 "desc": "前端、设计，以及一点点二次元", "tags": ["前端", "设计"],
                 "avatar": "https://example.com/avatar-6.png", "initial": "木",
                 "c1": "#FFD84D", "c2": "#FB7B44"},
                {"name": "深夜代码", "url": "https://example.com",
                 "desc": "夜深了，代码还没写完", "tags": ["后端", "Python"],
                 "avatar": "https://example.com/avatar-7.png", "initial": "夜",
                 "c1": "#9BA4B5", "c2": "#6C7A9F"},
                {"name": "灯塔观测站", "url": "https://example.com",
                 "desc": "关于网络安全与网络本身的一些观察", "tags": ["安全", "网络"],
                 "avatar": "https://example.com/avatar-8.png", "initial": "灯",
                 "c1": "#F4756A", "c2": "#EA3462"},
            ],
        }

    def _normalize(self, d):
        out = dict(d)  # 保留未知字段
        name = str(d.get("name", "未命名") or "未命名")
        c1 = d.get("c1") if QColor(str(d.get("c1", ""))).isValid() else "#8AB4F8"
        c2 = d.get("c2") if QColor(str(d.get("c2", ""))).isValid() else "#5E8BFF"
        tags = d.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        out.update({
            "name": name,
            "url": str(d.get("url", "")),
            "desc": str(d.get("desc", "")),
            "tags": [str(t) for t in tags],
            "avatar": str(d.get("avatar", "")),
            "initial": str(d.get("initial", "") or name[:1]),
            "c1": c1,
            "c2": c2,
        })
        return out

    def load_data(self, data, path=None):
        if not isinstance(data, dict):
            data = {"updated": QDate.currentDate().toString("yyyy-MM-dd"), "friends": []}
        friends = data.get("friends", [])
        if not isinstance(friends, list):
            friends = []

        self.data = data
        self.data["friends"] = [self._normalize(x) for x in friends if isinstance(x, dict)]
        self.current_path = path
        self.current = 0 if self.data["friends"] else -1
        self._refresh_all()
        self._update_title()

    def _update_title(self):
        if self.current_path:
            self.setWindowTitle("友链 JSON 编辑器 - %s" % os.path.basename(self.current_path))
        else:
            self.setWindowTitle("友链 JSON 编辑器 - 未保存")

    def _refresh_all(self):
        d = QDate.fromString(str(self.data.get("updated", "")), "yyyy-MM-dd")
        if not d.isValid():
            d = QDate.currentDate()
            self.data["updated"] = d.toString("yyyy-MM-dd")
        self.date_edit.blockSignals(True)
        self.date_edit.setDate(d)
        self.date_edit.blockSignals(False)

        self.refresh_list()

    def refresh_list(self):
        cur = self.current
        self.list.blockSignals(True)
        self.list.clear()
        for f in self.data["friends"]:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, copy.deepcopy(f))
            item.setSizeHint(QSize(0, 62))
            self.list.addItem(item)
        self.list.blockSignals(False)

        count = self.list.count()
        if count == 0:
            self.current = -1
            self._on_current_changed(-1)
        else:
            if not (0 <= cur < count):
                cur = 0
            self.current = cur
            self.list.setCurrentRow(cur)

    def _refresh_item(self, idx):
        if 0 <= idx < self.list.count():
            self.list.item(idx).setData(Qt.UserRole, copy.deepcopy(self.data["friends"][idx]))

    # ------------------------------------------------------------ 交互 ----
    def _on_current_changed(self, row):
        self.current = row
        valid = 0 <= row < len(self.data["friends"])
        self._set_form_enabled(valid)

        if not valid:
            self._loading = True
            for w in self._form_widgets[:6]:
                w.clear()
            self._loading = False
            self.preview.set_data(None)
            return

        d = self.data["friends"][row]
        self._loading = True
        self.ed_name.setText(d["name"])
        self.ed_url.setText(d["url"])
        self.ed_desc.setText(d["desc"])
        self.ed_tags.setText(", ".join(d["tags"]))
        self.ed_avatar.setText(d["avatar"])
        self.ed_initial.setText(d["initial"])
        self.btn_c1.setColor(d["c1"])
        self.btn_c2.setColor(d["c2"])
        self._loading = False
        self.preview.set_data(d)

    def _set_form_enabled(self, ok):
        for w in self._form_widgets:
            w.setEnabled(ok)
        self.btn_del.setEnabled(ok)
        self.btn_up.setEnabled(ok)
        self.btn_down.setEnabled(ok)

    def _on_field_changed(self, *args):
        if self._loading or not (0 <= self.current < len(self.data["friends"])):
            return

        d = self.data["friends"][self.current]
        name = self.ed_name.text().strip()
        initial = self.ed_initial.text().strip()

        d["name"] = name
        d["url"] = self.ed_url.text().strip()
        d["desc"] = self.ed_desc.text().strip()
        d["tags"] = [t.strip() for t in re.split(r"[,，]", self.ed_tags.text()) if t.strip()]
        d["avatar"] = self.ed_avatar.text().strip()
        d["initial"] = initial or (name[:1] if name else "?")
        d["c1"] = self.btn_c1.color()
        d["c2"] = self.btn_c2.color()

        self._refresh_item(self.current)
        self.preview.set_data(d)

    def _on_date_changed(self, date):
        self.data["updated"] = date.toString("yyyy-MM-dd")

    # ------------------------------------------------------------ 列表操作 --
    def add_friend(self):
        d = {
            "name": "新的朋友",
            "url": "https://example.com",
            "desc": "这个人很懒，什么都没有写",
            "tags": ["新朋友"],
            "avatar": "https://example.com/avatar.png",
            "initial": "新",
            "c1": "#8AB4F8",
            "c2": "#5E8BFF",
        }
        self.data["friends"].append(d)
        self.current = len(self.data["friends"]) - 1
        self.refresh_list()
        self.list.setCurrentRow(self.current)
        self.ed_name.setFocus()
        self.ed_name.selectAll()
        self.statusBar().showMessage("已添加一个新好友")

    def remove_friend(self):
        if not (0 <= self.current < len(self.data["friends"])):
            return
        name = self.data["friends"][self.current].get("name", "")
        ret = QMessageBox.question(
            self, "删除确认", "确定要删除「%s」吗？" % name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ret != QMessageBox.Yes:
            return
        del self.data["friends"][self.current]
        if self.data["friends"]:
            self.current = min(self.current, len(self.data["friends"]) - 1)
        else:
            self.current = -1
        self.refresh_list()
        self.statusBar().showMessage("已删除「%s」" % name)

    def move_friend(self, delta):
        i = self.current
        j = i + delta
        friends = self.data["friends"]
        if not (0 <= i < len(friends)) or not (0 <= j < len(friends)):
            return
        friends[i], friends[j] = friends[j], friends[i]
        self.current = j
        self.refresh_list()
        self.statusBar().showMessage("已移动到第 %d 位" % (j + 1))

    # ------------------------------------------------------------ 文件 ----
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 JSON 文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "打开失败", "无法解析该 JSON 文件：\n%s" % e)
            return
        if not isinstance(data, dict):
            QMessageBox.warning(self, "格式不正确", "JSON 根节点应该是一个对象。")
            return
        self.load_data(data, path=path)
        self.statusBar().showMessage("已打开：%s" % path)

    def save_file(self):
        if not self.current_path:
            return self.save_file_as()
        self._write(self.current_path)

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 JSON 文件", "friends.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._write(path)

    def _write(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return False
        self.current_path = path
        self._update_title()
        self.statusBar().showMessage("已保存：%s" % path)
        return True

    # ------------------------------------------------------------ 构建 HTML --
    def _script_dir(self):
        """编辑器所在目录（不是当前工作目录）。"""
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.getcwd()

    def _python_exe(self):
        exe = sys.executable or "python"
        # 如果是 pythonw.exe（无控制台），优先换回 python.exe，方便捕获输出
        base = os.path.basename(exe).lower()
        if base == "pythonw.exe":
            cand = os.path.join(os.path.dirname(exe), "python.exe")
            if os.path.exists(cand):
                return cand
        return exe

    def build_html(self):
        if self._build_proc is not None:
            return  # 正在构建

        script_dir = self._script_dir()
        build_py = os.path.join(script_dir, "build.py")
        if not os.path.exists(build_py):
            QMessageBox.warning(
                self, "未找到 build.py",
                "在编辑器所在目录没有找到 build.py：\n%s" % script_dir
            )
            return

        # 先保存数据（避免构建的是旧数据）
        if self.current_path:
            if not self._write(self.current_path):
                return
        else:
            ret = QMessageBox.question(
                self, "尚未保存",
                "当前数据还没有保存到文件。\n是否先另存为 JSON 再构建？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if ret == QMessageBox.Cancel:
                return
            if ret == QMessageBox.Yes:
                self.save_file_as()
                if not self.current_path:   # 用户取消了保存
                    return

        self.btn_build.setEnabled(False)
        self.btn_build.setText("构建中…")
        self.statusBar().showMessage("正在执行 build.py …")

        self._build_output = []
        proc = QProcess(self)
        proc.setWorkingDirectory(script_dir)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_build_output)
        proc.finished.connect(self._on_build_finished)
        proc.errorOccurred.connect(self._on_build_error)
        self._build_proc = proc

        proc.start(self._python_exe(), [build_py])

    def _on_build_output(self):
        if self._build_proc is None:
            return
        raw = bytes(self._build_proc.readAllStandardOutput())
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = raw.decode(errors="replace")
        self._build_output.append(text)
        # 状态栏显示最后一行
        last = text.strip().splitlines()
        if last:
            self.statusBar().showMessage("build.py: " + last[-1][:120])

    def _on_build_error(self, err):
        if self._build_proc is None:
            return
        self._build_output.append("\n[进程错误] code=%s, %s\n" % (
            int(err), self._build_proc.errorString()
        ))

    def _on_build_finished(self, exit_code, exit_status):
        proc = self._build_proc
        self._build_proc = None

        if proc is not None:
            # 收尾，把剩余输出读干净
            raw = bytes(proc.readAllStandardOutput())
            if raw:
                try:
                    self._build_output.append(raw.decode("utf-8", errors="replace"))
                except Exception:
                    self._build_output.append(raw.decode(errors="replace"))
            proc.deleteLater()

        self.btn_build.setEnabled(True)
        self.btn_build.setText("构建 HTML")

        ok = (exit_status == QProcess.NormalExit) and (exit_code == 0)
        output = "".join(self._build_output).strip() or "（没有输出）"
        # 截断超长输出，避免对话框过大
        if len(output) > 8000:
            output = output[:8000] + "\n…（输出过长，已截断）"

        if ok:
            self.statusBar().showMessage("构建完成 ✓")
            QMessageBox.information(
                self, "构建完成",
                "build.py 执行成功。\n\n输出：\n%s" % output
            )
        else:
            self.statusBar().showMessage("构建失败 ✗（退出码 %s）" % exit_code)
            QMessageBox.critical(
                self, "构建失败",
                "build.py 执行失败（退出码 %s）。\n\n输出：\n%s" % (exit_code, output)
            )

    # ------------------------------------------------------------ 快捷键 --
    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.save_file()
                return
            if event.key() == Qt.Key_O:
                self.open_file()
                return
            if event.key() == Qt.Key_B:
                self.build_html()
                return
        super().keyPressEvent(event)


# ---------------------------------------------------------------- 入口 ------

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()