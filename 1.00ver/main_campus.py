#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校园网认证助手 - 主程序
Clean and Simple Campus Network Authentication Tool
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui_campus import CampusNetworkWindow

def main():
    """主函数"""
    # 启用高DPI支持 (Qt 6默认启用,无需显式设置AA_EnableHighDpiScaling和AA_UseHighDpiPixmaps)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("校园网认证助手")

    # 创建主窗口
    window = CampusNetworkWindow()
    window.show()

    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
