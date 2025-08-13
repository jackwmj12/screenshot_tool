import re
import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QShortcut,
                             QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QDialog, QDialogButtonBox, QSizePolicy,
                             QFileDialog, QMessageBox, QComboBox, QMenu, QAction,
                             QStyleFactory, QGridLayout, QFrame, QSizeGrip, QCheckBox, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, QSettings, QTimer
from PyQt5.QtGui import (QPixmap, QImage, QPainter, QPen, QColor, QScreen,
                         QKeySequence, QFont, QFontMetrics, QValidator,
                         QCursor, QBrush, QIcon, QPalette)
from loguru import logger

class SizeValidator(QValidator):
    def validate(self, input_text, pos):
        """验证输入是否为有效的整数"""
        if input_text == "":
            return (QValidator.Intermediate, input_text, pos)
        try:
            value = int(input_text)
            if 10 <= value <= 5000:
                return (QValidator.Acceptable, input_text, pos)
            return (QValidator.Intermediate, input_text, pos)
        except ValueError:
            return (QValidator.Invalid, input_text, pos)


class SizeInputDialog(QDialog):
    def __init__(self, current_size, parent=None):
        super().__init__(parent)
        self.setWindowTitle("修改尺寸")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setFixedSize(300, 180)

        # 创建布局
        layout = QVBoxLayout()
        input_layout = QGridLayout()

        # 创建标签
        width_label = QLabel("宽度:")
        height_label = QLabel("高度:")

        # 创建输入框
        self.width_edit = QLineEdit(str(current_size.width()))
        self.width_edit.setValidator(SizeValidator())
        self.width_edit.setAlignment(Qt.AlignCenter)

        self.height_edit = QLineEdit(str(current_size.height()))
        self.height_edit.setValidator(SizeValidator())
        self.height_edit.setAlignment(Qt.AlignCenter)

        # 锁定比例复选框
        self.lock_aspect = QCheckBox("锁定宽高比")
        self.lock_aspect.setChecked(False)
        self.aspect_ratio = current_size.width() / current_size.height() if current_size.height() != 0 else 1

        # 锁定大小复选框
        self.lock_size = QCheckBox("锁定大小")
        self.lock_size.setChecked(False)

        # 连接信号
        self.width_edit.textEdited.connect(self.update_height)
        self.height_edit.textEdited.connect(self.update_width)
        self.lock_aspect.stateChanged.connect(self.toggle_aspect_lock)

        # 添加控件到布局
        input_layout.addWidget(width_label, 0, 0)
        input_layout.addWidget(self.width_edit, 0, 1)
        input_layout.addWidget(height_label, 1, 0)
        input_layout.addWidget(self.height_edit, 1, 1)
        input_layout.addWidget(self.lock_aspect, 2, 0, 1, 2)
        input_layout.addWidget(self.lock_size, 3, 0, 1, 2)

        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # 设置整体布局
        layout.addLayout(input_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 2px solid #3498db;
                border-radius: 8px;
            }
            QLabel {
                font-size: 14px;
                padding: 5px;
            }
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QCheckBox {
                padding: 5px;
                font-size: 14px;
            }
        """)

        # 设置焦点
        self.width_edit.setFocus()
        self.width_edit.selectAll()

    def toggle_aspect_lock(self, state):
        """切换宽高比锁定状态"""
        if state == Qt.Checked:
            try:
                self.aspect_ratio = float(self.width_edit.text()) / float(self.height_edit.text())
            except:
                self.aspect_ratio = 1.0

    def update_height(self, text):
        """根据宽度更新高度（如果锁定宽高比）"""
        if self.lock_aspect.isChecked() and text and self.aspect_ratio != 0:
            try:
                width = int(text)
                height = int(width / self.aspect_ratio)
                self.height_edit.setText(str(height))
            except:
                pass

    def update_width(self, text):
        """根据高度更新宽度（如果锁定宽高比）"""
        if self.lock_aspect.isChecked() and text and self.aspect_ratio != 0:
            try:
                height = int(text)
                width = int(height * self.aspect_ratio)
                self.width_edit.setText(str(width))
            except:
                pass

    def get_size(self):
        """获取用户输入的尺寸"""
        try:
            width = int(self.width_edit.text())
            height = int(self.height_edit.text())
            return QSize(width, height)
        except ValueError:
            return None

    def get_lock_size(self):
        """获取是否锁定大小"""
        return self.lock_size.isChecked()


class HotkeyEdit(QLineEdit):
    def __init__(self, hotkey="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(40)
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 2px solid #3498db;
                border-radius: 6px;
                padding: 10px;
                font-size: 16px;
                font-family: Consolas, Monaco, monospace;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 3px solid #5dade2;
                background-color: #2c3e50;
            }
            QLineEdit:hover {
                border: 2px solid #5dade2;
            }
        """)
        self.hotkey = hotkey
        self.setText(hotkey)
        
    def keyPressEvent(self, event):
        """捕获按键组合"""
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Escape:
            self.setText("")
            self.hotkey = ""
            return
            
        # 忽略单独的修饰键
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
            
        # 使用QKeySequence获取完整的快捷键字符串
        key_sequence = QKeySequence(key | modifiers)
        hotkey = key_sequence.toString()
        
        if hotkey:
            self.setText(hotkey)
            self.hotkey = hotkey
        
    def get_hotkey(self):
        return self.hotkey


class SettingsDialog(QDialog):
    def __init__(self, save_path, hotkeys, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setFixedSize(700, 720)

        # 创建布局
        layout = QVBoxLayout()

        # 保存路径设置
        path_layout = QHBoxLayout()
        path_layout.setSpacing(10)
        path_label = QLabel("保存路径:")
        path_label.setStyleSheet("font-size: 16px; padding: 5px;")
        self.path_edit = QLineEdit(save_path)
        self.path_edit.setReadOnly(True)
        self.path_edit.setMinimumHeight(40)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_folder)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_btn)

        # 文件名格式
        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)
        format_label = QLabel("文件名格式:")
        format_label.setStyleSheet("font-size: 16px; padding: 5px;")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["截图_%Y%m%d_%H%M%S", "截图_%Y%m%d_%H%M%S_%f", "screenshot_%Y%m%d_%H%M%S"])
        self.format_combo.setMinimumHeight(40)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo, 1)

        # 热键设置
        hotkeys_group = QFrame()
        hotkeys_group.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 1px solid #3498db;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        hotkeys_layout = QGridLayout(hotkeys_group)
        hotkeys_layout.setSpacing(20)
        hotkeys_layout.setColumnMinimumWidth(0, 200)
        hotkeys_layout.setColumnStretch(1, 1)
        
        hotkeys_title = QLabel("快捷键设置")
        hotkeys_title.setStyleSheet("font-weight: bold; font-size: 18px; padding: 5px; min-height: 40px;")
        hotkeys_layout.addWidget(hotkeys_title, 0, 0, 1, 2)

        # 创建热键输入框
        self.hotkey_inputs = {}
        hotkey_labels = {
            'toggle_visibility': '显示/隐藏工具',
            'capture_area': '截图',
            'open_settings': '打开设置',
            'quit_app': '退出应用'
        }

        row = 1
        for key, label in hotkey_labels.items():
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px; min-height: 20px;")
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            hotkey_edit = HotkeyEdit(hotkeys.get(key, ""))
            self.hotkey_inputs[key] = hotkey_edit
            
            hotkeys_layout.addWidget(label_widget, row, 0)
            hotkeys_layout.addWidget(hotkey_edit, row, 1)
            row += 1

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # 添加到主布局
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addLayout(path_layout)
        layout.addSpacing(10)
        layout.addLayout(format_layout)
        layout.addSpacing(10)
        layout.addWidget(hotkeys_group)
        layout.addSpacing(15)
        layout.addWidget(button_box)
        self.setLayout(layout)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 2px solid #3498db;
                border-radius: 8px;
            }
            QLabel {
                font-size: 16px;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
            QComboBox, QLineEdit {
                font-size: 16px;
                padding: 10px;
            }
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                min-width: 100px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QComboBox {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 10px;
            }
        """)

    def browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)

    def get_settings(self):
        """获取设置"""
        hotkeys = {}
        for key, edit in self.hotkey_inputs.items():
            hotkeys[key] = edit.get_hotkey()
        return self.path_edit.text(), self.format_combo.currentText(), hotkeys

    def validate_hotkeys(self):
        """验证热键是否有冲突"""
        hotkeys = {}
        conflicts = []
        
        for key, edit in self.hotkey_inputs.items():
            hotkey = edit.get_hotkey()
            if hotkey and hotkey in hotkeys:
                conflicts.append(f"'{hotkey}' 被 '{hotkeys[hotkey]}' 和 '{key}' 同时使用")
            hotkeys[hotkey] = key
            
        return conflicts


class ScreenshotTool(QMainWindow):
    def __init__(self):
        super().__init__()
        # 状态变量
        self.dragging = False
        self.dragging_rect = False
        self.editing_size = False
        self.drag_offset = QPoint()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.rect = QRect()
        self.size_text_rect = QRect()
        self.original_rect = QRect()

        # 控制点状态
        self.dragging_control_point = False
        self.active_control_point = None
        self.control_points = []

        # 控制点尺寸
        self.control_point_size = 10
        self.edge_handle_size = 6
        self.edge_handle_length = 20

        # 设置
        self.settings = QSettings("ScreenshotTool", "ScreenshotTool")
        self.save_path = self.settings.value("save_path", os.path.expanduser("~/Pictures"))
        self.filename_format = self.settings.value("filename_format", "截图_%Y%m%d_%H%M%S")
        
        # 锁定大小设置
        self.locked_size = QSize(
            int(self.settings.value("locked_width", 800)),
            int(self.settings.value("locked_height", 600))
        )
        self.lock_size_enabled = self.settings.value("lock_size_enabled", False, type=bool)
        
        # 默认热键设置
        self.default_hotkeys = {
            'toggle_visibility': 'Ctrl+Alt+A',
            'capture_area': 'Enter',
            'open_settings': 'Ctrl+S',
            'quit_app': 'Ctrl+Q'
        }
        
        # 加载热键设置
        self.hotkeys = {}
        for key, default in self.default_hotkeys.items():
            self.hotkeys[key] = self.settings.value(f"hotkey_{key}", default)

        # 隐藏/显示状态
        self.hidden = False
        self.hidden_pos = QPoint(100, 100)  # 隐藏时的位置
        self.hidden_size = QSize(300, 100)  # 隐藏时的大小

        # 系统托盘
        self.tray_icon = None

        # 快捷键对象
        self.shortcuts = {}

        # 创建UI
        self.initUI()
        self.capture_screen()
        
        # 如果启用了锁定大小，设置初始矩形
        if self.lock_size_enabled:
            self.setup_locked_size()

        # 添加快捷键
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """设置所有快捷键"""
        # 清除现有快捷键
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts.clear()
        
        # 设置新的快捷键
        self.shortcuts['toggle_visibility'] = QShortcut(QKeySequence(self.hotkeys['toggle_visibility']), self)
        self.shortcuts['toggle_visibility'].activated.connect(self.toggle_visibility)
        
        self.shortcuts['capture_area'] = QShortcut(QKeySequence(self.hotkeys['capture_area']), self)
        self.shortcuts['capture_area'].activated.connect(self.capture_selected_area)
        
        self.shortcuts['open_settings'] = QShortcut(QKeySequence(self.hotkeys['open_settings']), self)
        self.shortcuts['open_settings'].activated.connect(self.open_settings)
        
        
        self.shortcuts['quit_app'] = QShortcut(QKeySequence(self.hotkeys['quit_app']), self)
        self.shortcuts['quit_app'].activated.connect(self.quit_application)

    def initUI(self):
        # 设置窗口为全屏无边框透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, QApplication.primaryScreen().size().width(),
                         QApplication.primaryScreen().size().height())

        # 创建标签用于显示屏幕截图
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.width(), self.height())
        self.label.setAlignment(Qt.AlignCenter)

        # 设置鼠标跟踪
        self.setMouseTracking(True)
        self.label.setMouseTracking(True)

        # 创建工具栏
        self.create_toolbar()

        # 创建隐藏时的迷你控制面板
        self.create_mini_control()
        
        # 创建系统托盘
        self.create_system_tray()

    def create_mini_control(self):
        """创建隐藏时显示的迷你控制面板"""
        self.mini_control = QFrame(self)
        self.mini_control.setGeometry(100, 100, 300, 100)
        self.mini_control.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.mini_control.setStyleSheet("""
            QFrame {
                background-color: rgba(44, 62, 80, 200);
                border-radius: 8px;
                border: 2px solid #3498db;
                padding: 10px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-width: 80px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        self.mini_control.setVisible(False)

        layout = QVBoxLayout(self.mini_control)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("截图工具 (Ctrl + Alt + A 显示)")
        title.setAlignment(Qt.AlignCenter)

        # 显示按钮
        show_btn = QPushButton("显示截图工具")
        show_btn.clicked.connect(self.show_screenshot_tool)

        # 退出按钮
        exit_btn = QPushButton("退出")
        exit_btn.clicked.connect(self.close)

        layout.addWidget(title)
        layout.addWidget(show_btn)
        layout.addWidget(exit_btn)

        # 添加拖动功能
        self.mini_control.mousePressEvent = self.mini_control_mousePressEvent
        self.mini_control.mouseMoveEvent = self.mini_control_mouseMoveEvent

    def mini_control_mousePressEvent(self, event):
        """迷你控制面板的鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.mini_control.frameGeometry().topLeft()
            event.accept()

    def mini_control_mouseMoveEvent(self, event):
        """迷你控制面板的鼠标移动事件"""
        if event.buttons() == Qt.LeftButton:
            self.mini_control.move(event.globalPos() - self.drag_position)
            event.accept()

    def create_system_tray(self):
        """创建系统托盘图标"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # 创建托盘图标（使用应用图标或默认图标）
            tray_icon = QIcon()
            # 创建一个简单的图标作为托盘图标
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.blue)
            painter = QPainter(pixmap)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawRect(2, 2, 12, 12)
            painter.drawText(4, 12, "S")
            painter.end()
            tray_icon.addPixmap(pixmap)
            self.tray_icon.setIcon(tray_icon)
            
            # 创建托盘菜单
            tray_menu = QMenu()
            
            show_action = QAction("显示截图工具", self)
            show_action.triggered.connect(self.show_from_tray)
            tray_menu.addAction(show_action)
            
            hide_action = QAction("隐藏截图工具", self)
            hide_action.triggered.connect(self.hide_to_tray)
            tray_menu.addAction(hide_action)
            
            tray_menu.addSeparator()
            
            settings_action = QAction("设置", self)
            settings_action.triggered.connect(self.open_settings)
            tray_menu.addAction(settings_action)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self.quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("截图工具")
            
            # 连接托盘图标激活信号
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()
        elif reason == QSystemTrayIcon.Trigger:
            # 单击显示上下文菜单
            self.tray_icon.contextMenu().popup(QCursor.pos())

    def show_from_tray(self):
        """从托盘显示截图工具"""
        if self.hidden:
            self.show_screenshot_tool()
        else:
            self.showNormal()
            self.activateWindow()

    def hide_to_tray(self):
        """隐藏截图工具到托盘"""
        if not self.hidden:
            self.hide_screenshot_tool()

    def quit_application(self):
        """退出应用程序"""
        if self.tray_icon:
            self.tray_icon.hide()
        self.close()

    def create_toolbar(self):
        """创建截图工具栏"""
        """创建截图工具栏"""
        self.toolbar = QFrame(self)
        self.toolbar.setGeometry(10, 10, 465, 50)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(44, 62, 80, 200);
                border-radius: 8px;
                border: 1px solid #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-width: 80px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 5px;
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(10, 5, 10, 5)

        # 截图按钮
        self.capture_btn = QPushButton("截图")
        self.capture_btn.clicked.connect(self.capture_selected_area)

        # 设置按钮
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.open_settings)

        # 最小化
        self.minimize_btn = QPushButton("最小化")
        self.minimize_btn.clicked.connect(self.hide_to_tray)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.quit_application)

        # 状态标签
        self.status_label = QLabel("就绪")

        layout.addWidget(self.capture_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.close_btn)
        layout.addWidget(self.status_label)

        self.toolbar.show()

    def toggle_visibility(self):
        logger.debug(self.hidden)
        """切换隐藏/显示状态"""
        if self.hidden:
            self.show_screenshot_tool()
        else:
            self.hide_screenshot_tool()

    def clear_canvas(self):
        """清空画布"""
        # 清空截图和矩形选择
        self.screenshot = QPixmap()
        self.rect = QRect()
        self.start_point = QPoint()
        self.end_point = QPoint()
        
        # 清空标签显示
        self.label.clear()
        self.label.setText("截图工具已隐藏")
        self.label.setStyleSheet("color: white; font-size: 24px;")
        
        # 强制刷新显示
        self.label.repaint()
        self.repaint()

    def hide_screenshot_tool(self):
        """隐藏截图工具"""
        # 保存当前窗口位置和大小
        self.hidden_pos = self.pos()
        self.hidden_size = self.size()

        # 清空画布
        self.clear_canvas()

        # 隐藏主窗口
        self.hide()
        self.hidden = True

        # 显示迷你控制面板
        self.mini_control.setGeometry(self.hidden_pos.x(), self.hidden_pos.y(),
                                      self.mini_control.width(), self.mini_control.height())
        self.mini_control.show()

    def show_screenshot_tool(self):
        """显示截图工具"""
        # 隐藏迷你控制面板
        self.mini_control.hide()

        # 恢复主窗口
        self.setGeometry(0, 0, QApplication.primaryScreen().size().width(),
                         QApplication.primaryScreen().size().height())
        self.showFullScreen()
        self.hidden = False

        # 强制清空之前的显示
        self.label.clear()
        self.label.setStyleSheet("")
        
        # 延迟重新捕获屏幕，确保窗口完全显示
        QTimer.singleShot(50, self.delayed_show_screen)

    def delayed_show_screen(self):
        """延迟重新捕获屏幕"""
        self.capture_screen()
        self.reset_selection()

    def capture_screen(self):
        """捕获整个屏幕并显示在标签上"""
        # 确保清除之前的截图
        self.screenshot = QPixmap()
        
        # 获取主屏幕并捕获
        screen = QApplication.primaryScreen()
        if screen:
            self.screenshot = screen.grabWindow(0)
            if not self.screenshot.isNull():
                self.label.setPixmap(self.screenshot)
            else:
                # 如果捕获失败，显示错误信息
                self.label.setText("屏幕捕获失败")
                self.label.setStyleSheet("color: red; font-size: 24px;")
        
        self.reset_selection()

    def setup_locked_size(self):
        """设置锁定大小的矩形"""
        screen_size = QApplication.primaryScreen().size()
        center_x = screen_size.width() // 2
        center_y = screen_size.height() // 2
        
        self.rect = QRect(
            center_x - self.locked_size.width() // 2,
            center_y - self.locked_size.height() // 2,
            self.locked_size.width(),
            self.locked_size.height()
        )
        
        # 确保矩形在屏幕内
        self.rect = self.rect.intersected(QRect(0, 0, screen_size.width(), screen_size.height()))

    def reset_selection(self):
        """重置选择区域"""
        if self.lock_size_enabled:
            # 锁定大小时重新居中矩形
            self.setup_locked_size()
        else:
            # 正常重置
            self.rect = QRect()
            self.start_point = QPoint()
            self.end_point = QPoint()
        
        self.dragging = False
        self.dragging_rect = False
        self.dragging_control_point = False
        self.active_control_point = None
        self.update()
        self.status_label.setText("就绪")
        self.label.setPixmap(self.screenshot)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否在尺寸文本上
            if self.rect.isValid() and self.size_text_rect.contains(event.pos()):
                self.original_rect = self.rect
                self.open_size_dialog()
                return

            # 如果启用了锁定大小，只允许拖动整个矩形
            if self.lock_size_enabled and self.rect.isValid():
                if self.rect.contains(event.pos()):
                    self.dragging_rect = True
                    self.drag_offset = event.pos() - self.rect.topLeft()
                return

            # 正常模式下的处理
            if not self.lock_size_enabled:
                # 检查是否在控制点上
                self.active_control_point = self.get_control_point_at(event.pos())
                if self.active_control_point:
                    self.dragging_control_point = True
                    self.drag_offset = event.pos()
                    return

                # 检查是否在矩形区域内
                if self.rect.isValid() and self.rect.contains(event.pos()):
                    # 拖动矩形模式
                    self.dragging_rect = True
                    self.drag_offset = event.pos() - self.rect.topLeft()
                else:
                    # 绘制新矩形模式
                    if not self.lock_size_enabled:
                        self.dragging = True
                        self.start_point = event.pos()
                        self.end_point = event.pos()
                        self.rect = QRect()

            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and not self.lock_size_enabled:
            self.end_point = event.pos()
            self.rect = self.get_selection_rect()
            self.update()
        elif self.dragging_rect and self.rect.isValid():
            # 计算新的矩形位置
            new_top_left = event.pos() - self.drag_offset
            width = self.rect.width()
            height = self.rect.height()

            # 确保矩形不会移出屏幕
            new_top_left.setX(max(0, min(new_top_left.x(), self.width() - width)))
            new_top_left.setY(max(0, min(new_top_left.y(), self.height() - height)))

            # 更新矩形位置
            self.rect.moveTo(new_top_left)
            if not self.lock_size_enabled:
                self.start_point = self.rect.topLeft()
                self.end_point = self.rect.bottomRight()
            self.update()
        elif self.dragging_control_point and self.active_control_point and self.rect.isValid() and not self.lock_size_enabled:
            # 调整控制点位置
            self.adjust_rect_from_control_point(event.pos())
            self.update()
        elif self.rect.isValid():
            # 更新鼠标光标形状
            if self.lock_size_enabled:
                # 锁定大小时只显示移动光标
                if self.rect.contains(event.pos()):
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
            else:
                control_point = self.get_control_point_at(event.pos())
                if control_point:
                    cursor = self.get_cursor_for_control_point(control_point)
                    self.setCursor(cursor)
                elif self.rect.contains(event.pos()):
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            if self.dragging:
                self.dragging = False
                self.end_point = event.pos()
                self.rect = self.get_selection_rect()
            elif self.dragging_rect:
                self.dragging_rect = False
            elif self.dragging_control_point:
                self.dragging_control_point = False
                self.active_control_point = None

            self.update()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        # 使用QKeySequence来匹配配置的快捷键
        key_sequence = QKeySequence(event.key() | event.modifiers())
        
        # 检查是否匹配配置的快捷键
        for action, hotkey in self.hotkeys.items():
            if str(key_sequence) == str(QKeySequence(hotkey)):
                if action == 'capture_area':
                    self.capture_selected_area()
                elif action == 'open_settings':
                    self.open_settings()
                elif action == 'quit_app':
                    self.quit_application()
                return
                
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide_to_tray()
            event.ignore()
        else:
            self.quit_application()
            event.accept()

    def paintEvent(self, event):
        """绘制事件 - 绘制矩形选择框和尺寸文本"""
        if self.dragging or self.rect.isValid():
            # 创建屏幕截图副本
            pixmap = self.screenshot.copy()
            painter = QPainter(pixmap)

            # 设置半透明遮罩
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.drawRect(0, 0, pixmap.width(), pixmap.height())

            # 清除选择区域内的遮罩
            if self.rect.isValid():
                rect = self.rect
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.drawPixmap(rect, self.screenshot, rect)

                # 绘制选择框
                pen = QPen(Qt.red, 2, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawRect(rect)

                # 绘制控制点和调整手柄
                if not self.lock_size_enabled:
                    self.draw_control_points(painter, rect)

                # 绘制尺寸文本
                font = QFont("Arial", 12)
                painter.setFont(font)
                text = f"{rect.width()} × {rect.height()} (点击修改)"

                # 计算文本大小
                metrics = QFontMetrics(font)
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()

                # 设置文本位置（矩形下方）
                text_x = rect.x() + (rect.width() - text_width) // 2
                text_y = rect.bottom() + text_height + 5

                # 确保文本在屏幕内
                if text_y > self.height() - 10:
                    text_y = rect.top() - 10

                # 绘制文本背景
                bg_rect = QRect(text_x - 5, text_y - text_height, text_width + 10, text_height + 5)
                painter.setBrush(QColor(0, 0, 0, 180))
                painter.setPen(Qt.NoPen)
                painter.drawRect(bg_rect)

                # 保存文本矩形用于点击检测
                self.size_text_rect = bg_rect

                # 绘制文本
                painter.setPen(Qt.yellow)
                painter.drawText(text_x, text_y, text)
                painter.drawText(text_x, text_y - rect.height() - text_height - 10, f"{rect.x()} : {rect.y()}(起点坐标)")

                logger.debug(f"当前截图 x: {rect.x()} y: {rect.y()} width: {rect.width()} height: {rect.height()}")

            painter.end()
            self.label.setPixmap(pixmap)

    def draw_control_points(self, painter, rect):
        """绘制控制点和调整手柄"""
        # 清空控制点列表
        self.control_points = []

        # 绘制四个角的控制点
        for point_type, pos in [
            ('topleft', rect.topLeft()),
            ('topright', rect.topRight()),
            ('bottomleft', rect.bottomLeft()),
            ('bottomright', rect.bottomRight())
        ]:
            # 计算控制点位置
            control_rect = QRect(
                pos.x() - self.control_point_size // 2,
                pos.y() - self.control_point_size // 2,
                self.control_point_size,
                self.control_point_size
            )

            # 保存控制点位置和类型
            self.control_points.append((control_rect, point_type))

            # 绘制控制点
            painter.setPen(QPen(Qt.blue, 1))
            painter.setBrush(QBrush(Qt.red))
            painter.drawRect(control_rect)

        # 绘制四个边的调整手柄
        # 上边中点
        top_center = QPoint(rect.left() + rect.width() // 2, rect.top())
        top_handle = QRect(
            top_center.x() - self.edge_handle_length // 2,
            top_center.y() - self.edge_handle_size // 2,
            self.edge_handle_length,
            self.edge_handle_size
        )
        self.control_points.append((top_handle, 'top'))

        # 下边中点
        bottom_center = QPoint(rect.left() + rect.width() // 2, rect.bottom())
        bottom_handle = QRect(
            bottom_center.x() - self.edge_handle_length // 2,
            bottom_center.y() - self.edge_handle_size // 2,
            self.edge_handle_length,
            self.edge_handle_size
        )
        self.control_points.append((bottom_handle, 'bottom'))

        # 左边中点
        left_center = QPoint(rect.left(), rect.top() + rect.height() // 2)
        left_handle = QRect(
            left_center.x() - self.edge_handle_size // 2,
            left_center.y() - self.edge_handle_length // 2,
            self.edge_handle_size,
            self.edge_handle_length
        )
        self.control_points.append((left_handle, 'left'))

        # 右边中点
        right_center = QPoint(rect.right(), rect.top() + rect.height() // 2)
        right_handle = QRect(
            right_center.x() - self.edge_handle_size // 2,
            right_center.y() - self.edge_handle_length // 2,
            self.edge_handle_size,
            self.edge_handle_length
        )
        self.control_points.append((right_handle, 'right'))

        # 绘制边手柄
        painter.setPen(QPen(Qt.blue, 1))
        painter.setBrush(QBrush(Qt.green))
        painter.drawRect(top_handle)
        painter.drawRect(bottom_handle)
        painter.drawRect(left_handle)
        painter.drawRect(right_handle)

    def get_control_point_at(self, pos):
        """检查鼠标位置是否在控制点上"""
        for rect, point_type in self.control_points:
            if rect.contains(pos):
                return point_type
        return None

    def get_cursor_for_control_point(self, point_type):
        """根据控制点类型返回适当的鼠标光标"""
        if point_type in ['topleft', 'bottomright']:
            return Qt.SizeFDiagCursor
        elif point_type in ['topright', 'bottomleft']:
            return Qt.SizeBDiagCursor
        elif point_type in ['top', 'bottom']:
            return Qt.SizeVerCursor
        elif point_type in ['left', 'right']:
            return Qt.SizeHorCursor
        return Qt.ArrowCursor

    def adjust_rect_from_control_point(self, mouse_pos):
        """根据控制点调整矩形大小"""
        if not self.active_control_point or not self.rect.isValid():
            return

        # 创建矩形副本
        rect = self.rect.normalized()

        # 根据控制点类型调整矩形
        if self.active_control_point == 'topleft':
            rect.setTopLeft(mouse_pos)
        elif self.active_control_point == 'topright':
            rect.setTopRight(mouse_pos)
        elif self.active_control_point == 'bottomleft':
            rect.setBottomLeft(mouse_pos)
        elif self.active_control_point == 'bottomright':
            rect.setBottomRight(mouse_pos)
        elif self.active_control_point == 'top':
            rect.setTop(mouse_pos.y())
        elif self.active_control_point == 'bottom':
            rect.setBottom(mouse_pos.y())
        elif self.active_control_point == 'left':
            rect.setLeft(mouse_pos.x())
        elif self.active_control_point == 'right':
            rect.setRight(mouse_pos.x())

        # 确保矩形不小于最小尺寸
        min_size = 20
        if rect.width() < min_size:
            if self.active_control_point in ['left', 'topleft', 'bottomleft']:
                rect.setLeft(rect.right() - min_size)
            else:
                rect.setRight(rect.left() + min_size)

        if rect.height() < min_size:
            if self.active_control_point in ['top', 'topleft', 'topright']:
                rect.setTop(rect.bottom() - min_size)
            else:
                rect.setBottom(rect.top() + min_size)

        # 确保矩形在屏幕范围内
        rect = rect.intersected(QRect(0, 0, self.width(), self.height()))

        # 更新矩形
        self.rect = rect
        self.start_point = rect.topLeft()
        self.end_point = rect.bottomRight()

    def get_selection_rect(self):
        """获取规范化矩形区域"""
        if self.dragging:
            return QRect(
                min(self.start_point.x(), self.end_point.x()),
                min(self.start_point.y(), self.end_point.y()),
                abs(self.start_point.x() - self.end_point.x()),
                abs(self.start_point.y() - self.end_point.y())
            )
        elif self.rect.isValid():
            return self.rect
        return QRect()

    def open_size_dialog(self):
        """打开尺寸修改对话框"""
        dialog = SizeInputDialog(self.rect.size(), self)
        if dialog.exec_() == QDialog.Accepted:
            new_size = dialog.get_size()
            lock_size = dialog.get_lock_size()
            if new_size and new_size.isValid() and new_size.width() >= 10 and new_size.height() >= 10:
                # 更新锁定大小设置
                self.locked_size = new_size
                self.lock_size_enabled = lock_size
                
                # 保存到配置
                self.settings.setValue("locked_width", new_size.width())
                self.settings.setValue("locked_height", new_size.height())
                self.settings.setValue("lock_size_enabled", lock_size)
                
                if not lock_size:
                    # 保持矩形中心点不变
                    center = self.rect.center()
                    new_rect = QRect(0, 0, new_size.width(), new_size.height())
                    new_rect.moveCenter(center)

                    # 确保矩形在屏幕内
                    if new_rect.left() < 0:
                        new_rect.moveLeft(0)
                    if new_rect.top() < 0:
                        new_rect.moveTop(0)
                    if new_rect.right() > self.width():
                        new_rect.moveRight(self.width())
                    if new_rect.bottom() > self.height():
                        new_rect.moveBottom(self.height())

                    self.rect = new_rect
                
                self.update()

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.save_path, self.hotkeys, self)
        if dialog.exec_() == QDialog.Accepted:
            self.save_path, self.filename_format, self.hotkeys = dialog.get_settings()
            self.save_settings()
            self.setup_shortcuts()  # 重新设置快捷键

    def save_settings(self):
        """保存设置"""
        new_path = self.save_path.strip().replace("/", "\\")
        new_format = self.filename_format.strip()

        # 验证路径
        if not new_path:
            QMessageBox.warning(self, "错误", "保存路径不能为空")
            return

        # 验证文件名格式
        if not new_format:
            QMessageBox.warning(self, "错误", "文件名格式不能为空")
            return

        # 尝试格式验证
        try:
            from datetime import datetime
            test_name = datetime.now().strftime(new_format)
            if not test_name:
                raise ValueError("格式无效")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"文件名格式无效: {str(e)}")
            return

        # 验证热键设置
        hotkey_map = {}
        for key, hotkey in self.hotkeys.items():
            if not hotkey:
                QMessageBox.warning(self, "错误", f"{key} 的快捷键不能为空")
                return
            if hotkey in hotkey_map:
                QMessageBox.warning(self, "错误", f"快捷键 '{hotkey}' 已被 '{hotkey_map[hotkey]}' 和 '{key}' 同时使用")
                return
            hotkey_map[hotkey] = key

        # 保存设置
        self.save_path = new_path
        self.filename_format = new_format

        logger.debug(f"save_path: {self.save_path}")
        logger.debug(f"filename_format: {self.filename_format}")
        logger.debug(f"hotkeys: {self.hotkeys}")

        self.settings.setValue("save_path", new_path)
        self.settings.setValue("filename_format", new_format)
        
        # 保存热键设置
        for key, hotkey in self.hotkeys.items():
            self.settings.setValue(f"hotkey_{key}", hotkey)
            
        QMessageBox.information(self, "设置已保存", "设置已成功保存！")

    def capture_selected_area(self):
        """捕获选定区域并进行处理"""
        if not self.rect.isValid() or self.rect.width() < 10 or self.rect.height() < 10:
            self.status_label.setText("区域无效，请重新选择")
            QTimer.singleShot(2000, lambda: self.status_label.setText("就绪"))
            return

        # 从原始截图获取选定区域
        selected_area = self.screenshot.copy(self.rect)

        # 转换为OpenCV格式（修复内存对齐问题）
        qimage = selected_area.toImage().convertToFormat(QImage.Format_RGB888)
        width = qimage.width()
        height = qimage.height()

        # 获取每行的字节数和总字节数
        bytes_per_line = qimage.bytesPerLine()
        total_bytes = bytes_per_line * height

        # 获取图像数据
        ptr = qimage.bits()
        ptr.setsize(total_bytes)

        # 创建numpy数组
        arr = np.frombuffer(ptr, dtype=np.uint8, count=total_bytes)

        # 处理内存对齐问题
        if bytes_per_line == width * 3:
            # 没有填充字节的情况
            cv_image = arr.reshape(height, width, 3)
        else:
            # 有填充字节的情况 - 逐行处理
            cv_image = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                start = i * bytes_per_line
                end = start + width * 3
                row_data = arr[start:end].reshape(width, 3)
                cv_image[i] = row_data

        # 转换为BGR格式
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

        # 生成文件名
        from datetime import datetime
        filename = datetime.now().strftime(self.filename_format) + ".png"
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)  # 过滤非法字符
        filepath = os.path.join(self.save_path, filename)

        # 确保目录存在
        os.makedirs(self.save_path, exist_ok=True)

        # 保存截图
        # success = cv2.imwrite(filepath, cv_image)
        success = cv2.imencode('.png', cv_image)[1].tofile(filepath)  # 替换imwrite
        logger.debug(success)
        if os.path.isfile(filepath):
            # 显示状态信息
            self.status_label.setText(f"已保存: {filename}")
            # 重置选择区域
            self.reset_selection()
        else:
            logger.debug("保存失败")
            self.status_label.setText("保存失败")
            QTimer.singleShot(3000, lambda: self.status_label.setText("就绪"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))

    # 设置应用样式
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = ScreenshotTool()
    window.showFullScreen()
    
    # 显示托盘提示信息
    if window.tray_icon and window.tray_icon.isSystemTrayAvailable():
        window.tray_icon.showMessage(
            "截图工具已启动",
            "程序已最小化到系统托盘\n双击托盘图标可显示/隐藏\n右键托盘图标可查看更多选项",
            QSystemTrayIcon.Information,
            3000
        )
    
    sys.exit(app.exec_())