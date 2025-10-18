#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网认证助手 - UI界面 v2.0
新增功能: 托盘、通知、多账号、统计、日志
"""

import sys
import os
import json
import time
from pathlib import Path

# Windows注册表支持(仅Windows)
try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit, QPushButton, QRadioButton,
                                QCheckBox, QButtonGroup, QFrame, QMessageBox,
                                QSystemTrayIcon, QMenu, QComboBox, QDialog,
                                QListWidget, QDialogButtonBox, QTextEdit, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QIcon, QAction

# 导入认证模块
from srun_encrypted import srun_encrypted_auth
import network

# 导入新模块
from config_manager import ConfigManager
from logger import logger
from network_stats import NetworkStats

# 导入电源监控模块
try:
    from power_monitor import get_power_monitor
    POWER_MONITOR_AVAILABLE = True
except ImportError:
    POWER_MONITOR_AVAILABLE = False


class AuthThread(QThread):
    """单次认证线程"""
    finished = Signal(bool, str)

    def __init__(self, username, password, operator):
        super().__init__()
        self.username = username
        self.password = password
        self.operator = operator

    def run(self):
        try:
            current_ip = network.get_current_ip()
            if not current_ip:
                logger.error("无法获取IP地址")
                self.finished.emit(False, "无法获取IP地址")
                return

            full_username = self.username + self.operator
            logger.info(f"开始认证: {full_username}, IP: {current_ip}")

            success, message, data = srun_encrypted_auth.login(
                full_username, self.password, current_ip, ac_id=1
            )

            if success:
                logger.info(f"认证成功: {message}")
            else:
                logger.warning(f"认证失败: {message}")

            self.finished.emit(success, message)

        except Exception as e:
            error_msg = f"认证异常: {str(e)}"
            logger.error(error_msg)
            self.finished.emit(False, error_msg)


class MonitorThread(QThread):
    """循环监控线程"""
    status_update = Signal(str)
    auth_trigger = Signal()

    def __init__(self, check_interval=60):
        super().__init__()
        self.check_interval = check_interval
        self.running = True
        self.login_count = 0
        self.max_login = 100
        self._is_authenticating = False

    def run(self):
        try:
            while self.running and self.login_count < self.max_login:
                for _ in range(self.check_interval * 2):
                    if not self.running:
                        return
                    time.sleep(0.5)

                if self.running and not self._is_authenticating:
                    self.status_update.emit(f"正在检查网络状态... (已检查{self.login_count}次)")

                    try:
                        if not network.network_check(timeout=3):
                            self._is_authenticating = True
                            self.status_update.emit("检测到网络断开,准备重新认证...")
                            logger.warning("网络断开，触发重新认证")
                            self.auth_trigger.emit()
                            self.login_count += 1

                            for _ in range(60):
                                if not self.running:
                                    return
                                time.sleep(0.5)

                            self._is_authenticating = False
                        else:
                            self.status_update.emit(f"✓ 网络正常 (第{self.login_count + 1}次检查)")
                    except Exception as e:
                        logger.error(f"网络检查异常: {e}")
                        self._is_authenticating = False

        except Exception as e:
            logger.error(f"监控线程异常: {e}")

    def stop(self):
        self.running = False


class StatsDialog(QDialog):
    """统计信息对话框"""

    def __init__(self, stats: NetworkStats, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.setWindowTitle("网络统计")
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 统计摘要
        summary_label = QLabel(self.stats.get_stats_summary())
        summary_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                padding: 15px;
                background-color: #F5F5F7;
                border-radius: 8px;
            }
        """)
        layout.addWidget(summary_label)

        # 历史记录
        history_label = QLabel("最近认证历史")
        history_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(history_label)

        history_list = QListWidget()
        history_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)

        for item in self.stats.get_recent_history(20):
            status = "✓" if item['success'] else "✗"
            text = f"{item['time']} - {status} {item['message']}"
            history_list.addItem(text)

        layout.addWidget(history_list)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class AccountManageDialog(QDialog):
    """账号管理对话框"""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("账号管理")
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 账号列表
        list_label = QLabel("保存的账号")
        list_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(list_label)

        self.account_list = QListWidget()
        self.account_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        self.refresh_list()
        layout.addWidget(self.account_list)

        # 按钮
        btn_layout = QHBoxLayout()
        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_account)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def refresh_list(self):
        self.account_list.clear()
        accounts = self.config_manager.get_accounts()
        for account in accounts:
            name = account.get('name', f"{account['username']}{account['operator']}")
            self.account_list.addItem(name)

    def delete_account(self):
        current_row = self.account_list.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "确认删除",
                "确定要删除选中的账号吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.config_manager.remove_account(current_row):
                    self.config_manager.save(self.config_manager.config)
                    self.refresh_list()
                    QMessageBox.information(self, "成功", "账号已删除")


class CampusNetworkWindow(QMainWindow):
    """校园网认证主窗口 - 增强版"""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.stats = NetworkStats()
        self.auth_thread = None
        self.monitor_thread = None
        self.is_monitoring = False
        self.power_monitor = None
        self.tray_icon = None

        # 统计定时器
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats_display)
        self.stats_timer.start(1000)

        self.init_ui()
        self.load_config()
        self.setup_tray_icon()

        if POWER_MONITOR_AVAILABLE:
            self.setup_power_monitor()

        self.check_auto_start_status()

        if self.auto_login_checkbox.isChecked():
            QTimer.singleShot(1000, self.smart_connect_and_auth)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("校园网认证助手 v2.0")
        self.setFixedSize(480, 650)

        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(12)

        # 标题
        title_label = QLabel("校园网认证助手")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a1a1a; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # 账号选择区域
        account_frame = QFrame()
        account_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)
        account_layout = QVBoxLayout(account_frame)
        account_layout.setContentsMargins(15, 15, 15, 15)
        account_layout.setSpacing(8)

        # 账号下拉框
        account_select_layout = QHBoxLayout()
        account_label = QLabel("快速选择:")
        self.account_combo = QComboBox()
        self.account_combo.addItem("新建账号...")
        self.account_combo.currentIndexChanged.connect(self.on_account_selected)
        self.account_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #F5F5F7;
            }
        """)
        manage_account_btn = QPushButton("管理")
        manage_account_btn.setFixedWidth(60)
        manage_account_btn.clicked.connect(self.show_account_manage)
        manage_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        account_select_layout.addWidget(account_label)
        account_select_layout.addWidget(self.account_combo, 1)
        account_select_layout.addWidget(manage_account_btn)
        account_layout.addLayout(account_select_layout)

        main_layout.addWidget(account_frame)

        # 配置区域
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(10)

        # 学号输入
        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("请输入一卡通号")
        self.student_id_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #F5F5F7;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
                background-color: #FFFFFF;
            }
        """)
        config_layout.addWidget(self.student_id_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.student_id_input.styleSheet())
        config_layout.addWidget(self.password_input)

        # 运营商选择
        operator_label = QLabel("运营商选择")
        operator_label.setStyleSheet("font-size: 13px; color: #666666;")
        config_layout.addWidget(operator_label)

        operator_layout = QHBoxLayout()
        operator_layout.setSpacing(15)
        operator_layout.setContentsMargins(0, 5, 0, 5)

        self.operator_group = QButtonGroup(self)
        operators = [
            ("电信", "@chinanet"),
            ("移动", "@cmcc"),
            ("联通", "@chinaunicom"),
            ("办公", "@")
        ]

        for text, value in operators:
            radio = QRadioButton(text)
            radio.setProperty("value", value)
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 13px;
                    spacing: 5px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            self.operator_group.addButton(radio)
            operator_layout.addWidget(radio)

        self.operator_group.buttons()[0].setChecked(True)
        config_layout.addLayout(operator_layout)

        # 选项
        self.auto_login_checkbox = QCheckBox("启动时自动登录")
        self.auto_login_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #333333;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        config_layout.addWidget(self.auto_login_checkbox)

        self.auto_start_checkbox = QCheckBox("开机自动启动")
        self.auto_start_checkbox.setStyleSheet(self.auto_login_checkbox.styleSheet())
        self.auto_start_checkbox.toggled.connect(self.on_auto_start_changed)
        config_layout.addWidget(self.auto_start_checkbox)

        self.save_account_checkbox = QCheckBox("保存此账号到列表")
        self.save_account_checkbox.setStyleSheet(self.auto_login_checkbox.styleSheet())
        config_layout.addWidget(self.save_account_checkbox)

        main_layout.addWidget(config_frame)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.login_button = QPushButton("立即登录")
        self.login_button.setFixedHeight(48)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:pressed {
                background-color: #004299;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.login_button.clicked.connect(self.on_login_clicked)
        button_layout.addWidget(self.login_button)

        self.stop_button = QPushButton("停止监控")
        self.stop_button.setFixedHeight(48)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #FF3B30;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #CC2F26;
            }
            QPushButton:pressed {
                background-color: #99241D;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.stop_button.clicked.connect(self.stop_monitoring)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(button_layout)

        # 统计按钮
        stats_btn = QPushButton("查看统计")
        stats_btn.setFixedHeight(36)
        stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2BA047;
            }
        """)
        stats_btn.clicked.connect(self.show_stats)
        main_layout.addWidget(stats_btn)

        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #666666;
                padding: 10px;
                border-radius: 8px;
                background-color: #F5F5F7;
            }
        """)
        main_layout.addWidget(self.status_label)

        # 统计信息标签
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #999999;
                padding: 8px;
            }
        """)
        main_layout.addWidget(self.stats_label)

        main_layout.addStretch()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F7;
            }
        """)

    def setup_tray_icon(self):
        """设置系统托盘图标"""
        icon_path = self.get_icon_path()
        if not icon_path:
            return

        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)

        # 创建托盘菜单
        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        stats_action = QAction("查看统计", self)
        stats_action.triggered.connect(self.show_stats)
        tray_menu.addAction(stats_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        logger.info("系统托盘已初始化")

    def on_tray_activated(self, reason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def show_window(self):
        """显示窗口"""
        self.show()
        self.activateWindow()

    def quit_application(self):
        """退出应用"""
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        """窗口关闭事件 - 最小化到托盘"""
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "校园网认证助手",
                "程序已最小化到托盘，继续在后台运行",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.cleanup_and_close()
            event.accept()

    def cleanup_and_close(self):
        """清理并关闭"""
        if self.is_monitoring:
            self.stop_monitoring()

        if self.power_monitor:
            self.power_monitor.stop()

        self.stats.end_session()
        self.save_config()
        logger.info("程序正常退出")

    def get_icon_path(self):
        """获取图标路径"""
        possible_paths = [
            "image.ico",
            "11409B.png",
            os.path.join(os.path.dirname(__file__), "image.ico"),
            os.path.join(os.path.dirname(__file__), "11409B.png")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def load_config(self):
        """加载配置"""
        try:
            config = self.config_manager.load()

            self.student_id_input.setText(config.get('username', ''))
            self.password_input.setText(config.get('password', ''))

            operator = config.get('operator', '@chinanet')
            for button in self.operator_group.buttons():
                if button.property("value") == operator:
                    button.setChecked(True)
                    break

            self.auto_login_checkbox.setChecked(config.get('auto_login', False))

            # 加载账号列表到下拉框
            self.refresh_account_list()

        except Exception as e:
            logger.error(f"加载配置失败: {e}")

    def refresh_account_list(self):
        """刷新账号列表"""
        self.account_combo.clear()
        self.account_combo.addItem("新建账号...")

        accounts = self.config_manager.get_accounts()
        for account in accounts:
            name = account.get('name', f"{account['username']}{account['operator']}")
            self.account_combo.addItem(name)

    def on_account_selected(self, index):
        """账号选择事件"""
        if index == 0:
            return

        accounts = self.config_manager.get_accounts()
        if index - 1 < len(accounts):
            account = accounts[index - 1]
            self.student_id_input.setText(account.get('username', ''))
            self.password_input.setText(account.get('password', ''))

            operator = account.get('operator', '@chinanet')
            for button in self.operator_group.buttons():
                if button.property("value") == operator:
                    button.setChecked(True)
                    break

    def show_account_manage(self):
        """显示账号管理对话框"""
        dialog = AccountManageDialog(self.config_manager, self)
        dialog.exec()
        self.refresh_account_list()

    def show_stats(self):
        """显示统计信息"""
        dialog = StatsDialog(self.stats, self)
        dialog.exec()

    def update_stats_display(self):
        """更新统计显示"""
        if self.is_monitoring:
            session_time = self.stats.get_current_session_time()
            total_time = self.stats.get_total_online_time() + session_time
            formatted_time = self.stats.format_time(total_time)
            self.stats_label.setText(f"本次在线: {self.stats.format_time(session_time)} | 总计: {formatted_time}")
        else:
            total_time = self.stats.get_total_online_time()
            if total_time > 0:
                self.stats_label.setText(f"历史在线时长: {self.stats.format_time(total_time)}")

    def save_config(self):
        """保存配置"""
        try:
            config = {
                'username': self.student_id_input.text(),
                'password': self.password_input.text(),
                'operator': self.get_selected_operator(),
                'auto_login': self.auto_login_checkbox.isChecked()
            }

            # 如果勾选了保存账号
            if self.save_account_checkbox.isChecked():
                self.config_manager.add_account(
                    config['username'],
                    config['password'],
                    config['operator']
                )
                self.refresh_account_list()

            self.config_manager.save(config)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def get_selected_operator(self):
        """获取选中的运营商"""
        for button in self.operator_group.buttons():
            if button.isChecked():
                return button.property("value")
        return "@chinanet"

    def on_login_clicked(self):
        """登录按钮点击"""
        username = self.student_id_input.text().strip()
        password = self.password_input.text().strip()

        if not username:
            self.update_status("请输入一卡通号", error=True)
            self.show_notification("输入错误", "请输入一卡通号", QSystemTrayIcon.MessageIcon.Warning)
            return

        if not password:
            self.update_status("请输入密码", error=True)
            self.show_notification("输入错误", "请输入密码", QSystemTrayIcon.MessageIcon.Warning)
            return

        self.save_config()
        self.smart_connect_and_auth()

    def smart_connect_and_auth(self):
        """智能连接和认证流程"""
        self.update_status("正在检测网络环境...")
        connection_type = network.get_connection_type()

        if connection_type == 'ethernet':
            self.update_status("✓ 检测到以太网连接,准备认证...")
            QTimer.singleShot(500, self.start_auth)

        elif connection_type == 'wifi':
            current_wifi = network.get_connected_wifi()
            if current_wifi:
                self.update_status(f"✓ 已连接WiFi: {current_wifi},准备认证...")
                QTimer.singleShot(500, self.start_auth)
            else:
                self.update_status("WiFi未连接,尝试连接校园网...")
                self.try_connect_campus_wifi()

        else:
            self.update_status("未检测到网络连接,尝试连接校园网WiFi...")
            self.try_connect_campus_wifi()

    def try_connect_campus_wifi(self):
        """尝试连接校园网WiFi"""
        self.update_status("正在扫描开放WiFi网络...")

        try:
            best_ssid = network.scan_open_wifi()

            if best_ssid == 'PERMISSION_DENIED':
                self.show_location_permission_dialog()
                return

            if best_ssid == 'WIFI_DISABLED':
                self.show_wifi_disabled_dialog()
                return

            if best_ssid:
                self.update_status(f"找到校园网: {best_ssid},正在连接...")

                if network.connect_to_wifi(best_ssid):
                    self.update_status(f"✓ 成功连接到 {best_ssid},等待IP分配...")

                    for i in range(20):
                        QTimer.singleShot(500 * i, lambda: None)
                        time.sleep(0.5)
                        current_ip = network.get_current_ip()
                        if current_ip:
                            self.update_status(f"✓ 已获取IP: {current_ip},开始认证...")
                            QTimer.singleShot(500, self.start_auth)
                            return

                    self.update_status("⚠ WiFi已连接但未获取IP,尝试认证...", error=True)
                    QTimer.singleShot(500, self.start_auth)
                else:
                    self.update_status(f"✗ 连接到 {best_ssid} 失败", error=True)
            else:
                self.update_status("✗ 未找到开放的校园网WiFi", error=True)

        except Exception as e:
            logger.error(f"WiFi连接失败: {e}")
            self.update_status(f"✗ WiFi连接失败: {str(e)}", error=True)

    def show_wifi_disabled_dialog(self):
        """显示WiFi未连接提示对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("WiFi未连接")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("WiFi适配器未连接")
        msg_box.setInformativeText(
            "检测到WiFi适配器未连接到任何网络。\n\n"
            "WiFi扫描需要WiFi适配器处于活动状态。\n\n"
            "您可以:\n"
            "1. 点击\"打开WiFi设置\"手动连接到校园网WiFi\n"
            "2. 连接成功后点击\"重新检测\"继续认证"
        )

        open_settings_btn = msg_box.addButton("打开WiFi设置", QMessageBox.ButtonRole.AcceptRole)
        retry_btn = msg_box.addButton("重新检测", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        clicked_button = msg_box.clickedButton()

        if clicked_button == open_settings_btn:
            if network.open_wifi_settings():
                self.update_status("已打开WiFi设置,请连接到校园网WiFi后点击\"重新检测\"")
            else:
                self.update_status("打开WiFi设置失败", error=True)
        elif clicked_button == retry_btn:
            self.update_status("正在重新检测网络连接...")
            QTimer.singleShot(500, self.smart_connect_and_auth)
        else:
            self.update_status("已取消WiFi连接")

    def show_location_permission_dialog(self):
        """显示位置权限提示对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("需要位置权限")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("WiFi扫描需要位置权限")
        msg_box.setInformativeText(
            "Windows需要位置权限才能扫描WiFi网络。\n\n"
            "您可以:\n"
            "1. 点击\"打开位置设置\"启用权限\n"
            "2. 或者手动连接到校园网WiFi后再使用本程序"
        )

        open_settings_btn = msg_box.addButton("打开位置设置", QMessageBox.ButtonRole.AcceptRole)
        manual_connect_btn = msg_box.addButton("我已手动连接WiFi", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        clicked_button = msg_box.clickedButton()

        if clicked_button == open_settings_btn:
            if network.open_location_settings():
                self.update_status("已打开位置设置,请启用位置权限后重试")
            else:
                self.update_status("打开位置设置失败", error=True)
        elif clicked_button == manual_connect_btn:
            self.update_status("正在重新检测网络连接...")
            QTimer.singleShot(500, self.smart_connect_and_auth)
        else:
            self.update_status("已取消WiFi扫描")

    def start_auth(self):
        """开始认证"""
        self.login_button.setEnabled(False)
        self.login_button.setText("认证中...")
        self.update_status("正在进行校园网认证...")

        username = self.student_id_input.text().strip()
        password = self.password_input.text().strip()
        operator = self.get_selected_operator()

        self.auth_thread = AuthThread(username, password, operator)
        self.auth_thread.finished.connect(self.on_auth_finished)
        self.auth_thread.start()

    def on_auth_finished(self, success, message):
        """认证完成"""
        self.login_button.setEnabled(True)
        self.login_button.setText("立即登录")

        # 记录统计
        self.stats.record_login(success, message)

        if success:
            self.update_status(f"✓ {message}", error=False)
            self.show_notification("认证成功", message, QSystemTrayIcon.MessageIcon.Information)

            # 启动会话计时
            self.stats.start_session()

            if not self.is_monitoring:
                QTimer.singleShot(500, self.start_monitoring)
        else:
            self.update_status(f"✗ {message}", error=True)
            self.show_notification("认证失败", message, QSystemTrayIcon.MessageIcon.Critical)

    def start_monitoring(self):
        """启动网络监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True

        self.monitor_thread = MonitorThread(check_interval=60)
        self.monitor_thread.status_update.connect(self.update_status)
        self.monitor_thread.auth_trigger.connect(self.handle_auth_trigger)
        self.monitor_thread.start()

        self.login_button.setText("监控中...")
        self.login_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_status("✓ 网络监控已启动")
        logger.info("网络监控已启动")

    def stop_monitoring(self):
        """停止网络监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            self.monitor_thread = None

        # 结束会话计时
        self.stats.end_session()

        self.login_button.setText("立即登录")
        self.login_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status("监控已停止")
        logger.info("网络监控已停止")

    def handle_auth_trigger(self):
        """处理监控线程触发的认证请求"""
        username = self.student_id_input.text().strip()
        password = self.password_input.text().strip()
        operator = self.get_selected_operator()

        if username and password:
            auth_thread = AuthThread(username, password, operator)
            auth_thread.finished.connect(self.on_monitor_auth_finished)
            auth_thread.finished.connect(auth_thread.deleteLater)
            auth_thread.start()
        else:
            self.update_status("✗ 认证信息不完整，无法重新认证", error=True)
            logger.warning("认证信息不完整")

    def on_monitor_auth_finished(self, success, message):
        """监控触发的认证完成"""
        self.stats.record_login(success, message)

        if success:
            self.update_status(f"✓ 重新认证成功: {message}")
            self.show_notification("重新认证成功", message, QSystemTrayIcon.MessageIcon.Information)
        else:
            self.update_status(f"✗ 重新认证失败: {message}")
            self.show_notification("重新认证失败", message, QSystemTrayIcon.MessageIcon.Critical)

    def show_notification(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information):
        """显示系统通知"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, 3000)

    def update_status(self, message, error=False):
        """更新状态"""
        self.status_label.setText(message)

        if error:
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #FF3B30;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #FFE5E5;
                }
            """)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #34C759;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #E5F5E5;
                }
            """)

    def setup_power_monitor(self):
        """设置电源监控"""
        try:
            self.power_monitor = get_power_monitor()
            self.power_monitor.system_resumed.connect(self.on_system_resumed)
            self.power_monitor.system_suspend.connect(self.on_system_suspend)
            self.power_monitor.start()
            logger.info("电源监控已启动")
        except Exception as e:
            logger.error(f"电源监控启动失败: {e}")

    def on_system_resumed(self):
        """系统唤醒事件处理"""
        self.update_status("系统唤醒，正在重新认证...")
        logger.info("检测到系统唤醒")

        username = self.student_id_input.text().strip()
        password = self.password_input.text().strip()
        operator = self.get_selected_operator()

        if username and password:
            auth_thread = AuthThread(username, password, operator)
            auth_thread.finished.connect(lambda s, m: self.update_status(
                f"✓ 唤醒后认证成功: {m}" if s else f"✗ 唤醒后认证失败: {m}",
                error=not s
            ))
            auth_thread.finished.connect(auth_thread.deleteLater)
            auth_thread.start()

        if self.is_monitoring and (not self.monitor_thread or not self.monitor_thread.isRunning()):
            self.is_monitoring = False
            self.start_monitoring()

    def on_system_suspend(self):
        """系统休眠事件处理"""
        self.update_status("系统休眠中...")
        logger.info("检测到系统休眠")

    def check_auto_start_status(self):
        """检查开机自启状态"""
        if not WINREG_AVAILABLE:
            self.auto_start_checkbox.setChecked(False)
            self.auto_start_checkbox.setEnabled(False)
            return

        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "校园网认证助手")
                self.auto_start_checkbox.setChecked(True)
            except FileNotFoundError:
                self.auto_start_checkbox.setChecked(False)
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"检查开机自启状态失败: {e}")
            self.auto_start_checkbox.setChecked(False)

    def on_auto_start_changed(self, checked):
        """开机自启选项改变"""
        if checked:
            self.enable_auto_start()
        else:
            self.disable_auto_start()

    def enable_auto_start(self):
        """启用开机自启"""
        if not WINREG_AVAILABLE:
            QMessageBox.warning(self, "不支持", "开机自启仅支持Windows系统")
            self.auto_start_checkbox.setChecked(False)
            return

        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(sys.argv[0])

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "校园网认证助手", 0, winreg.REG_SZ, f'"{exe_path}"')
            winreg.CloseKey(key)

            self.update_status("✓ 开机自启已启用")
            logger.info("开机自启已启用")

        except Exception as e:
            logger.error(f"设置开机自启失败: {e}")
            self.update_status(f"✗ 设置开机自启失败: {str(e)}", error=True)
            self.auto_start_checkbox.setChecked(False)
            QMessageBox.warning(
                self,
                "设置失败",
                f"无法设置开机自启:\n{str(e)}\n\n可能需要管理员权限"
            )

    def disable_auto_start(self):
        """禁用开机自启"""
        if not WINREG_AVAILABLE:
            return

        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            try:
                winreg.DeleteValue(key, "校园网认证助手")
                self.update_status("✓ 开机自启已禁用")
                logger.info("开机自启已禁用")
            except FileNotFoundError:
                pass
            finally:
                winreg.CloseKey(key)

        except Exception as e:
            logger.error(f"取消开机自启失败: {e}")
            self.update_status(f"✗ 取消开机自启失败: {str(e)}", error=True)
            QMessageBox.warning(
                self,
                "操作失败",
                f"无法取消开机自启:\n{str(e)}"
            )
