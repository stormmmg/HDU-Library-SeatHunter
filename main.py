'''
Author: littleherozzzx zhou.xin2022.code@outlook.com
Date: 2023-01-12 16:38:00
LastEditTime: 2023-02-02 18:02:32
Software: VSCode
'''
import os
import sys
import ast

from time import sleep
from pwinput import pwinput
from datetime import datetime
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





class UserInterface:
    def __init__(self, args=None):
        self.configFile = os.path.join(get_app_dir(), "config", "config.yaml") if args is None else args.config
        self.killer = Killer()
        self.funcs = [self.changePlan, self.changeTime, self.startNow, self.startAt,self.setSettings, self.help, self.exit]
    
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
        while not flag:
            if self.killer.userInfo["login_name"]  and self.killer.userInfo["password"] :
                if self.killer.login():
                    print("登录成功")
                    self.killer.saveConfig()
                    self.th = Thread(target=self.killer.updateRooms)
                    self.th.start()
                    flag = True
                else:
                    print("配置文件中账号密码错误，请重新输入")
                    self.setUserInfo()
            else:
                self.setUserInfo()
    
    def showMenu(self):
        print("1. 查看/添加/删除待选座位方案")   
        print("2. 批量修改方案中预约时间")
        print("3. 立即开始抢座")
        print("4. 定时抢座")
        print("5. 修该请求间隔和次数")
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
            index = index+"," if index[-1] != "," else index
            index = ast.literal_eval(f"({index})")
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
             
    def startNow(self):
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
                    input("按回车键退出")
                    return
                else:
                    print(f"\r第{i+1}个方案预约失败，原因为："+"\033[0;31m%s\033[0m" % res['MESSAGE'])
                sleep(self.killer.cfg["settings"]["interval"])
                    
    def startAt(self):
        try:
            startTime = input("请输入程序开始运行时间（格式为yyyy-mm-dd hh:mm:ss，如2023-01-01 12:00:00）：")
            startTime = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            if startTime < datetime.now():
                raise Exception("开始时间不能小于当前时间")
            print(f"在倒计时过程中，您可以使用Ctrl+C终止程序")
            while True:
                if datetime.now() >= startTime:
                    break
                now = datetime.now().replace(microsecond=0)
                left = int((startTime-datetime.now()).total_seconds())
                if left < 60:
                    print(f"\r当前时间为{now}，预约开始时间为{startTime}，还有{left}秒，请耐心等待", end="", flush=True)
                elif left < 3600:
                    print(f"\r当前时间为{now}，预约开始时间为{startTime}，还有{left//60}分{left%60}秒，请耐心等待", end="", flush=True)
                else:
                    print(f"\r当前时间为{now}，预约开始时间为{startTime}，还有{left//3600}时{left%3600//60}分{left%60}秒，请耐心等待", end="", flush=True)
                sleep(1)
            self.startNow()
        except KeyboardInterrupt:
            print("程序终止")
            return
        except Exception as e:
            print("\033[0;31m%s\033[0m" % e)
            print("输入错误，取消本次操作")
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
            seats = seats+"," if seats[-1] != "," else seats
            seats = ast.literal_eval(f"({seats})")
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
            index = index+"," if index[-1] != "," else index
            index = ast.literal_eval(f"({index})")
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