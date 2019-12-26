#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: Tryrus

"""
=== 思路 ===
核心：每次落稳之后截图，根据截图算出棋子的坐标和下一个块顶面的中点坐标，
    根据两个点的水平距离乘以一个时间系数获得长按的时间

识别棋子：使用cv2.matchTemplate函数来识别

识别棋盘：靠底色和方块的色差来做，从分数之下的位置开始，一行一行扫描，
    由于圆形的块最顶上是一条线，方形的上面大概是一个点，所以就
    用类似识别棋子的做法多识别了几个点求中点，这时候得到了块中点的 X
    轴坐标，这时候假设现在棋子在当前块的中心，根据一个通过截图获取的
    固定的角度来推出中点的 Y 坐标

最后：根据两点的坐标算水平距离乘以系数来获取长按时间
"""

from __future__ import print_function, division
import os
import time
import cv2
from PIL import Image
import random

VERSION = "1.1.4"
template = cv2.imread('./image/character.png')
template_size = template.shape[:2]


def check_screenshot():
    try:
        pull_screenshot()
    except Exception:
        print('请确认已经连接上手机，并且adb可用')


def pull_screenshot():
    os.system('adb shell screencap -p /sdcard/autojump.png')
    os.system('adb pull /sdcard/autojump.png ./autojump.png')


# 搜索棋子在图片中的位置，并计算出棋子中点的坐标
def find_piece(im, template):
    result = cv2.matchTemplate(im, template, cv2.TM_SQDIFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    return im, min_loc[0] + template_size[1] / 2


def find_board(im, piece_x):  # 寻找终点坐标
    w, h = im.size  # 图片宽高
    im_pixel = im.load()

    piece_width = w // 14  # 估算棋子宽度
    # 寻找落点
    board_x = 0
    # 限制棋盘扫描的横坐标 避免音符bug
    if piece_x < w / 2:
        board_x_start, board_x_end = w // 2, w  # 起点和终点的中点是画面中心
    else:
        board_x_start, board_x_end = 0, w // 2

    # 寻找落点顶点
    board_x_set = []  # 目标坐标集合/改为list避免去重
    for by in range((h - w) // 2, (h + w) // 2, 4):
        bg_pixel = im_pixel[0, by]
        for bx in range(board_x_start, board_x_end):
            pixel = im_pixel[bx, by]
            # 修掉脑袋比下一个小格子还高的情况 屏蔽小人左右的范围
            if abs(bx - piece_x) < piece_width:
                continue

            # 修掉圆顶的时候一条线导致的小bug 这个颜色判断应该OK
            if (abs(pixel[0] - bg_pixel[0]) +
                    abs(pixel[1] - bg_pixel[1]) +
                    abs(pixel[2] - bg_pixel[2]) > 10):
                board_x_set.append(bx)

        if len(board_x_set) > 10:
            board_x = sum(board_x_set) / len(board_x_set)
            print('%-12s %s' % ('target_x:', board_x))
            break  # 找到了退出

    return board_x


def set_button_position(im, gameover=0):  # 重设点击位置 再来一局位置
    w, h = im.size
    if h // 16 > w // 9 + 2:  # 长窄屏 2px容差 获取ui描绘的高度
        uih = int(w / 9 * 16)
    else:
        uih = h

    # 如果游戏结束 点击再来一局
    left = int(w / 2)  # 按钮半宽
    # 根据9:16实测按钮高度中心0.825 按钮半高
    top = int((h - uih) / 2 + uih * 0.825)
    if gameover:
        return left, top

    # 游戏中点击 随机位置防 ban
    left = random.randint(w // 4, w - 20)  # 避开左下角按钮
    top = random.randint(h * 3 // 4, h - 20)
    return left, top


def jump(piece_x, board_x, im, swipe_x1, swipe_y1):
    distanceX = abs(board_x - piece_x)  # 起点到目标的水平距离
    shortEdge = min(im.size)  # 屏幕宽度
    jumpPercent = distanceX / shortEdge  # 跳跃百分比
    jumpFullWidth = 1700  # 跳过整个宽度 需要按压的毫秒数
    press_time = round(jumpFullWidth * jumpPercent)  # 按压时长
    press_time = 0 if not press_time else max(
        press_time, 200)  # press_time大于0时限定最小值
    print('%-12s %.2f%% (%s/%s) | Press: %sms' %
          ('Distance:', jumpPercent * 100, distanceX, shortEdge, press_time))

    cmd = 'adb shell input swipe {x1} {y1} {x2} {y2} {duration}'.format(
        x1=swipe_x1,
        y1=swipe_y1,
        x2=swipe_x1 + random.randint(-10, 10),  # 模拟位移
        y2=swipe_y1 + random.randint(-10, 10),
        duration=press_time
    )
    print(cmd)
    os.system(cmd)


def main():
    check_screenshot()  # 检查截图

    count = 0
    while True:
        count += 1
        print('---\n%-12s %s (%s)' % ('Times:', count, time.asctime( time.localtime(time.time()))))

        # 获取截图
        pull_screenshot()

        # 找出棋子的位置，也就是第一个点的X轴的坐标
        im = cv2.imread('autojump.png')
        img, piece_x= find_piece(im,template)

        # 找出棋盘位置，也就是第二个点的X轴坐标
        im = Image.open('./autojump.png')
        board_x = find_board(im, piece_x)

        # 检查游戏是否结束
        gameover = 0 if all((piece_x, board_x)) else 1
        swipe_x1, swipe_y1 = set_button_position(
            im, gameover=gameover)  # 随机点击位置

        jump(piece_x, board_x, im, swipe_x1, swipe_y1)

        # 等待时间，用于抓取更清晰的图片
        wait = (random.random())**5 * 5 + 2  # 停2~5秒 指数越高平均间隔越短
        print('---\nWait %.3f s...' % wait)
        time.sleep(wait)
        print('Continue!')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os.system('adb kill-server')
        print('bye')
        exit(0)
