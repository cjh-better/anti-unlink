#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络统计模块
记录认证历史、在线时长、成功率等
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List


class NetworkStats:
    """网络统计管理器"""

    def __init__(self):
        self.stats_path = Path.home() / ".campus_network" / "stats.json"
        self.stats_path.parent.mkdir(exist_ok=True)
        self.stats = self.load_stats()
        self.session_start_time = None
        self.total_online_time = self.stats.get('total_online_time', 0)

    def load_stats(self) -> Dict:
        """加载统计数据"""
        try:
            if self.stats_path.exists():
                with open(self.stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载统计数据失败: {e}")

        return {
            'total_logins': 0,
            'success_logins': 0,
            'failed_logins': 0,
            'total_online_time': 0,
            'last_login_time': None,
            'history': []
        }

    def save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存统计数据失败: {e}")

    def record_login(self, success: bool, message: str = ""):
        """记录一次登录尝试"""
        self.stats['total_logins'] += 1

        if success:
            self.stats['success_logins'] += 1
        else:
            self.stats['failed_logins'] += 1

        # 记录到历史
        history_item = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': success,
            'message': message
        }

        if 'history' not in self.stats:
            self.stats['history'] = []

        self.stats['history'].append(history_item)

        # 只保留最近100条记录
        if len(self.stats['history']) > 100:
            self.stats['history'] = self.stats['history'][-100:]

        self.stats['last_login_time'] = history_item['time']
        self.save_stats()

    def start_session(self):
        """开始在线会话"""
        self.session_start_time = time.time()

    def end_session(self):
        """结束在线会话"""
        if self.session_start_time:
            duration = time.time() - self.session_start_time
            self.stats['total_online_time'] += duration
            self.total_online_time = self.stats['total_online_time']
            self.save_stats()
            self.session_start_time = None

    def get_current_session_time(self) -> int:
        """获取当前会话时长（秒）"""
        if self.session_start_time:
            return int(time.time() - self.session_start_time)
        return 0

    def get_total_online_time(self) -> int:
        """获取总在线时长（秒）"""
        return int(self.total_online_time)

    def get_success_rate(self) -> float:
        """获取认证成功率"""
        total = self.stats['total_logins']
        if total == 0:
            return 0.0
        return (self.stats['success_logins'] / total) * 100

    def get_recent_history(self, count: int = 10) -> List[Dict]:
        """获取最近的认证历史"""
        history = self.stats.get('history', [])
        return history[-count:] if len(history) > count else history

    def format_time(self, seconds: int) -> str:
        """格式化时间"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟{secs}秒"
        else:
            return f"{secs}秒"

    def get_stats_summary(self) -> str:
        """获取统计摘要"""
        total_time = self.get_total_online_time() + self.get_current_session_time()
        success_rate = self.get_success_rate()

        summary = f"总认证: {self.stats['total_logins']}次 | "
        summary += f"成功: {self.stats['success_logins']}次 | "
        summary += f"失败: {self.stats['failed_logins']}次\n"
        summary += f"成功率: {success_rate:.1f}% | "
        summary += f"总在线: {self.format_time(total_time)}"

        return summary
