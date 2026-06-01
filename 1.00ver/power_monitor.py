#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows电源事件监控模块
用于检测系统休眠/唤醒事件
参考1.0.5ver的pump_thread.py实现
"""

import win32gui
import win32con
import win32api
import threading
from PySide6.QtCore import QObject, Signal


class PowerEventMonitor(QObject):
    """
    Windows电源事件监控器
    使用独立的消息循环线程监听电源广播事件
    """
    # 定义信号
    system_resumed = Signal()  # 系统唤醒信号
    system_suspend = Signal()  # 系统休眠信号

    def __init__(self):
        super().__init__()
        self.hwnd = None
        self.pump_thread = None
        self.running = False

    def start(self):
        """启动电源监控"""
        if self.running:
            return

        self.running = True

        # 创建隐藏消息窗口
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._power_event_handler
            wc.lpszClassName = "PowerMonitorClass_Qt"

            try:
                class_atom = win32gui.RegisterClass(wc)
            except win32gui.error as e:
                if e.winerror != 1410:  # 忽略类已存在的错误
                    raise

            # 创建窗口实例
            self.hwnd = win32gui.CreateWindowEx(
                0,  # dwExStyle
                wc.lpszClassName,
                "PowerMonitor",
                0,  # dwStyle
                0, 0, 0, 0,  # x, y, width, height
                None,
                None,
                wc.hInstance,
                None
            )

            # 启动独立消息循环线程
            self.pump_thread = threading.Thread(
                target=self._message_pump,
                daemon=True,
                name="PowerMonitorThread"
            )
            self.pump_thread.start()

            print("电源监控已启动")

        except Exception as e:
            print(f"启动电源监控失败: {e}")
            self.running = False

    def stop(self):
        """停止电源监控"""
        self.running = False

        if self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)
                win32gui.DestroyWindow(self.hwnd)
            except Exception:
                pass
            self.hwnd = None

        if self.pump_thread and self.pump_thread.is_alive():
            self.pump_thread.join(timeout=2)

        print("电源监控已停止")

    def _message_pump(self):
        """独立消息循环线程"""
        try:
            while self.running:
                win32gui.PumpMessages()
        except Exception as e:
            print(f"消息循环异常: {e}")
        finally:
            print("消息循环线程已退出")

    def _power_event_handler(self, hwnd, msg, wparam, lparam):
        """
        电源事件处理回调
        参考1.0.5ver/pump_thread.py:51
        """
        if msg == win32con.WM_POWERBROADCAST:
            if wparam == win32con.PBT_APMRESUMEAUTOMATIC:
                print("检测到系统唤醒事件")
                # 发射唤醒信号
                self.system_resumed.emit()

            elif wparam == win32con.PBT_APMSUSPEND:
                print("检测到系统休眠事件")
                # 发射休眠信号
                self.system_suspend.emit()

        return 0  # 必须返回0


# 单例模式
_power_monitor_instance = None


def get_power_monitor():
    """获取电源监控器单例"""
    global _power_monitor_instance
    if _power_monitor_instance is None:
        _power_monitor_instance = PowerEventMonitor()
    return _power_monitor_instance
