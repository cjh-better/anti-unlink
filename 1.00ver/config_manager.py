#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责配置文件的读写和密码加密
"""

import json
import base64
import os
import stat
from pathlib import Path
from typing import Dict, Optional


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            self.config_path = Path.home() / "campus_network_config.json"
        else:
            self.config_path = config_path

        self.config = {}

    def _obfuscate_password(self, password: str) -> str:
        """混淆密码（Base64编码，仅防止肉眼可见，并非真正加密）"""
        if not password:
            return ""
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')

    def _deobfuscate_password(self, encoded: str) -> str:
        """反混淆密码"""
        if not encoded:
            return ""
        try:
            return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        except Exception:
            return encoded

    # Keep old names as aliases for backward compatibility
    def encrypt_password(self, password: str) -> str:
        return self._obfuscate_password(password)

    def decrypt_password(self, encrypted: str) -> str:
        return self._deobfuscate_password(encrypted)

    def load(self) -> Dict:
        """加载配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)

                # 解密密码
                if 'password' in self.config:
                    self.config['password'] = self.decrypt_password(self.config['password'])

                # 加载账号列表
                if 'accounts' in self.config:
                    for account in self.config['accounts']:
                        if 'password' in account:
                            account['password'] = self.decrypt_password(account['password'])

                return self.config
        except Exception as e:
            print(f"加载配置失败: {e}")

        return {}

    def save(self, config: Dict) -> bool:
        """保存配置"""
        try:
            # 复制配置以避免修改原始数据
            save_config = config.copy()

            # 加密主账号密码
            if 'password' in save_config:
                save_config['password'] = self.encrypt_password(save_config['password'])

            # 加密账号列表中的密码
            if 'accounts' in save_config:
                accounts_copy = []
                for account in save_config['accounts']:
                    account_copy = account.copy()
                    if 'password' in account_copy:
                        account_copy['password'] = self.encrypt_password(account_copy['password'])
                    accounts_copy.append(account_copy)
                save_config['accounts'] = accounts_copy

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, ensure_ascii=False, indent=2)

            # Restrict file permissions to owner-only (cross-platform best-effort)
            try:
                self.config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass

            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def add_account(self, username: str, password: str, operator: str, name: str = None) -> bool:
        """添加账号到列表"""
        if 'accounts' not in self.config:
            self.config['accounts'] = []

        # 检查是否已存在
        for account in self.config['accounts']:
            if account.get('username') == username and account.get('operator') == operator:
                # 更新密码
                account['password'] = password
                if name:
                    account['name'] = name
                return True

        # 添加新账号
        account = {
            'username': username,
            'password': password,
            'operator': operator,
            'name': name or f"{username}{operator}"
        }
        self.config['accounts'].append(account)
        return True

    def get_accounts(self) -> list:
        """获取所有账号"""
        return self.config.get('accounts', [])

    def remove_account(self, index: int) -> bool:
        """删除账号"""
        try:
            if 'accounts' in self.config and 0 <= index < len(self.config['accounts']):
                self.config['accounts'].pop(index)
                return True
        except Exception:
            pass
        return False
