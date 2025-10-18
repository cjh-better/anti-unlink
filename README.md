# 校园网认证助手 (Anti-Unlink)

基于深澜Srun加密认证的校园网自动认证工具，适配江西科技师范大学，支持断网自动重连和电源唤醒自动认证。
如果你喜欢我的项目，请给我点个星星吧
如果有问题请联系我：1023584005@qq.com

## ✨ 版本信息

- **当前版本**: v1.0
- **发布日期**: 2025-10-18
- **状态**: ✅ 稳定版

## 🚀 快速开始

### 下载运行

1. 进入 `release` 目录
2. 双击运行 `校园网认证助手_v1.0.exe` 或 `校园网认证助手_v1.0_正式版.pkg`
3. 输入账号密码，选择运营商
4. 点击"立即登录"

### 系统要求

- Windows 7/8/10/11
- 已连接到校园网WiFi
- 无需安装Python或其他依赖

## 📦 项目结构

```
anti-unlink/
├── 1.00ver/                         # 源代码目录
│   ├── main_campus.py               # 主程序入口
│   ├── ui_campus.py                 # UI界面模块
│   ├── srun_encrypted.py            # 深澜加密认证模块
│   ├── network.py                   # 网络工具（支持跨平台）
│   ├── power_monitor.py             # 电源监控模块
│   ├── 校园网认证工具_新版.spec      # PyInstaller打包配置
│   ├── 打包到release.bat            # 打包到release脚本
│   ├── 打包程序.bat                 # 普通打包脚本
│   ├── 重新打包.bat                 # 重新打包脚本
│   ├── image.ico                    # 程序图标
│   └── 11409B.png                   # 资源图片
│
├── release/                         # 发布版本
│   ├── 校园网认证助手_v1.0.exe       # Windows可执行文件
│   ├── 校园网认证助手_v1.0_正式版.pkg # 打包版本
│   └── config.json                  # 配置文件示例
│
├── docs/                            # 文档目录
│   └── README.md                    # 详细使用说明
│
├── build.py                         # 构建脚本
├── requirements.txt                 # Python依赖列表
├── 11409B.png                       # 资源图片
└── README.md                        # 项目说明文档
```

## 🔧 核心功能

### 认证功能
- ✅ 深澜Srun加密认证算法
- ✅ 支持电信/移动/联通/办公运营商
- ✅ 自动保存账号密码
- ✅ 启动时自动登录

### 监控功能
- ✅ 60秒间隔网络状态检测
- ✅ 断网自动重连
- ✅ 电源唤醒自动认证
- ✅ 实时状态显示

### UI设计
- ✅ 简洁的iOS风格界面
- ✅ 清晰的状态提示
- ✅ 友好的错误信息

## 📖 使用文档

详细使用说明请查看 [docs/README.md](docs/README.md)

## 🛠️ 开发说明

### 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 或手动安装核心依赖
pip install pyinstaller PySide6 requests
```

### 运行源码
```bash
cd 1.00ver
python main_campus.py
```

### 打包程序
```bash
cd 1.00ver

# 方法1: 使用批处理脚本（推荐）
打包到release.bat

# 方法2: 使用spec文件
pyinstaller 校园网认证工具_新版.spec

# 方法3: 使用其他打包脚本
打包程序.bat
重新打包.bat
```

## 🔐 安全说明

- ✅ 密码加密存储在本地配置文件
- ✅ 仅本地认证，不上传任何信息
- ✅ 使用官方深澜认证协议
- ⚠️ 配置文件包含密码，请妥善保管
- ⚠️ 不要在公共电脑上勾选"自动登录"

## 🙏 致谢

感谢以下开源项目：
- [UCAS-srun-login-script](https://github.com/Yurzi/UCAS-srun-login-script) - 深澜认证算法参考
- [SRunPy-GUI](https://github.com/Mm7/SRunPy-GUI) - 深澜加密算法实现
- [PySide6](https://www.qt.io/qt-for-python) - Qt Python绑定

## 📝 更新日志

### v1.0 (2025-10-18)
- [功能] 深澜Srun加密认证
- [功能] 支持多运营商选择
- [功能] 断网自动重连
- [功能] 电源唤醒自动认证
- [优化] iOS风格UI界面
- [优化] 跨平台支持（Windows/Linux/WSL）

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业用途。

---

**最后更新**: 2025-10-18
**版本**: v1.0
