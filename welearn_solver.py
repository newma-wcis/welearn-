import requests
import json
import time
import random
import re
import base64
from urllib.parse import urlparse, parse_qs, unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class WeLearnAssistant:
    def __init__(self):
        self.base_url = "http://welearn.sflep.com/Ajax/SCO.aspx"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = requests.Session()
        # 配置重试机制
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

        # 用户相关数据
        self.user_id = ""
        self.course_id = ""
        self.class_id = ""
        self.target_units = [1, 2, 3, 4, 5, 6, 7, 8]  # 默认尝试刷前8个单元
        self.max_section = 40

    def set_cookie(self, cookie_str):
        """设置 Cookie 并更新 Session Headers"""
        self.session.headers.update({"Cookie": cookie_str})

    def login(self, username, password):
        """
        自动登录逻辑
        逆向分析：Base64(Timestamp * Hex(Password))
        """
        print("[*] 正在连接 SSO 服务器...")

        try:
            # 1. 访问 WeLearn 触发 SSO 跳转，获取关键的 returnUrl (包含 state 和 challenge)
            entry_url = "http://welearn.sflep.com/Student/MyCourse.aspx"
            resp = self.session.get(entry_url)

            # 检查是否跳转到了 sso 登录页
            current_url = resp.url
            if "idsvr/login.html" not in current_url:
                # 还有一种可能：Session 里已经有有效 Cookie，直接进系统了
                if "welearn.sflep.com" in current_url:
                    print("[+] 检测到已登录状态，跳过登录步骤。")
                    return True
                print("[-] 初始化登录环境失败，未跳转到 SSO 页面。")
                return False

            # 从 URL Query 中提取 returnUrl
            parsed = urlparse(current_url)
            qs = parse_qs(parsed.query)
            return_url = qs.get('returnUrl', [''])[0]

            if not return_url:
                print("[-] 无法获取 returnUrl 参数，SSO 协议可能已变更。")
                return False

            # 2. 构造加密 Payload
            ts = str(int(time.time() * 1000))
            # 将密码转为 Hex 字符串 (小写)
            pwd_hex = password.encode('utf-8').hex()
            # 拼接: 时间戳 * Hex密码
            raw_str = f"{ts}*{pwd_hex}"
            # Base64 编码
            encrypted_pwd = base64.b64encode(raw_str.encode('utf-8')).decode('utf-8')

            # 3. 发送登录请求
            login_api = "https://sso.sflep.com/idsvr/account/login"

            headers = self.headers.copy()
            headers.update({
                "Referer": current_url,
                "Origin": "https://sso.sflep.com"
            })

            data = {
                "rturl": return_url,
                "account": username,
                "pwd": encrypted_pwd,
                "ts": ts
            }

            print(f"[*] 正在验证账户 {username} ...")
            resp_login = self.session.post(login_api, data=data, headers=headers)

            # 4. 处理登录结果
            # 服务器通常返回 JSON: {"state": 1, "url": "/connect/authorize/callback?..."}
            if resp_login.status_code == 200:
                try:
                    res_json = resp_login.json()
                    if res_json.get('state') == 1 and res_json.get('url'):
                        # 登录成功，获取跳转链接
                        redirect_url = res_json['url']
                        if not redirect_url.startswith('http'):
                            redirect_url = "https://sso.sflep.com" + redirect_url

                        print("[*] 验证通过，正在进行授权回调...")
                        # 访问回调地址，这一步会自动处理一系列 302 重定向，最终写 Cookie
                        self.session.get(redirect_url)
                        print("[+] 登录成功！")
                        return True
                    else:
                        print(f"[-] 登录失败: {res_json.get('msg', '账号或密码错误')}")
                        return False
                except json.JSONDecodeError:
                    print("[-] 登录响应解析失败，非 JSON 格式。")
                    return False
            else:
                print(f"[-] 服务器返回错误状态码: {resp_login.status_code}")
                return False

        except Exception as e:
            print(f"[!] 登录过程发生异常: {e}")
            return False

    def parse_course_url(self, url):
        """从 URL 中提取 cid 和 classid"""
        try:
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)

            if 'cid' in params:
                self.course_id = params['cid'][0]
            if 'classid' in params:
                self.class_id = params['classid'][0]

            return bool(self.course_id and self.class_id)
        except Exception as e:
            print(f"[!] URL 解析失败: {e}")
            return False

    def fetch_user_id(self):
        """
        [自动探测 User ID]
        策略：
        放弃直接解析 StudyCourse.aspx (因为有 JS 防盗链跳转)。
        改为访问 '个人主页' (myprofile.aspx)，该页面必然会通过 HTTP 302 或 JS 指向含有 UID 的详情页。
        """
        print("[*] 正在探测 User ID ...")

        # 目标：个人主页入口
        entry_url = "http://welearn.sflep.com/user/myprofile.aspx"

        try:
            print(f"    -> 正在访问: {entry_url}")
            page_headers = self.headers.copy()
            # 移除 Ajax 标识，伪装成普通浏览器请求页面，避免触发服务器的特殊处理
            if "X-Requested-With" in page_headers: del page_headers["X-Requested-With"]

            resp = self.session.get(entry_url, headers=page_headers, timeout=15)

            # 情况 1: HTTP 302 跳转 (requests 自动跟随)
            # 如果最终 URL 变成了 .../stuprofile.aspx?uid=12345，直接提取
            final_url = resp.url
            if 'uid=' in final_url:
                parsed = urlparse(final_url)
                params = parse_qs(parsed.query)
                if 'uid' in params:
                    self.user_id = params['uid'][0]
                    print(f"[+] 成功！通过跳转自动捕获 User ID: {self.user_id}")
                    return True

            # 情况 2: 页面源码包含链接或 JS 跳转
            # 如果 requests 停留在 myprofile.aspx，说明是 JS 跳转
            # 我们直接在源码里找 "uid=xxxx"
            html = resp.text

            # 调试：检查是否 Cookie 失效
            if "login.aspx" in final_url.lower() or "signin" in final_url.lower():
                print("[-] Cookie 已失效，请重新登录。")
                return False

            print("    -> 分析页面源码寻找 UID...")

            # 正则 A: 匹配 stuprofile.aspx?uid=12345
            match = re.search(r'stuprofile\.aspx\?uid=(\d+)', html, re.IGNORECASE)
            if match:
                self.user_id = match.group(1)
                print(f"[+] 成功！从源码链接中提取到 User ID: {self.user_id}")
                return True

            # 正则 B: 暴力匹配任意 uid=12345 (防止链接格式变化)
            match_loose = re.search(r'uid=(\d{4,})', html, re.IGNORECASE)
            if match_loose:
                self.user_id = match_loose.group(1)
                print(f"[+] 成功！从源码中提取到 User ID: {self.user_id}")
                return True

        except Exception as e:
            print(f"    [!] 探测失败: {e}")

        print("[-] 无法自动获取 User ID。")
        print("    可能原因：1. Cookie失效  2. 网络问题  3. 页面结构变更")
        print("    请尝试手动输入 User ID。")
        return False

    def generate_ids(self):
        """生成任务 ID 列表"""
        ids = []
        for unit in self.target_units:
            for section in range(1, self.max_section + 1):
                ids.append(f"m-3-{unit}-{section}")
        for unit in self.target_units:
            ids.append(f"m-3-{unit}-intro")
        return ids

    # ================= 刷课核心逻辑 =================

    def start_sco(self, scoid):
        params = {
            "action": "startsco160928",
            "cid": self.course_id,
            "scoid": scoid,
            "uid": self.user_id,
            "classid": self.class_id,
            "tid": "-1",
            "nocache": random.random()
        }
        try:
            resp = self.session.post(self.base_url, data=params, headers=self.headers, timeout=10)
            return resp.json().get('ret') == 0
        except:
            return False

    def get_sco_info(self, scoid):
        params = {
            "action": "getscoinfo_v7",
            "cid": self.course_id,
            "scoid": scoid,
            "uid": self.user_id,
            "nocache": random.random()
        }
        try:
            resp = self.session.post(self.base_url, data=params, headers=self.headers, timeout=10)
            if resp.status_code == 200 and resp.json().get('ret') == 0:
                return resp.json().get('comment', '')
            return None
        except:
            return None

    def construct_payload(self, raw_data_str):
        try:
            if not raw_data_str:
                cmi_data = {
                    "cmi": {
                        "completion_status": "completed",
                        "success_status": "passed",
                        "mode": "normal",
                        "score": {"scaled": "1", "raw": "100"},
                        "session_time": str(random.randint(300, 600)),
                        "progress_measure": "1",
                        "interactions": []
                    },
                    "adl": {"data": []},
                    "cci": {"data": [], "retry_count": "1", "submit": {}}
                }
            else:
                cmi_data = json.loads(raw_data_str)
                cmi_data['cmi']['completion_status'] = "completed"
                cmi_data['cmi']['success_status'] = "passed"
                cmi_data['cmi']['score']['raw'] = "100"
                cmi_data['cmi']['score']['scaled'] = "1"
                cmi_data['cmi']['session_time'] = str(random.randint(300, 600))

                if 'interactions' in cmi_data['cmi']:
                    for item in cmi_data['cmi']['interactions']:
                        item['result'] = "correct"
                        if 'correct_responses' in item and len(item['correct_responses']) > 0:
                            pat = item['correct_responses'][0].get('pattern')
                            if pat: item['learner_response'] = pat

            suffix_parts = []
            interactions = cmi_data.get('cmi', {}).get('interactions', [])
            for index, item in enumerate(interactions):
                response = item.get('learner_response', '')
                part = f"{index}[]false[]false[]{response}[]correct"
                suffix_parts.append(part)

            suffix = "[INTERACTIONINFO]" + "$$".join(suffix_parts) if suffix_parts else "[INTERACTIONINFO]"

            json_str = json.dumps(cmi_data, separators=(',', ':'))
            return json_str + suffix

        except Exception as e:
            return None

    def submit_sco(self, scoid, data_payload):
        params = {
            "action": "setscoinfo",
            "cid": self.course_id,
            "scoid": scoid,
            "uid": self.user_id,
            "data": data_payload,
            "isend": "true",
            "nocache": random.random()
        }
        try:
            resp = self.session.post(self.base_url, data=params, headers=self.headers, timeout=10)
            return resp.json()
        except Exception as e:
            return {"ret": -1, "mess": str(e)}

    def run_task(self, scoid):
        print(f"处理: {scoid} ...", end=" ", flush=True)

        info = self.get_sco_info(scoid)

        if info is None:
            print("[未激活]", end=" ", flush=True)
            if self.start_sco(scoid):
                print("-> [激活成功]", end=" ", flush=True)
                info = self.get_sco_info(scoid)
            else:
                print("-> [跳过(对象不存在)]")
                return

        if info is None:
            print("-> [无法获取数据]")
            return

        payload = self.construct_payload(info)
        if not payload:
            return

        res = self.submit_sco(scoid, payload)
        if res.get('ret') == 0:
            print("-> [成功100分!]")
        else:
            print(f"-> [失败: {res.get('mess', '未知错误')}]")


# ================= 交互界面 =================

def main():
    print("========================================")
    print("      WeLearn 通用刷课助手 Pro v1.0      ")
    print("========================================")

    assistant = WeLearnAssistant()

    # 1. 登录模块
    print("\n[步骤 1/3] 登录方式")
    print("1. 账号密码登录 (推荐)")
    print("2. 手动输入 Cookie")
    choice = input("请选择 (1/2) > ").strip()

    logged_in = False
    if choice == '2':
        cookie = input("Cookie > ").strip()
        if cookie:
            assistant.set_cookie(cookie)
            logged_in = True
    else:
        user = input("手机号/账号 > ").strip()
        pwd = input("密码 > ").strip()
        if user and pwd:
            if assistant.login(user, pwd):
                logged_in = True
            else:
                print("登录失败，程序退出。")
                return
        else:
            print("账号密码不能为空。")
            return

    if not logged_in:
        return

    # 2. 获取课程链接
    print("\n[步骤 2/3] 请输入课程主页链接:")
    print("例如: http://welearn.sflep.com/Student/StudyCourse.aspx?cid=1234&classid=123456")
    url = input("URL > ").strip()
    if not assistant.parse_course_url(url):
        print("URL 格式不正确，未找到 cid 或 classid")
        return
    print(f"[*] 解析成功: CID={assistant.course_id}, ClassID={assistant.class_id}")

    # 3. 自动获取 User ID
    print("\n[步骤 3/3] 正在验证身份...")
    if not assistant.fetch_user_id():
        print("无法获取用户信息，请检查账号状态。")
        manual = input("是否手动输入 User ID? (y/n) > ")
        if manual.lower() == 'y':
            uid = input("User ID > ").strip()
            assistant.user_id = uid
        else:
            return

    # 4. 确认执行
    print("\n================ 信息确认 ================")
    print(f"用户 ID: {assistant.user_id}")
    print(f"课程 ID: {assistant.course_id}")
    print(f"班级 ID: {assistant.class_id}")
    print("==========================================")

    confirm = input("确认开始刷题吗? (y/n) > ")
    if confirm.lower() != 'y':
        return

    tasks = assistant.generate_ids()
    print(f"\n[*] 任务队列已生成，共 {len(tasks)} 个节点")
    print("[*] 开始执行 (按 Ctrl+C 中止)...")

    try:
        for scoid in tasks:
            assistant.run_task(scoid)
            time.sleep(random.uniform(1, 2))
    except KeyboardInterrupt:
        print("\n[!] 用户中止")

    print("\n[*] 执行完毕！请去网页端刷新查看进度。")


if __name__ == "__main__":
    main()