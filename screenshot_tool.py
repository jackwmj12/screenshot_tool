import re
import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QShortcut,
                             QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QDialog, QDialogButtonBox, QSizePolicy,
                             QFileDialog, QMessageBox, QComboBox, QMenu, QAction,
                             QStyleFactory, QGridLayout, QFrame, QSizeGrip, QCheckBox)
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
        self.setFixedSize(300, 150)

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


class SettingsDialog(QDialog):
    def __init__(self, save_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setFixedSize(400, 200)

        # 创建布局
        layout = QVBoxLayout()

        # 保存路径设置
        path_layout = QHBoxLayout()
        path_label = QLabel("保存路径:")
        self.path_edit = QLineEdit(save_path)
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_folder)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_btn)

        # 文件名格式
        format_layout = QHBoxLayout()
        format_label = QLabel("文件名格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["截图_%Y%m%d_%H%M%S", "截图_%Y%m%d_%H%M%S_%f", "screenshot_%Y%m%d_%H%M%S"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo, 1)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # 添加到主布局
        layout.addLayout(path_layout)
        layout.addLayout(format_layout)
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
            QLabel, QComboBox, QLineEdit, QPushButton {
                font-size: 14px;
                padding: 5px;
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
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QComboBox {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
            }
        """)

    def browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)

    def get_settings(self):
        """获取设置"""
        return self.path_edit.text(), self.format_combo.currentText()


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

        # 创建UI
        self.initUI()
        self.capture_screen()

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

        # 添加快捷键
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.reset_selection)
        QShortcut(QKeySequence("Enter"), self).activated.connect(self.capture_selected_area)
        QShortcut(QKeySequence("Return"), self).activated.connect(self.capture_selected_area)
        QShortcut(QKeySequence("S"), self).activated.connect(self.open_settings)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_settings)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self.close)

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
        self.capture_btn = QPushButton("截图 (Enter)")
        self.capture_btn.clicked.connect(self.capture_selected_area)

        # 重置按钮
        self.reset_btn = QPushButton("重置 (R)")
        self.reset_btn.clicked.connect(self.reset_selection)

        # 设置按钮
        self.settings_btn = QPushButton("设置 (S)")
        self.settings_btn.clicked.connect(self.open_settings)

        # 关闭按钮
        self.close_btn = QPushButton("关闭 (Esc)")
        self.close_btn.clicked.connect(self.close)

        # 状态标签
        self.status_label = QLabel("就绪")

        layout.addWidget(self.capture_btn)
        layout.addWidget(self.reset_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.close_btn)
        layout.addWidget(self.status_label)

        self.toolbar.show()

    def capture_screen(self):
        """捕获整个屏幕并显示在标签上"""
        """捕获整个屏幕并显示在标签上"""
        screen = QApplication.primaryScreen()
        self.screenshot = screen.grabWindow(0)
        self.label.setPixmap(self.screenshot)
        self.reset_selection()

    def reset_selection(self):
        """重置选择区域"""
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
                self.dragging = True
                self.start_point = event.pos()
                self.end_point = event.pos()
                self.rect = QRect()

            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging:
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
            self.start_point = self.rect.topLeft()
            self.end_point = self.rect.bottomRight()
            self.update()
        elif self.dragging_control_point and self.active_control_point and self.rect.isValid():
            # 调整控制点位置
            self.adjust_rect_from_control_point(event.pos())
            self.update()
        elif self.rect.isValid():
            # 更新鼠标光标形状
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
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            self.capture_selected_area()
        else:
            super().keyPressEvent(event)

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
            if new_size and new_size.isValid() and new_size.width() >= 10 and new_size.height() >= 10:
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
        dialog = SettingsDialog(self.save_path, self)
        if dialog.exec_() == QDialog.Accepted:
            self.save_path, self.filename_format = dialog.get_settings()
            self.save_settings()

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

        # 保存设置
        self.save_path = new_path
        self.filename_format = new_format

        logger.debug(f"save_path: {self.save_path}")
        logger.debug(f"filename_format: {self.filename_format}")

        self.settings.setValue("save_path", new_path)
        self.settings.setValue("filename_format", new_format)
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
        success = cv2.imwrite(filepath, cv_image)
        if success:
            # 显示状态信息
            self.status_label.setText(f"已保存: {filename}")

            # 重置选择区域
            self.reset_selection()
        else:
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
    sys.exit(app.exec_())