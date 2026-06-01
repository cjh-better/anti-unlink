import subprocess
import requests
import random
import requests.exceptions
import re
import time
import platform
import socket
import sys
from logger import logger

# Windows-only imports
try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

# Windows下的常量定义
if platform.system() == "Windows":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

_IS_WINDOWS = platform.system() == "Windows"


def _subprocess_kwargs():
    """Return platform-appropriate subprocess kwargs."""
    kwargs = {}
    if _IS_WINDOWS:
        kwargs['creationflags'] = CREATE_NO_WINDOW
    return kwargs

def check_location_permission():
    """检测Windows位置权限是否已启用

    返回:
        True: 位置权限已启用
        False: 位置权限未启用
        None: 无法检测
    """
    if not _IS_WINDOWS or not WINREG_AVAILABLE:
        return None

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "Value")
            winreg.CloseKey(key)
            return value == "Allow"
        except FileNotFoundError:
            return False
    except Exception as e:
        logger.error(f"检测位置权限失败: {e}")
        return None

def enable_wifi_adapter():
    """启用WiFi适配器

    返回:
        True: 成功启用
        False: 启用失败
    """
    if not _IS_WINDOWS:
        return False

    try:
        cmd = 'netsh interface set interface name="WLAN" admin=enabled'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **_subprocess_kwargs())

        if result.returncode == 0:
            time.sleep(2)
            return True
        else:
            for interface_name in ["无线网络连接", "Wi-Fi", "Wireless Network Connection"]:
                cmd = f'netsh interface set interface name="{interface_name}" admin=enabled'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **_subprocess_kwargs())
                if result.returncode == 0:
                    time.sleep(2)
                    return True

            return False
    except Exception as e:
        logger.error(f"启用WiFi适配器失败: {e}")
        return False

def check_wifi_adapter_status():
    """检查WiFi适配器状态

    返回:
        'connected': WiFi已连接
        'disconnected': WiFi适配器已启用但未连接
        'disabled': WiFi适配器已禁用
        None: 无法检测或无WiFi适配器
    """
    if not _IS_WINDOWS:
        return None

    try:
        cmd = 'netsh wlan show interfaces'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, **_subprocess_kwargs()).decode('utf-8')

        for line in result.split('\n'):
            if '状态' in line or 'State' in line:
                if '已连接' in line or 'connected' in line.lower():
                    return 'connected'
                elif '已断开' in line or 'disconnected' in line.lower():
                    return 'disconnected'

        return 'disconnected'
    except subprocess.CalledProcessError:
        return 'disabled'
    except Exception:
        return None

def open_wifi_settings():
    """打开Windows WiFi设置页面

    返回:
        True: 成功打开设置页面
        False: 打开失败
    """
    if platform.system() != "Windows":
        return False

    try:
        # 使用Windows URI打开WiFi设置
        subprocess.Popen(['start', 'ms-settings:network-wifi'], shell=True)
        return True
    except Exception as e:
        return False

def open_location_settings():
    """打开Windows位置设置页面

    返回:
        True: 成功打开设置页面
        False: 打开失败
    """
    if platform.system() != "Windows":
        return False

    try:
        # 使用Windows URI打开位置设置
        subprocess.Popen(['start', 'ms-settings:privacy-location'], shell=True)
        return True
    except Exception as e:
        return False

def get_current_ip():  # 返回ip值（优先WiFi，其次以太网）
    """获取当前网络的IP地址，优先返回WiFi的IP，如果没有WiFi则返回以太网IP"""

    # 检测操作系统
    system = platform.system()

    if system == "Linux":
        # Linux/WSL环境 - 使用 ip addr 命令
        try:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            lines = result.stdout.split('\n')

            # 优先查找 wlan/wlp 接口 (WiFi)
            for i, line in enumerate(lines):
                if 'wlan' in line or 'wlp' in line:
                    # 在接下来的几行中查找 inet 地址
                    for j in range(i, min(i+10, len(lines))):
                        if 'inet ' in lines[j] and 'inet6' not in lines[j]:
                            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', lines[j])
                            if match:
                                ip = match.group(1)
                                if not ip.startswith('127.'):
                                    return ip

            # 如果没有WiFi，查找 eth/enp 接口 (以太网)
            for i, line in enumerate(lines):
                if 'eth' in line or 'enp' in line:
                    # 在接下来的几行中查找 inet 地址
                    for j in range(i, min(i+10, len(lines))):
                        if 'inet ' in lines[j] and 'inet6' not in lines[j]:
                            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', lines[j])
                            if match:
                                ip = match.group(1)
                                if not ip.startswith('127.') and not ip.startswith('169.254'):
                                    return ip

            # 如果仍未找到，尝试获取任何非回环地址
            for line in lines:
                if 'inet ' in line and 'inet6' not in line and '127.0.0.1' not in line:
                    match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip = match.group(1)
                        if not ip.startswith('127.') and not ip.startswith('169.254'):
                            return ip

        except Exception as e:
            return None

    else:
        # Windows环境
        cmd = "ipconfig"
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            # WSL环境下尝试使用 ipconfig.exe
            try:
                result = subprocess.run("ipconfig.exe", capture_output=True, text=True, encoding='gbk')
            except:
                return None

        # 首先尝试获取WiFi的IP
        searched_wlan = 0
        for line in result.stdout.split('\n'):
            if "无线局域网适配器 WLAN" in line or "Wireless LAN adapter WLAN" in line or "Wireless LAN adapter Wi-Fi" in line:
                searched_wlan = 1
            if searched_wlan:
                if "IPv4 地址" in line or "IPv4 Address" in line:
                    return line.split(":")[1].strip()
                # 如果遇到下一个适配器，停止搜索
                if searched_wlan and "适配器" in line and "无线局域网" not in line:
                    break

        # 如果没有WiFi IP，尝试获取以太网IP
        searched_ethernet = 0
        for line in result.stdout.split('\n'):
            if "以太网适配器" in line or "Ethernet adapter" in line:
                searched_ethernet = 1
            if searched_ethernet:
                if "IPv4 地址" in line or "IPv4 Address" in line:
                    ip = line.split(":")[1].strip()
                    # 过滤掉虚拟适配器的IP
                    if not ip.startswith("169.254"):  # 排除自动分配的IP
                        return ip
                # 如果遇到下一个适配器，停止搜索
                if searched_ethernet and "适配器" in line and "以太网" not in line:
                    searched_ethernet = 0

    return None

def get_connection_type():
    """检测当前连接类型：'wifi', 'ethernet', 'none'"""
    if not _IS_WINDOWS:
        ip = get_current_ip()
        return 'ethernet' if ip else 'none'

    cmd = "ipconfig"
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 检查WiFi连接
    wifi_connected = False
    ethernet_connected = False

    lines = result.stdout.split('\n')
    current_adapter = None

    for i, line in enumerate(lines):
        if "无线局域网适配器" in line or "Wireless LAN adapter" in line:
            # 检查是否是虚拟WiFi适配器
            if "本地连接*" in line or "Local Area Connection*" in line:
                current_adapter = None
            else:
                current_adapter = 'wifi'
        elif "以太网适配器" in line or "Ethernet adapter" in line:
            # 排除虚拟适配器
            if "vEthernet" in line or "VMware" in line or "VirtualBox" in line or "蓝牙" in line or "Bluetooth" in line:
                current_adapter = None
            else:
                current_adapter = 'ethernet'
        elif "适配器" in line or "adapter" in line:
            # 遇到新的适配器,清除当前状态
            current_adapter = None

        if current_adapter and ("IPv4 地址" in line or "IPv4 Address" in line):
            ip = line.split(":")[1].strip()
            if not ip.startswith("169.254"):  # 排除自动分配的IP
                if current_adapter == 'wifi':
                    wifi_connected = True
                elif current_adapter == 'ethernet':
                    ethernet_connected = True

    # 如果检测到WiFi,再次确认真的有WiFi连接
    if wifi_connected:
        wifi_ssid = get_connected_wifi()
        if wifi_ssid:
            return 'wifi'
        else:
            wifi_connected = False

    if ethernet_connected:
        return 'ethernet'
    else:
        return 'none'

def connect_to_wifi(ssid):  # 连接无密码网络
    if not _IS_WINDOWS:
        return False

    wlan = get_connected_wifi()

    if wlan != ssid:
        disconnect_result = subprocess.call(["netsh", "wlan", "disconnect"])
        if disconnect_result != 0:
            pass
        connect_result = subprocess.call(["netsh", "wlan", "connect", "name=" + ssid])
        if connect_result != 0:
            return False

    return True

def scan_open_wifi():
    """扫描所有开放的WiFi网络，返回信号最强的开放网络SSID

    注意: Windows 11需要位置权限才能扫描WiFi
    如果扫描失败,建议用户手动连接WiFi后再运行程序

    返回:
        str: WiFi SSID名称
        None: 扫描失败
        'PERMISSION_DENIED': 需要位置权限
        'WIFI_DISABLED': WiFi适配器未启用或断开
    """
    if not _IS_WINDOWS:
        return None

    # 首先检查WiFi适配器状态
    wifi_status = check_wifi_adapter_status()

    if wifi_status == 'disabled':
        if not enable_wifi_adapter():
            return 'WIFI_DISABLED'
        # 重新检查状态
        wifi_status = check_wifi_adapter_status()

    if wifi_status == 'disconnected':
        # 尝试启用WiFi适配器(即使显示已启用,重新启用可能会激活它)
        enable_wifi_adapter()
        # 继续扫描
    elif wifi_status == 'connected':
        # 如果已经连接了WiFi,就不需要扫描了
        connected_wifi = get_connected_wifi()
        if connected_wifi:
            return connected_wifi

    # 检查位置权限
    location_enabled = check_location_permission()
    if location_enabled == False:
        return 'PERMISSION_DENIED'
    elif location_enabled != True:
        pass  # 无法检测位置权限状态,继续尝试扫描

    cmd = 'netsh wlan show networks mode=bssid'

    result = None
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, **_subprocess_kwargs()).decode('gbk')
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode('gbk', errors='ignore') if e.output else ""
        if "位置" in error_msg or "permission" in error_msg.lower() or "拒绝访问" in error_msg:
            return 'PERMISSION_DENIED'
        else:
            return 'WIFI_DISABLED'
    except Exception as e:
        try:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, **_subprocess_kwargs()).decode('utf-8')
        except Exception as e2:
            return 'WIFI_DISABLED'

    if not result:
        return 'WIFI_DISABLED'

    networks = []
    current_ssid = None
    current_signal = 0
    current_auth = None

    for line in result.split('\n'):
        line = line.strip()

        # 提取SSID
        if 'SSID' in line and ':' in line:
            parts = line.split(':', 1)
            if len(parts) > 1:
                ssid = parts[1].strip()
                if ssid and 'BSSID' not in line:  # 排除包含BSSID的行
                    current_ssid = ssid

        # 提取认证类型
        if '身份验证' in line or 'Authentication' in line:
            current_auth = line.split(':')[-1].strip()

        # 提取信号强度
        if '信号' in line or 'Signal' in line:
            signal_str = line.split(':')[-1].strip().replace('%', '')
            try:
                current_signal = int(signal_str)
            except:
                current_signal = 0

            # 如果是开放网络（无密码），添加到列表
            if current_ssid and current_auth:
                auth_lower = current_auth.lower()
                is_open = '开放' in auth_lower or 'open' in auth_lower

                if is_open:
                    networks.append({
                        'ssid': current_ssid,
                        'signal': current_signal,
                        'auth': current_auth
                    })

    # 按信号强度排序，返回最强的
    if networks:
        networks.sort(key=lambda x: x['signal'], reverse=True)
        best_network = networks[0]
        return best_network['ssid']
    else:
        return None

def get_connected_wifi():
    """获取当前连接的WiFi名称。返回SSID字符串或None"""
    if not _IS_WINDOWS:
        return None

    cmd = 'netsh wlan show interfaces'
    try:
        result = subprocess.check_output(cmd, shell=True, **_subprocess_kwargs()).decode('utf-8')
    except subprocess.CalledProcessError:
        return None
    except Exception:
        try:
            result = subprocess.check_output(cmd, shell=True, **_subprocess_kwargs()).decode('gbk')
        except Exception:
            return None

    try:
        for line in result.split('\n'):
            if 'SSID' in line and 'BSSID' not in line:
                ssid = line.split(':')[-1].strip()
                if ssid:
                    return ssid
    except Exception:
        pass

    return None

def connect_to_best_open_wifi():
    """自动连接信号最强的开放WiFi"""
    best_ssid = scan_open_wifi()
    if best_ssid:
        return connect_to_wifi(best_ssid)
    return False


def network_check(timeout=3):
    """Check internet connectivity by requesting a random URL from the pool."""
    net_list = ["https://daohang.qq.com/", "https://www.sogou.com", "https://cn.bing.com", "https://www.msn.cn"]
    net = random.choice(net_list)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    try:
        resp = requests.get(net, timeout=timeout, headers=headers)
        return resp.status_code == 200
    except ConnectionResetError:
        return True
    except requests.exceptions.RequestException:
        return False
