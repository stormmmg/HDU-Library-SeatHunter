import os
import sys
import json

from time import sleep
from pwinput import pwinput
from datetime import datetime, timedelta
from utils.killer import Killer
from utils.window import maximizeWindow
from threading import Thread
from prettytable import PrettyTable

from argparse import ArgumentParser


def get_app_dir():
    """获取应用程序根目录（兼容PyInstaller打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))





BOOKING_ADVANCE_DAYS = 2  # x日座位预约开放时间为x-2日晚20:00


class UserInterface:
    def __init__(self, args=None):
        self.configFile = os.path.join(get_app_dir(), "config", "config.yaml") if args is None else args.config
        self.killer = Killer()
        self.funcs = [self.changePlan, self.changeTime, self.startNow, self.scheduledBooking, self.setSettings, self.help, self.exit]
    
    def init(self):
        
        if not os.path.exists(self.configFile):
            print(f"未检测到配置文件，将在config目录下创建配置文件: {self.configFile}")
            self.killer.init(self.configFile)
        else:
            try:
                self.killer.init(self.configFile)              
            except Exception as e:
                print(f"配置文件解析失败，请检查配置文件是否正确。错误为：")
                print(e)
                print(f"若无法解决，请尝试删除{self.configFile}，重新运行程序。")
                exit(1)
            print(f"配置文件解析成功。")
            sleep(1)

    def setUserInfo(self):
        userInfo = {}
        userInfo["login_name"] = input("请输入学号：")
        userInfo["password"] = pwinput("请输入密码：")
        self.killer.userInfo = userInfo

    def login(self):
        flag = False
        network_retry_count = 0
        max_network_retries = 5
        while not flag:
            if self.killer.userInfo["login_name"]  and self.killer.userInfo["password"] :
                success, err_type = self.killer.login()
                if success:
                    print("登录成功")
                    self.killer.saveConfig()
                    self.th = Thread(target=self.killer.updateRooms)
                    self.th.start()
                    flag = True
                elif err_type == self.killer.LOGIN_ERR_NETWORK:
                    network_retry_count += 1
                    if network_retry_count <= max_network_retries:
                        wait = min(network_retry_count * 5, 30)
                        print(f"网络连接失败（连接被重置），{wait}秒后第{network_retry_count}次重试（共{max_network_retries}次）...")
                        sleep(wait)
                    else:
                        print(f"网络连接持续失败，已重试{max_network_retries}次。")
                        print("可能的原因：")
                        print("  1. 不在校园网环境内（需要连接HDU校园网或VPN）")
                        print("  2. 图书馆服务器暂时不可用")
                        print("  3. 网络防火墙拦截了连接")
                        retry = input("是否继续重试？(y/n): ").strip().lower()
                        if retry == 'y':
                            network_retry_count = 0
                        else:
                            exit(1)
                else:
                    print("账号密码错误，请重新输入")
                    self.setUserInfo()
            else:
                self.setUserInfo()
    
    def showMenu(self):
        print("1. 查看/添加/删除待选座位方案")   
        print("2. 批量修改方案中预约时间")
        print("3. 立即开始抢座")
        print("4. 定时抢座")
        print("5. 修改请求间隔和次数")
        print("6. 使用帮助")
        print("7. 退出")
    
    def changePlan(self):
        self.killer.showPlan()
        while True:
            print("1. 添加方案")
            print("2. 删除方案")
            print("3. 返回上一级")
            try:

                choice = int(input("请输入选项："))
                if choice == 1:
                    self.addPlan()
                elif choice == 2:
                    self.deletePlan()
                elif choice == 3:
                    break
                else:
                    print("输入错误，请重新输入")
                    sleep(1)
                    continue
            except Exception as e:
                print("输入错误，请重新输入")
                sleep(1)
                continue
    
    def changeTime(self):
        self.killer.showPlan()
        try:
            index = input("请输入要删除的预约序号（多个用英文逗号隔开，如1,2,3，输入0表示修改所有方案）：")
            index = tuple(int(x.strip()) for x in index.split(",") if x.strip())
            if any([x > len(self.killer.plans) for x in index]):
                raise Exception(f"序号超出范围，当前共有{len(self.killer.plans)}个方案")
            if any([x < 0 for x in index]):
                raise Exception("序号不能小于0")
            if 0 in index and len(index) > 1:
                raise Exception("序号序列不能同时包含0和其他序号")
            if 0 in index:
                index = list(range(1, len(self.killer.plans)+1))
            index = [x-1 for x in index]
            print("请注意，**本模块不对预约时间和预约时长的合法性进行检查**，请您自行检查，错误的时间可能导致**封号一周**的惩罚。")
            print(f"请输入开始使用时间（格式为yyyy-mm-dd hh:mm:ss，如2023-01-01 12:00:00）：")
            time = input()
            time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
            hours = int(input(f"请输入使用时长，单位为小时："))
            if hours < 0:
                raise Exception("时长不能小于0")
            self.killer.changeTime(index, time, hours)
            self.killer.saveConfig()
            print("修改成功")
            sleep(1)
            self.killer.showPlan()
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)
             
    def startNow(self, prompt="按回车键退出"):
        for retryCnt in range(self.killer.cfg["settings"]["max_try_times"]):
            print(f"第{retryCnt+1}次尝试")
            for i, plan in enumerate(self.killer.plans):
                res = self.killer.run(plan)
                if res["CODE"] == "ok":
                    print("座位预约成功，座位信息为：")
                    table = PrettyTable(["房间名", "楼层名", "座位号", "开始时间", "持续时间", "预约人"])
                    seat = plan["seatsInfo"][0]
                    table.add_row([seat['roomName'], seat['floorName'], ",".join([x["seatNum"] for x in plan["seatsInfo"]]), plan['beginTime'], str(plan['duration'])+"小时", ",".join([x["bookerName"] for x in plan["seatsInfo"]])])
                    print(table)
                    input(prompt)
                    return
                else:
                    print(f"\r第{i+1}个方案预约失败，原因为："+"\033[0;31m%s\033[0m" % res['MESSAGE'])
                sleep(self.killer.cfg["settings"]["interval"])
                    
    def scheduledBooking(self):
        while True:
            print("1. 单次定时抢座")
            print("2. 指定日期抢座（预约日前2天20:00触发）")
            print("3. 按星期几抢座（预约日前2天20:00触发）")
            print("4. 查看/管理已保存的定时任务")
            print("5. 返回上一级")
            try:
                choice = int(input("请输入选项："))
                if choice == 1:
                    self._startAtOnce()
                elif choice == 2:
                    self._startAtDates()
                elif choice == 3:
                    self._startAtWeekdays()
                elif choice == 4:
                    self._manageSchedules()
                elif choice == 5:
                    break
                else:
                    print("输入错误，请重新输入")
                    sleep(1)
                    continue
            except ValueError:
                print("输入错误，请重新输入")
                sleep(1)
                continue

    def _countdown(self, target, label):
        print(f"在倒计时过程中，您可以使用Ctrl+C终止程序")
        while True:
            if datetime.now() >= target:
                break
            now = datetime.now().replace(microsecond=0)
            left = int((target - datetime.now()).total_seconds())
            if left < 60:
                print(f"\r当前时间为{now}，{label}，还有{left}秒，请耐心等待", end="", flush=True)
            elif left < 3600:
                print(f"\r当前时间为{now}，{label}，还有{left//60}分{left%60}秒，请耐心等待", end="", flush=True)
            else:
                print(f"\r当前时间为{now}，{label}，还有{left//3600}时{left%3600//60}分{left%60}秒，请耐心等待", end="", flush=True)
            sleep(1)

    def _getScheduleFile(self):
        configDir = os.path.dirname(self.configFile)
        return os.path.join(configDir, "schedule.json")

    def _loadSchedules(self):
        scheduleFile = self._getScheduleFile()
        if not os.path.exists(scheduleFile):
            return []
        try:
            with open(scheduleFile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("schedules", [])
        except:
            return []

    def _saveSchedules(self, schedules):
        scheduleFile = self._getScheduleFile()
        with open(scheduleFile, 'w', encoding='utf-8') as f:
            json.dump({"schedules": schedules}, f, ensure_ascii=False, indent=2)

    def _updatePlansBeginTime(self, target_date):
        """更新所有方案的beginTime为目标日期，保留原始时分秒"""
        for plan in self.killer.plans:
            old = plan["beginTime"]
            plan["beginTime"] = target_date.replace(
                hour=old.hour, minute=old.minute, second=old.second
            )

    def _findNextBookingTime(self, target_weekdays):
        """找到下一个目标星期几，返回(target_date, trigger_time)
        target_weekdays: Python weekday(0-6)，表示要使用座位的星期
        trigger_time = target_date - BOOKING_ADVANCE_DAYS天 at 20:00
        """
        now = datetime.now()
        for delta in range(0, 14):
            candidate = (now + timedelta(days=delta)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            if candidate.weekday() in target_weekdays:
                trigger = candidate.replace(hour=20, minute=0, second=0) - timedelta(days=BOOKING_ADVANCE_DAYS)
                if trigger > now:
                    return candidate, trigger
        raise Exception("无法找到下一个匹配的预约时间")

    def _startAtOnce(self):
        try:
            startTime = input("请输入程序开始运行时间（格式为yyyy-mm-dd hh:mm:ss，如2023-01-01 12:00:00）：")
            if not startTime.strip():
                raise Exception("输入不能为空")
            startTime = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            if startTime < datetime.now():
                raise Exception("开始时间不能小于当前时间")
            print("即将抢座的预约方案：")
            self.killer.showPlan()
            self._countdown(startTime, "预约开始时间")
            self.startNow("按回车键继续")
        except KeyboardInterrupt:
            print("\n程序终止")
            return
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)

    def _startAtDates(self):
        try:
            datesInput = input("请输入要使用座位的日期（格式为yyyy-mm-dd，多个用逗号隔开，如2026-04-19,2026-04-20）：")
            datesInput = datesInput.strip().replace("，", ",")
            if not datesInput:
                raise Exception("输入不能为空")
            target_dates = []
            for d in datesInput.split(","):
                d = d.strip()
                if not d:
                    continue
                target_dates.append(datetime.strptime(d, "%Y-%m-%d"))
            if not target_dates:
                raise Exception("请输入至少一个有效日期")
            target_dates.sort()

            # 保存到本地
            schedule = {
                "mode": "dates",
                "target_dates": [d.strftime("%Y-%m-%d") for d in target_dates],
                "created_at": datetime.now().isoformat()
            }
            schedules = self._loadSchedules()
            schedules.append(schedule)
            self._saveSchedules(schedules)

            self._runDatesSchedule(target_dates)
        except KeyboardInterrupt:
            print("\n程序终止")
            return
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)

    def _runDatesSchedule(self, target_dates):
        """执行指定日期模式的定时抢座"""
        WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        # 计算每个目标日期的触发时间: 目标日期 - BOOKING_ADVANCE_DAYS天 at 20:00
        triggers = []
        for td in target_dates:
            trigger = td.replace(hour=20, minute=0, second=0) - timedelta(days=BOOKING_ADVANCE_DAYS)
            triggers.append({"target": td, "trigger": trigger})
        triggers.sort(key=lambda x: x["trigger"])

        now = datetime.now()
        future = [t for t in triggers if t["trigger"] > now]
        skipped = [t for t in triggers if t["trigger"] <= now]
        if skipped:
            for s in skipped:
                print("\033[0;31m警告：%s(%s) 的预约开放时间(%s 20:00)已过，跳过\033[0m" % (
                    s['target'].strftime('%Y-%m-%d'), WEEKDAY_NAMES[s['target'].weekday()],
                    s['trigger'].strftime('%m-%d')))
        if not future:
            raise Exception("所有日期的预约开放时间已过，没有可执行的任务")

        print("即将抢座的预约方案：")
        self.killer.showPlan()

        for i, item in enumerate(future):
            target = item["target"]
            trigger = item["trigger"]
            label = "预约目标%s(%s), 触发时间%s 20:00" % (
                target.strftime('%m-%d'), WEEKDAY_NAMES[target.weekday()],
                trigger.strftime('%m-%d'))
            self._countdown(trigger, label)
            print(f"\n预约开放时间已到达，正在为{target.strftime('%Y-%m-%d')}({WEEKDAY_NAMES[target.weekday()]})更新方案并抢座...")
            self._updatePlansBeginTime(target)
            self.killer.saveConfig()
            self.startNow("按回车键继续")
            if i < len(future) - 1:
                next_item = future[i + 1]
                print(f"本轮抢座结束，等待下一个: {next_item['target'].strftime('%Y-%m-%d')}")

    def _startAtWeekdays(self):
        WEEKDAY_NAMES = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        try:
            weekdaysInput = input("请输入要使用座位的星期几（1-7，对应周一到周日，多个用逗号隔开，如1,3,5）：")
            weekdaysInput = weekdaysInput.strip().replace("，", ",")
            if not weekdaysInput:
                raise Exception("输入不能为空")
            target_weekdays = []
            for w in weekdaysInput.split(","):
                w = w.strip()
                if not w:
                    continue
                w = int(w)
                if w < 1 or w > 7:
                    raise Exception(f"星期{w}不合法，请输入1-7之间的数字")
                target_weekdays.append(w - 1)  # Python weekday 0-6
            if not target_weekdays:
                raise Exception("至少需要选择一天")
            target_weekdays = sorted(set(target_weekdays))

            # 保存到本地
            schedule = {
                "mode": "weekdays",
                "target_weekdays": [w + 1 for w in target_weekdays],  # 存为1-7
                "created_at": datetime.now().isoformat()
            }
            schedules = self._loadSchedules()
            schedules.append(schedule)
            self._saveSchedules(schedules)

            self._runWeekdaysSchedule(target_weekdays)
        except KeyboardInterrupt:
            print("\n程序终止")
            return
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)

    def _runWeekdaysSchedule(self, target_weekdays):
        """执行按星期几模式的定时抢座"""
        WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        print(f"将在以下星期的前{BOOKING_ADVANCE_DAYS}天20:00:00自动抢座: {', '.join([WEEKDAY_NAMES[w] for w in target_weekdays])}")
        print("即将抢座的预约方案：")
        self.killer.showPlan()

        while True:
            target_date, trigger_time = self._findNextBookingTime(target_weekdays)
            label = "预约目标%s(%s), 触发时间%s 20:00" % (
                target_date.strftime('%m-%d'), WEEKDAY_NAMES[target_date.weekday()],
                trigger_time.strftime('%m-%d'))
            self._countdown(trigger_time, label)
            print(f"\n预约开放时间已到达，正在为{target_date.strftime('%Y-%m-%d')}({WEEKDAY_NAMES[target_date.weekday()]})更新方案并抢座...")
            self._updatePlansBeginTime(target_date)
            self.killer.saveConfig()
            self.startNow("按回车键继续")
            print("本轮抢座结束，等待下一个预约时间...")

    def _manageSchedules(self):
        """查看/管理已保存的定时任务"""
        WEEKDAY_NAMES = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        schedules = self._loadSchedules()

        if not schedules:
            print("暂无已保存的定时任务")
            sleep(1)
            return

        while True:
            print(f"\n当前已保存{len(schedules)}个定时任务：")
            for i, s in enumerate(schedules):
                created = s.get("created_at", "未知")[:10]
                if s["mode"] == "dates":
                    dates_str = ", ".join(s["target_dates"])
                    print(f"  {i+1}. [指定日期] 使用日期: {dates_str} (创建于 {created})")
                elif s["mode"] == "weekdays":
                    days_str = ", ".join([WEEKDAY_NAMES.get(w, str(w)) for w in s["target_weekdays"]])
                    print(f"  {i+1}. [按星期几] {days_str} (创建于 {created})")

            print("\n1. 执行某个任务")
            print("2. 删除某个任务")
            print("3. 返回上一级")
            try:
                choice = int(input("请输入选项："))
                if choice == 1:
                    idx = int(input(f"请输入任务序号(1-{len(schedules)})："))
                    if idx < 1 or idx > len(schedules):
                        raise Exception("序号超出范围")
                    s = schedules[idx - 1]
                    if s["mode"] == "dates":
                        target_dates = [datetime.strptime(d, "%Y-%m-%d") for d in s["target_dates"]]
                        self._runDatesSchedule(target_dates)
                    elif s["mode"] == "weekdays":
                        tw = [w - 1 for w in s["target_weekdays"]]
                        self._runWeekdaysSchedule(tw)
                elif choice == 2:
                    idx = int(input(f"请输入要删除的任务序号(1-{len(schedules)})："))
                    if idx < 1 or idx > len(schedules):
                        raise Exception("序号超出范围")
                    schedules.pop(idx - 1)
                    self._saveSchedules(schedules)
                    print("删除成功")
                elif choice == 3:
                    break
                else:
                    print("输入错误，请重新输入")
            except ValueError:
                print("输入错误，请重新输入")
                sleep(1)
            except KeyboardInterrupt:
                print("\n已取消")
                return
            except Exception as e:
                print("\033[0;31m%s\033[0m" % e)
                sleep(1)
    
    def help(self):
        help_path = os.path.join(get_app_dir(), "docs", "help.md")
        if sys.platform == "win32":
            os.startfile(help_path)
        else:
            with open(help_path, "r") as f:
                print(f.read())
        input("按回车键返回")
    
    def exit(self):
        if self.th.is_alive():
            for _ in "请等待其他线程结束...":
                    print(_, end="", flush=True)
                    sleep(0.5 if self.th.is_alive() else 0.1)
            while self.th.is_alive():
                print(".", end="", flush=True)
                sleep(0.5)
        exit(0)
        
    def run(self):
        ui.init()
        ui.login()
        while True:
            self.showMenu()
            try:
                choice = int(input("请输入选项："))
                self.funcs[choice-1]()
            except Exception as e:
                print("输入错误，请重新输入")
                sleep(1)
                continue

    def addPlan(self):
        try:
            print("请根据系统提示填写作为预约信息，过程中可随时使用ctrl+c取消填写。")       
            # num = int(input("请输入使用人数(1-4)："))
            # if num < 1 or num > 4:
            #     raise Exception("人数不合法")
            num=1
            if self.th.is_alive():
                print("正在初始化楼层和座位信息（为避免频繁请求而导致封号，此过程可能需要几秒，请耐心等待）")
                for _ in "loading...":
                    print(_, end="", flush=True)
                    sleep(0.5 if self.th.is_alive() else 0.1)
                while self.th.is_alive():
                    print(".", end="", flush=True)
                    sleep(0.5)
            numRooms = len(self.killer.rooms)
            print("\n")
            for i in range(numRooms):
                print(f"{i+1}. {list(self.killer.rooms.keys())[i]}")
            print(f"请选择房间类型(1-{numRooms})：")
            roomName = int(input())
            if roomName < 1 or roomName > numRooms:
                raise Exception("房间类型不合法")
            roomName = list(self.killer.rooms.keys())[roomName-1]
            room = self.killer.rooms[roomName]
            floor = self.killer.getFloorNamesByRoom(roomName)
            if len(floor) == 0:
                raise Exception(f"{roomName}没有开放楼层")
            print(f"请选择楼层(1-{len(floor)})：")
            for i in range(len(floor)):
                print(f"{i+1}. {floor[i]}")
            floorName = floor[int(input())-1]
            print(f'本房间最早开放时间为：{room["range"]["minBeginTime"]}时，最晚开放时间为：{room["range"]["maxEndTime"]}时')
            print(f"请输入开始使用时间（格式为yyyy-mm-dd hh:mm:ss，如2023-01-01 12:00:00）：")
            time = input()
            time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
            if time.hour < room["range"]["minBeginTime"] or time.hour > room["range"]["maxEndTime"]:
                raise Exception("开始时间不在房间开放时间内")
            leftTime = room["range"]["maxEndTime"] - time.hour
            hours = int(input(f"请输入使用时长（1-{leftTime},单位为小时）："))
            if hours < 1 or hours > leftTime:
                raise Exception("使用时长不合法")
            seatsInfo = self.killer.getSeatsByRoomAndFloor(roomName, floorName)
            seats = input("请输入座位号（多个座位号用逗号隔开，如1,2,3）：")
            seats = [s.strip() for s in seats.split(",") if s.strip()]
            seatsDictList = []
            for seat in seats:
                seat = str(seat)
                seatInfo = [x for x in seatsInfo if x["title"] == seat]
                if len(seatInfo) == 0:
                    raise Exception(f"{floorName}中座位{seat}不存在")
                if len(seatInfo) > 1:
                    raise Exception(f"程序错误，{floorName}中座位{seat}存在多个\n"+str(seatInfo))
                seatsDictList.append({
                    "roomName": roomName,
                    "floorName": floorName,
                    "seatId": seatInfo[0]["id"],
                    "seatNum": seatInfo[0]["title"],
                    "booker": self.killer.uid,
                    "bookerName": self.killer.name,
                })
            if len(seats) != num:
                raise Exception("座位数与人数不匹配")
            # TODO: 多人预约正确的uid
            seatBookers = (self.killer.uid, )
            self.killer.addPlan(roomName, time, hours, seatsDictList, seatBookers)
            print("添加成功")
            self.killer.saveConfig()
        except KeyboardInterrupt:
            print("已取消")
            return
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)
            return

    def deletePlan(self):
        self.killer.showPlan()
        try:
            index = input("请输入要删除的预约序号（多个用英文逗号隔开，如1,2,3）：")
            index = tuple(int(x.strip()) for x in index.split(",") if x.strip())
            if any([x > len(self.killer.plans) for x in index]):
                raise Exception(f"序号超出范围，当前共有{len(self.killer.plans)}个方案")
            if any([x < 1 for x in index]):
                raise Exception("序号不能小于1")
            index = [x-1 for x in index]
            self.killer.deletePlan(index)
            self.killer.saveConfig()
            print("删除成功")
            self.killer.showPlan()
            sleep(1)
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)
            return
        
    def setSettings(self):
        try:
            print("当前设置：")
            sleep(0.1)
            print(f"重试间隔：{self.killer.cfg['settings']['interval']}秒")
            sleep(0.1)
            print(f"最大重试次数：{self.killer.cfg['settings']['max_try_times']}次")
            sleep(0.1)
            time = input("请输入重试间隔（单位为秒），过小的重试间隔有可能导致**封号一周**的处罚，强烈建议该值不小于5秒：")
            times = input("请输入最大重试次数：")
            self.killer.cfg['settings']['interval'] = int(time)
            self.killer.cfg['settings']['max_try_times'] = int(times)
            self.killer.saveConfig()
            print("设置成功")
            sleep(1)
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
            sleep(1)
            return

if __name__ == "__main__":
    maximizeWindow()
    parse = ArgumentParser()
    parse.add_argument("-c", "--config", type=str, default="config/config.yaml", help="config file path")
    args = parse.parse_args()
    ui = UserInterface(args=args)
    ui.run()