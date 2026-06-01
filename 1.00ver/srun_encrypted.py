# -*- coding: utf-8 -*-
"""
深澜Srun加密认证模块
支持复杂的加密认证（chksum, info等参数）
参考: SRunPy-GUI-main 和 SRun-Auth-main 项目
"""
import hashlib
import json
import logging
import time
import hmac
import base64
import requests
import re
import math

logger = logging.getLogger('CampusAuth')


def get_md5(password):
    """MD5加密密码"""
    return hashlib.md5(password.encode()).hexdigest()


def get_hmac_md5(password, key):
    """HMAC-MD5加密（用于password参数）"""
    return hmac.new(key.encode(), password.encode(), hashlib.md5).hexdigest()


def get_sha1(value):
    """SHA1加密"""
    return hashlib.sha1(value.encode()).hexdigest()


def ordat(msg, idx):
    """获取索引处的字符代码，越界返回0"""
    if len(msg) > idx:
        return ord(msg[idx])
    return 0


def sencode(msg, key):
    """将字符串编码为整数数组（深澜编码算法）"""
    l = len(msg)
    pwd = []
    for i in range(0, l, 4):
        pwd.append(
            ordat(msg, i) | ordat(msg, i + 1) << 8 | ordat(msg, i + 2) << 16
            | ordat(msg, i + 3) << 24)
    if key:
        pwd.append(l)
    return pwd


def lencode(msg, key):
    """将整数数组转换回字符串（深澜解码算法）"""
    l = len(msg)
    ll = (l - 1) << 2
    if key:
        m = msg[l - 1]
        if m < ll - 3 or m > ll:
            return None
        ll = m
    for i in range(0, l):
        msg[i] = chr(msg[i] & 0xff) + chr(msg[i] >> 8 & 0xff) + chr(
            msg[i] >> 16 & 0xff) + chr(msg[i] >> 24 & 0xff)
    if key:
        return "".join(msg)[0:ll]
    return "".join(msg)


def xEncode(msg, key):
    """
    深澜XEncode加密算法 - 参考SRunPy-GUI实现
    使用TEA加密的变体，带有自定义常量
    """
    if msg == "":
        return ""

    pwd = sencode(msg, True)
    pwdk = sencode(key, False)

    if len(pwdk) < 4:
        pwdk = pwdk + [0] * (4 - len(pwdk))

    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    m = 0
    e = 0
    p = 0
    q = math.floor(6 + 52 / (n + 1))
    d = 0

    while 0 < q:
        d = d + c & (0x8CE0D9BF | 0x731F2640)
        e = d >> 2 & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = z >> 5 ^ y << 2
            m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = pwd[p] + m & (0xEFB8D130 | 0x10472ECF)
            z = pwd[p]
            p = p + 1
        y = pwd[0]
        m = z >> 5 ^ y << 2
        m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[n] = pwd[n] + m & (0xBB390742 | 0x44C6F8BD)
        z = pwd[n]
        q = q - 1

    return lencode(pwd, False)


def srun_base64_encode(s):
    """深澜Srun的Base64编码 - 参考SRunPy-GUI实现"""
    _ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"

    r = []
    x = len(s) % 3
    if x:
        s = s + '\0' * (3 - x)

    for i in range(0, len(s), 3):
        d = s[i:i + 3]
        a = ord(d[0]) << 16 | ord(d[1]) << 8 | ord(d[2])
        r.append(_ALPHA[a >> 18])
        r.append(_ALPHA[a >> 12 & 63])
        r.append(_ALPHA[a >> 6 & 63])
        r.append(_ALPHA[a & 63])

    if x == 1:
        r[-1] = '='
        r[-2] = '='
    if x == 2:
        r[-1] = '='

    return ''.join(r)


def get_info(username, password, ip, ac_id, token):
    """生成info参数（加密信息）- 参考SRunPy-GUI实现"""
    info_dict = {
        "username": username,
        "password": password,
        "ip": ip,
        "acid": str(ac_id),
        "enc_ver": "srun_bx1"
    }

    i = json.dumps(info_dict, separators=(',', ':'))

    # 使用token作为key进行xEncode
    encoded = xEncode(i, token)

    # 使用深澜的Base64编码
    info = "{SRBX1}" + srun_base64_encode(encoded)

    return info


def get_chksum(username, password, ip, ac_id, info_param, challenge=""):
    """
    计算chksum（校验和）
    注意：某些学校的Srun系统，chksum中的info使用的是原始JSON字符串，而不是加密后的
    """
    # 先尝试使用加密后的info（当前方法）
    chkstr = challenge  # challenge放在最前面
    chkstr += username
    chkstr += password
    chkstr += str(ac_id)
    chkstr += ip
    chkstr += "200"  # n参数
    chkstr += "1"    # type参数
    chkstr += info_param

    return get_sha1(chkstr)


def get_chksum_with_raw_info(username, password, ip, ac_id, challenge=""):
    """
    计算chksum（使用原始info JSON）
    某些学校的实现中，chksum使用未加密的info JSON字符串
    """
    # 生成原始info JSON
    info_dict = {
        "username": username,
        "password": password,
        "ip": ip,
        "acid": str(ac_id),
        "enc_ver": "srun_bx1"
    }
    raw_info = json.dumps(info_dict, separators=(',', ':'))

    chkstr = challenge
    chkstr += username
    chkstr += password
    chkstr += str(ac_id)
    chkstr += ip
    chkstr += "200"
    chkstr += "1"
    chkstr += "{SRBX1}" + raw_info  # 使用{SRBX1}前缀 + 原始JSON

    return get_sha1(chkstr)


class SrunEncryptedAuth:
    """深澜Srun加密认证类"""

    def __init__(self, portal_url="http://172.18.7.1/cgi-bin/srun_portal"):
        self.portal_url = portal_url
        self.session = requests.Session()
        # 禁用代理,避免内网地址走代理导致超时
        self.session.proxies = {
            'http': None,
            'https': None
        }
        self.session.trust_env = False  # 不使用环境变量中的代理设置

    def get_challenge(self, username, ip):
        """
        获取challenge值
        :param username: 完整用户名
        :param ip: 用户IP
        :return: challenge值，失败返回None
        """
        try:
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{str(timestamp)[:13]}_{timestamp}"

            params = {
                "callback": callback,
                "username": username,
                "ip": ip,
                "_": str(timestamp)
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*'
            }

            # 获取challenge的URL（通常是 /cgi-bin/get_challenge）
            challenge_url = self.portal_url.replace('/srun_portal', '/get_challenge')

            logger.debug(f"[获取Challenge] URL: {challenge_url}")

            response = self.session.get(
                challenge_url,
                params=params,
                headers=headers,
                timeout=5
            )

            logger.debug(f"[获取Challenge] 响应: {response.text[:200]}")

            # 解析JSONP响应
            match = re.search(r'jQuery\w+\((.*)\)', response.text)
            if match:
                data = json.loads(match.group(1))
                challenge = data.get('challenge')
                if challenge:
                    logger.debug(f"[获取Challenge] 成功")
                    return challenge

            logger.warning("[获取Challenge] 失败: 未找到challenge")
            return None

        except Exception as e:
            logger.error(f"[获取Challenge] 异常: {e}")
            return None

    def login(self, username, password, ip, ac_id=1):
        """
        执行加密登录 - 参考SRun-Auth-main项目实现
        :param username: 完整用户名（例如：20241654@chinanet）
        :param password: 明文密码
        :param ip: 用户IP地址
        :param ac_id: AC ID（默认为1）
        :return: (success, message, response_data)
        """
        try:
            # 0. 先获取challenge (token)
            challenge = self.get_challenge(username, ip)
            if not challenge:
                logger.warning("[加密登录] 未能获取challenge")
                return False, "无法获取Challenge，请检查网络", None

            # 1. 生成HMAC-MD5加密的密码
            hmac_md5 = get_hmac_md5(password, challenge)
            hmac_password = "{MD5}" + hmac_md5

            # 2. 生成info参数 (使用challenge作为xEncode的key)
            info_param = get_info(username, password, ip, ac_id, challenge)

            # 3. 计算chksum（UCAS算法：每个字段之间都插入token）
            chkstr = challenge + username
            chkstr += challenge + hmac_md5  # 使用纯HMAC-MD5,不带{MD5}前缀
            chkstr += challenge + str(ac_id)
            chkstr += challenge + ip
            chkstr += challenge + "200"  # n参数
            chkstr += challenge + "1"    # type参数
            chkstr += challenge + info_param
            chksum = get_sha1(chkstr)

            # 4. 生成callback（模拟jQuery）
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{str(timestamp)[:13]}_{timestamp}"

            # 5. 构造请求参数
            params = {
                "callback": callback,
                "action": "login",
                "username": username,
                "password": hmac_password,  # 带{MD5}前缀
                "os": "Windows 10",
                "name": "Windows",
                "double_stack": "0",
                "chksum": chksum,
                "info": info_param,
                "ac_id": str(ac_id),
                "ip": ip,
                "n": "200",
                "type": "1",
                "_": str(timestamp + 1)
            }

            # 6. 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'Accept': 'text/javascript, application/javascript, */*',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.portal_url.rsplit("/", 1)[0]}/srun_portal_pc?ac_id={ac_id}&theme=pro'
            }

            # 7. 发送请求
            logger.debug(f"[加密登录] 正在发送认证请求...")

            response = self.session.get(
                self.portal_url,
                params=params,
                headers=headers,
                timeout=10
            )

            logger.debug(f"[加密登录] HTTP状态码: {response.status_code}")

            # 8. 解析响应
            return self._parse_response(response.text)

        except requests.Timeout:
            return False, "连接超时，请检查网络", None
        except requests.ConnectionError:
            return False, "无法连接到认证服务器", None
        except Exception as e:
            return False, f"认证异常: {str(e)}", None

    def _parse_response(self, response_text):
        """解析JSONP响应"""
        try:
            # 先尝试解析JSONP格式
            match = re.search(r'jQuery\w+\((.*)\)', response_text)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
            else:
                # 尝试直接解析JSON
                data = json.loads(response_text)

            logger.debug("[解析响应] 收到响应数据")

            # 检查多种可能的字段
            error = str(data.get('error', '')).lower()
            error_msg = str(data.get('error_msg', '')).lower()
            message = str(data.get('message', '')).lower()
            res = str(data.get('res', '')).lower()
            code = data.get('code', -1)
            ecode = data.get('ecode', -1)

            # ===== 优先检查您学校的响应格式 =====
            # 检查 code: 0 + message: success (您学校的格式)
            if code == 0:
                logger.debug("[解析响应] 登录成功 (code=0)")
                return True, "登录成功！", data

            # ===== 标准深澜响应格式 =====
            # 【重要】先检查错误状态，再检查成功状态

            # 1. 签名错误（优先级最高）
            if 'sign_error' in error or 'sign_error' in res:
                return False, "认证签名错误，请检查账号密码或网络配置", data

            # 2. challenge过期错误
            if 'challenge_expire' in error or 'challenge_expire' in res:
                return False, "Challenge已过期，请重试", data

            # 3. 检查明确的成功标志
            if error == 'ok' or res == 'ok':
                return True, "登录成功！", data

            # 4. 检查是否已在线
            if 'already_online' in error or 'already_online' in res:
                return True, "您已在线", data

            if 'online_num' in error or 'online_num' in res:
                return True, "您已在线", data

            # 5. 包含"在线"关键词的error_msg
            if '在线' in error_msg or 'online' in error_msg.lower():
                return True, "您已在线", data

            # 失败
            if error and error != 'ok':
                return False, f"登录失败: {error}", data
            if error_msg:
                return False, f"登录失败: {error_msg}", data
            if message and 'success' not in message:
                return False, f"登录失败: {message}", data

            return False, "登录失败: 未知错误", data

        except json.JSONDecodeError:
            return False, f"无法解析响应: {response_text[:200]}", None
        except Exception as e:
            return False, f"解析响应时出错: {str(e)}", None


# 全局实例
srun_encrypted_auth = SrunEncryptedAuth()


def test_encrypted_login():
    """测试加密登录"""
    import network

    # 获取当前IP
    ip = network.get_current_ip()
    if not ip:
        print("无法获取IP地址")
        return

    print(f"当前IP: {ip}")

    # 测试参数（替换为你的信息）
    username = "20241654@chinanet"
    password = "your_password"  # 替换为真实密码
    ac_id = 1

    # 执行登录
    success, message, data = srun_encrypted_auth.login(username, password, ip, ac_id)

    print(f"\n结果: {'成功' if success else '失败'}")
    print(f"信息: {message}")
    if data:
        print(f"数据: {json.dumps(data, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    test_encrypted_login()
