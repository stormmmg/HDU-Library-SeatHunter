# 杭州电子科技大学图书馆抢座脚本

## 脚本介绍

作者发现github上的抢座脚本都停止维护，不能使用了，所以写了本项目。
本脚本用于杭电图书馆自习室座位预约，目前支持自动登录、批量预约、定时预约等功能，有以下模块：

* 查看/添加/删除待选座位方案
* 批量修改方案中预约时间
* 定时抢座
* 自定义抢座

**本脚本仅限用于个人图书馆预约座位，请勿恶意囤座位！**

## 运行说明

0. 本脚本基于Python 3.14编写，请先安装Python 3.14。
1. 克隆本项目

``` shell
git clone https://github.com/stormmmg/HDU-Library-SeatHunter.git
cd HDU-Library-SeatHunter
```

2. 安装依赖项

```shell
pip install -r requirements.txt
```

3. 运行脚本

``` shell
python main.py
```

4.构建 exe

``` python
python build.py
```

5. 根据软件提示登录、查看使用说明。
   
本脚本基于https://github.com/LittleHeroZZZX/hdu-library-killer改进
