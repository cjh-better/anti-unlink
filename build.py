#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
校园网认证工具 - 打包脚本
自动打包程序并生成release版本
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

# 配置
APP_NAME = "校园网认证工具"
VERSION = "1.00"
BUILD_DIR = "build"
DIST_DIR = "dist"
RELEASE_DIR = "release"
SPEC_FILE = "1.00ver/校园网认证工具_pyside6.spec"

def print_step(step_name):
    """打印步骤信息"""
    print("\n" + "="*60)
    print(f"  {step_name}")
    print("="*60)

def clean_dirs():
    """清理旧的构建文件"""
    print_step("清理旧的构建文件")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"删除目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    print("[OK] 清理完成")

def check_dependencies():
    """检查必要的依赖"""
    print_step("检查依赖")
    
    try:
        import PyInstaller
        print(f"[OK] PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] 未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        return False
    
    # 检查其他依赖
    dependencies = [
        'tkinter',
        'PIL',
        'requests',
        'pystray',
        'maliang',
    ]
    
    missing = []
    for dep in dependencies:
        try:
            if dep == 'tkinter':
                import tkinter
            elif dep == 'PIL':
                import PIL
            elif dep == 'requests':
                import requests
            elif dep == 'pystray':
                import pystray
            elif dep == 'maliang':
                import maliang
            print(f"[OK] {dep}: 已安装")
        except ImportError:
            print(f"[ERROR] {dep}: 未安装")
            missing.append(dep)
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("请先安装所有依赖！")
        return False
    
    return True

def build_exe():
    """使用PyInstaller打包"""
    print_step("开始打包程序")
    
    if not os.path.exists(SPEC_FILE):
        print(f"[ERROR] 未找到配置文件: {SPEC_FILE}")
        return False
    
    print(f"使用配置文件: {SPEC_FILE}")
    print("正在打包... 这可能需要几分钟时间")
    
    try:
        result = subprocess.run(
            ['pyinstaller', '--clean', SPEC_FILE],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("[OK] 打包成功")
            return True
        else:
            print("[ERROR] 打包失败")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"[ERROR] 打包过程出错: {e}")
        return False

def create_release():
    """创建release版本"""
    print_step("创建Release版本")
    
    # 创建release目录
    if not os.path.exists(RELEASE_DIR):
        os.makedirs(RELEASE_DIR)
        print(f"[OK] 创建目录: {RELEASE_DIR}")
    
    # 查找生成的exe文件
    exe_name = f"{APP_NAME}.exe"
    exe_path = os.path.join(DIST_DIR, exe_name)
    
    if not os.path.exists(exe_path):
        print(f"[ERROR] 未找到生成的exe文件: {exe_path}")
        return False
    
    # 直接复制到release目录（覆盖旧版本）
    release_exe = os.path.join(RELEASE_DIR, exe_name)
    shutil.copy2(exe_path, release_exe)
    print(f"[OK] 复制程序到: {RELEASE_DIR}/{exe_name}")
    
    # 不复制说明文档（按用户要求）
    print("[INFO] 跳过文档复制")
    
    print(f"\n[SUCCESS] Release创建成功！")
    print(f"   程序位置: {RELEASE_DIR}/{exe_name}")
    
    return True

def print_summary():
    """打印构建总结"""
    print_step("构建完成")
    print(f"程序名称: {APP_NAME}")
    print(f"版本号: {VERSION}")
    print(f"输出目录: {RELEASE_DIR}/")
    print("\n可执行文件:")
    print(f"  - {RELEASE_DIR}/{APP_NAME}.exe")
    print("\n使用方法:")
    print("  1. 进入release文件夹")
    print(f"  2. 双击运行 {APP_NAME}.exe")
    print("  3. 查看README.txt了解详细使用方法")
    print("\n" + "="*60)

def main():
    """主函数"""
    print("\n" + "="*60)
    print(f"  {APP_NAME} - 打包工具")
    print(f"  版本: {VERSION}")
    print("="*60)
    
    # 检查依赖
    if not check_dependencies():
        print("\n[ERROR] 依赖检查失败，请先安装所有依赖")
        return 1
    
    # 清理旧文件
    clean_dirs()
    
    # 打包程序
    if not build_exe():
        print("\n[ERROR] 打包失败")
        return 1
    
    # 创建release
    if not create_release():
        print("\n[ERROR] 创建Release失败")
        return 1
    
    # 打印总结
    print_summary()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

