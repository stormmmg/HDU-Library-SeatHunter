'''
Author: littleherozzzx zhou.xin2022.code@outlook.com
Date: 2023-01-12 13:27:24
LastEditTime: 2023-02-01 11:19:38
Software: VSCode
'''
import os
import requests
import sys
import os
from urllib.parse import unquote
from prettytable import PrettyTable
from time import sleep
import datetime as dt
import hashlib
import base64
import json
if getattr(sys, 'frozen', False):
    # PyInstaller打包模式，exe所在目录
    sys.path.append(os.path.dirname(sys.executable))
else:
    # 开发模式，项目根目录
    sys.path.append(os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

from config.config import ConfigParser

class Killer:
    def __init__(self):
        pass
    
    def init(self, configFile):
        self.loadConfig(configFile)
        self.__initSession()
        self.rooms = {}
    
    def loadConfig(self, configFile):
        self.configParser = ConfigParser(configFile)
        if not os.path.exists(configFile):
            self.configParser.createConfig()
        self.cfg = self.configParser.parseConfig()
        self.sessionCfg = self.cfg['session']
        self.urls = self.cfg['urls']
        self.seat_list = self.cfg["seat_list"]
        self.data = self.cfg["data"]
        self.settings = self.cfg["settings"]
        self.userInfo = self.cfg["user_info"]
        self.plans = self.cfg["plans"]

    def saveConfig(self):
        self.cfg['seat_list'] = self.seat_list
        self.cfg['user_info'] = self.userInfo
        self.cfg['plans'] = self.plans
        self.configParser.saveConfig(self.cfg)
    
    def __initSession(self):
        import urllib3
        urllib3.disable_warnings()
        self.session = requests.Session()
        self.session.headers.clear()
        self.session.headers = self.sessionCfg['headers']
        self.session.trust_env = self.sessionCfg['trust_env']
        self.session.verify = self.sessionCfg['verify']
        self.session.params = self.sessionCfg['params']

    def __getCookieFile(self):
        """返回cookie缓存文件路径"""
        configDir = os.path.dirname(self.configParser.configFile)
        return os.path.join(configDir, "session.json")

    def __saveCookies(self, cookies):
        """保存cookies到本地文件"""
        cookieFile = self.__getCookieFile()
        data = {
            "saved_at": dt.datetime.now().isoformat(),
            "cookies": cookies,
            "uid": self.uid,
            "name": self.name,
        }
        with open(cookieFile, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def __loadCookies(self):
        """加载本地cookies，超过20天返回None"""
        cookieFile = self.__getCookieFile()
        if not os.path.exists(cookieFile):
            return None
        try:
            with open(cookieFile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved_at = dt.datetime.fromisoformat(data["saved_at"])
            if (dt.datetime.now() - saved_at).days >= 20:
                return None
            return data
        except:
            return None

    def __loginWithCookies(self):
        """尝试用本地缓存的cookies登录"""
        cached = self.__loadCookies()
        if not cached:
            return False
        print("发现本地登录缓存，尝试使用...", flush=True)
        # 用字典方式设置cookies，避免domain匹配问题
        cookie_dict = {c['name']: c['value'] for c in cached["cookies"]}
        self.session.cookies.update(cookie_dict)
        # 验证cookies是否有效：调用searchSeats检查
        try:
            params = {
                "space_category[category_id]": self.data.get("query_data", {}).get("space_category[category_id]", "591"),
                "space_category[content_id]": self.data.get("query_data", {}).get("space_category[content_id]", "3"),
            }
            resp = self.session.get(url=self.urls["query_seats"], params=params, timeout=15)
            data = resp.json()
            if isinstance(data, dict) and data.get("data") and data["data"].get("uid"):
                self.uid = str(data["data"]["uid"])
                self.name = data["data"].get("uname", "")
                self.session.cookies.update({"org_id": "104"})
                print(f"本地缓存登录成功: uid={self.uid}, name={self.name}", flush=True)
                return True
            else:
                print(f"本地缓存验证失败，服务器返回: {json.dumps(data, ensure_ascii=False)[:200]}", flush=True)
        except Exception as e:
            print(f"本地缓存验证异常: {e}", flush=True)
        print("本地缓存已失效", flush=True)
        return False

    def __loginWithPlaywright(self):
        """通过Playwright浏览器自动化完成HDU CAS SSO登录"""
        import asyncio
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("请先安装playwright: pip install playwright && python -m playwright install chromium")
            return False

        async def _login():
            username = self.userInfo.get("login_name", "")
            password = self.userInfo.get("password", "")
            library_url = self.urls.get("index", "https://hdu.huitu.zhishulib.com/")

            async with async_playwright() as p:
                print("正在启动浏览器...", flush=True)
                launch_opts = {"headless": True}
                if getattr(sys, 'frozen', False):
                    # PyInstaller打包模式，使用捆绑的Chromium
                    chromium_path = os.path.join(os.path.dirname(sys.executable), 'chromium', 'chrome-win64', 'chrome.exe')
                    if os.path.exists(chromium_path):
                        launch_opts["executable_path"] = chromium_path
                    else:
                        print(f"警告: 未找到捆绑的Chromium: {chromium_path}", flush=True)
                browser = await p.chromium.launch(**launch_opts)
                context = await browser.new_context()
                page = await context.new_page()

                print("正在访问登录页面...", flush=True)
                await page.goto(library_url, wait_until='domcontentloaded', timeout=60000)

                # 直接等待用户名输入框出现，最多等30秒
                print("等待登录页面...", flush=True)
                username_selectors = [
                    'input[name="username"]',
                    'input[formcontrolname="username"]',
                    'input[placeholder*="学工号"]',
                    'input[type="text"]',
                ]
                username_input = None
                for selector in username_selectors:
                    try:
                        username_input = await page.wait_for_selector(selector, timeout=10000)
                        if username_input:
                            break
                    except:
                        continue

                # 如果第一批选择器都没找到，再等一轮
                if not username_input:
                    try:
                        username_input = await page.wait_for_selector(','.join(username_selectors), timeout=20000)
                    except:
                        pass

                if not username_input:
                    print("无法找到用户名输入框")
                    await browser.close()
                    return False, None, "", ""

                print("正在填写用户名...", flush=True)
                await username_input.fill(str(username))

                # 等待密码输入框
                password_selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[formcontrolname="password"]',
                ]
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = await page.wait_for_selector(selector, timeout=3000)
                        if password_input:
                            break
                    except:
                        continue

                if not password_input:
                    print("无法找到密码输入框")
                    await browser.close()
                    return False, None, "", ""

                await password_input.fill(str(password))

                print("正在提交登录...", flush=True)
                login_btn = None
                for selector in ['button[type="submit"]', 'button:has-text("登录")']:
                    try:
                        login_btn = await page.wait_for_selector(selector, timeout=3000)
                        if login_btn:
                            break
                    except:
                        continue

                if not login_btn:
                    print("无法找到登录按钮")
                    await browser.close()
                    return False, None, "", ""

                await login_btn.click()

                print("等待登录完成...", flush=True)
                try:
                    await page.wait_for_url('**/huitu.zhishulib.com/**', timeout=30000)
                except:
                    await asyncio.sleep(5)

                current_url = page.url
                if 'huitu.zhishulib.com' not in current_url:
                    print(f"登录可能失败，当前URL: {current_url}")
                    await browser.close()
                    return False, None, "", ""

                # 提取图书馆系统cookies
                all_cookies = await context.cookies()
                lib_cookies = [c for c in all_cookies if 'huitu.zhishulib.com' in c.get('domain', '')]

                # 获取用户信息
                print("正在获取用户信息...", flush=True)
                uid = ""
                name = ""
                try:
                    resp_text = await page.evaluate('''async () => {
                        const resp = await fetch("/Seat/Index/searchSeats?space_category[category_id]=591&space_category[content_id]=3&LAB_JSON=1");
                        return await resp.text();
                    }''')
                    data = json.loads(resp_text)
                    if isinstance(data, dict) and data.get("data"):
                        uid = str(data["data"].get("uid", ""))
                        name = data["data"].get("uname", "")
                except Exception as e:
                    print(f"浏览器内获取用户信息失败: {e}", flush=True)

                if not uid:
                    for c in lib_cookies:
                        if c['name'] == 'uid':
                            uid = c['value']
                            break

                print(f"获取到用户信息: uid={uid}, name={name}", flush=True)
                await browser.close()
                return True, lib_cookies, uid, name

        try:
            success, cookies, uid, name = asyncio.run(_login())
        except Exception as e:
            print(f"登录异常: {e}")
            return False

        if not success or not cookies:
            return False

        # 将Playwright获取的cookies设置到requests.Session中
        cookie_dict = {c['name']: c['value'] for c in cookies}
        self.session.cookies.update(cookie_dict)

        self.uid = uid or ""
        self.name = name or ""

        # 如果浏览器中未获取到uid，用requests调用searchSeats API
        if not self.uid:
            try:
                params = {
                    "space_category[category_id]": self.data.get("query_data", {}).get("space_category[category_id]", "591"),
                    "space_category[content_id]": self.data.get("query_data", {}).get("space_category[content_id]", "3"),
                }
                resp = self.session.get(url=self.urls["query_seats"], params=params, timeout=15)
                data = resp.json()
                if isinstance(data, dict) and data.get("data"):
                    self.uid = str(data["data"].get("uid", ""))
                    self.name = data["data"].get("uname", "")
            except:
                pass

        # 保存cookies到本地
        self.__saveCookies(cookies)
        print("登录成功（已保存登录缓存）")
        return True

    def login(self):
        """登录：优先使用本地cookie缓存，失败则用Playwright登录"""
        if self.__loginWithCookies():
            return True
        return self.__loginWithPlaywright()

    def __queryRooms(self):
        # 查询所有可用的房间类型，返回一个字典，键为房间名，值为房间对应的请求参数
        url = self.urls["query_rooms"]
        self.session.cookies.update({"org_id":"104"})
        queryRoomsRes = self.session.get(url=url, timeout=30).json()
        rawRooms = queryRoomsRes["content"]["children"][1]["defaultItems"]
        rooms = {x["name"]: unquote(x["link"]["url"]).split('?')[1] for x in rawRooms}
        for room in rooms.keys():
            rooms[room] = self.session.get(url=self.urls["query_seats"] + "?" + rooms[room], timeout=30).json()["data"]
            sleep(2)
        return rooms
    
    def __querySeats(self):
        #  查询每个房间的作为信息
        time = dt.datetime.now()
        if time.hour >= 22:
            time = time + dt.timedelta(days=1)
            time = time.replace(hour=11, minute=0, second=0)
        for room in self.rooms.keys():
            data = {
                "beginTime": time.timestamp(),
                "duration": 3600,
                "num": 1,
                "space_category[category_id]": self.rooms[room]["space_category"]["category_id"],
                "space_category[content_id]": self.rooms[room]["space_category"]["content_id"],
            }
            resp = self.session.post(url=self.urls["query_seats"], data=data, timeout=30).json()
            self.rooms[room]["floors"] = {x["roomName"]:x for x in resp["allContent"]["children"][2]["children"]["children"]}
            for floor in self.rooms[room]["floors"].keys():
                self.rooms[room]["floors"][floor]["seats"] = self.rooms[room]["floors"][floor]["seatMap"]["POIs"]
            sleep(2)
    def updateRooms(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.rooms = self.__queryRooms()
                self.__querySeats()
                return list(self.rooms.keys())
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"获取房间信息失败(第{attempt+1}次)，5秒后重试: {e}", flush=True)
                    sleep(5)
                else:
                    print(f"获取房间信息失败，已重试{max_retries}次: {e}", flush=True)
                    self.rooms = {}
                    return []
    
    def getFloorNamesByRoom(self, roomName):
        floors = self.rooms[roomName]["floors"]
        return list(floors.keys())
    
    def getSeatsByRoomAndFloor(self, roomName, floorName):
        seats = self.rooms[roomName]["floors"][floorName]["seats"]
        return seats
    
    def addPlan(self, roomName, beginTime, duration, seatsInfo, seatBookers):
        self.plans.append({
            "roomName": roomName,
            "beginTime": beginTime,
            "duration": duration,
            "seatsInfo": list(seatsInfo),
            "seatBookers": list(seatBookers),
        })
    
    def plan2data(self, plan):
        data = {}
        data["beginTime"] = int(plan["beginTime"].timestamp())
        data["duration"] = plan["duration"]*3600
        for i in range(len(plan["seatsInfo"])):
            data[f"seats[{i}]"] = plan["seatsInfo"][i]["seatId"]
        data["is_recommend"] = 0
        data["api_time"] = int(dt.datetime.now().timestamp())
        for i in range(len(plan["seatsInfo"])):
            data[f"seatBookers[{i}]"] = plan["seatBookers"][i]
        apiToken = f"post&/Seat/Index/bookSeats?LAB_JSON=1&api_time{data['api_time']}&beginTime{data['beginTime']}&duration{data['duration']}&is_recommend0&seatBookers[0]{data['seatBookers[0]']}&seats[0]{data['seats[0]']}"
        md5 = hashlib.md5(apiToken.encode("utf-8")).hexdigest()
        apiToken = base64.b64encode(md5.encode("utf-8"))
        return data, apiToken
    
    def showPlan(self):
        print(f"当前共有{len(self.plans)}个预约方案")
        if len(self.plans) == 0:
            return
        table = PrettyTable(["序号", "房间名", "楼层名", "座位号", "开始时间", "持续时间", "预约人"])
        for i, plan in enumerate(self.plans):
            seat = plan["seatsInfo"][0]
            table.add_row([f"{i+1}", seat['roomName'], seat['floorName'], ",".join([x["seatNum"] for x in plan["seatsInfo"]]), plan['beginTime'], str(plan['duration'])+"小时", ",".join([x["bookerName"] for x in plan["seatsInfo"]])])
        print(table)
    
    def deletePlan(self, index):
        index = set(index)
        self.plans = [x for i, x in enumerate(self.plans) if i not in index]
    def run(self, plan):
            data, Api_Token = self.plan2data(plan)
            url = self.urls["book_seat"]
            self.session.headers["Api-Token"] = Api_Token.decode()
            self.session.headers["Content-Length"] = "114"
            res = self.session.post(url=url, data=data).json()
            return res
            
    def changeTime(self, index, beginTime, duration):
        for i in index:
            self.plans[i]["beginTime"] = beginTime
            self.plans[i]["duration"] = duration
        

if __name__ == "__main__":

    
    killer = Killer()
    killer.init("./config/config.yaml")
    print(killer.login())
    killer.run(killer.plans[0])
        
        