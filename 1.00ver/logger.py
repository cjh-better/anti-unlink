#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的日志记录功能
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


class LogManager:
    """日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 日志文件路径
        log_dir = Path.home() / ".campus_network"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "campus_auth.log"

        # 创建logger
        self.logger = logging.getLogger('CampusAuth')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件处理器（带轮转，最大10MB，保留3个备份）
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,
                backupCount=3,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)

            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        self._initialized = True

    def info(self, message):
        """记录信息"""
        self.logger.info(message)

    def warning(self, message):
        """记录警告"""
        self.logger.warning(message)

    def error(self, message):
        """记录错误"""
        self.logger.error(message)

    def debug(self, message):
        """记录调试信息"""
        self.logger.debug(message)


# 全局日志实例
logger = LogManager()
