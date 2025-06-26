#!/usr/bin/env python3
"""
Top-view 和 Front-view 的鱼类轨迹实时跟踪
- 强化分割：闭开运算 + 中值滤波 + 膨胀
- Norfair 卡尔曼滤波跟踪：更长的丢帧容忍
- 仅显示独立空白画布上的滑动轨迹

用法:
    python fish_track_norfair.py top
    python fish_track_norfair.py front
"""
import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt
from norfair import Detection, Tracker
from collections import defaultdict, deque

# 全局参数：可根据实际视频分辨率和鱼体大小调整
MIN_AREA       = 100    # 最小轮廓面积，鱼体较小时可调小
MAX_LEN        = 20     # 滑动窗口保留轨迹点数
DIST_THRESH    = 50     # 卡尔曼滤波最大预测移动距离
HIT_COUNTER_MAX = 10    # 丢失帧容忍量
INIT_DELAY     = 2      # 新目标初始化延迟帧数
FPS_DISPLAY    = 30     # 显示帧率

# 使用内置向量化欧氏距离，提升性能
tracker = Tracker(
    distance_function="euclidean",
    distance_threshold=DIST_THRESH,
    hit_counter_max=HIT_COUNTER_MAX,
    initialization_delay=INIT_DELAY
)

# 轨迹存储：每个 ID 一个滑动窗口队列
trajectories = defaultdict(lambda: deque(maxlen=MAX_LEN))

def track_video(video_path, mode="top"):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"无法打开视频: {video_path}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 前景建模与核
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))

    win_name = 'Trail_Top' if mode=='top' else 'Trail_Front'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fg   = fgbg.apply(gray)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  kernel, iterations=2)
        fg = cv2.dilate(fg, kernel, iterations=1)      # 膨胀连接断裂
        fg = cv2.medianBlur(fg, 5)

        # 检测质心并生成 Norfair Detection
        detections = []
        cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) < MIN_AREA:
                continue
            M = cv2.moments(c)
            cx = M['m10']/M['m00']
            cy = M['m01']/M['m00']
            # top: (x,y)， front: (x,z)
            pt = np.array([cx, cy])
            detections.append(Detection(points=pt))

        tracked = tracker.update(detections=detections)

        # 绘制空白画布上的滑动窗口轨迹
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        for tobj in tracked:
            x, y = tobj.estimate[0]
            trajectories[tobj.id].append((int(x), int(y)))
            pts = np.array(trajectories[tobj.id], dtype=np.int32)
            color = tuple((np.array(plt.get_cmap('tab20')(tobj.id % 20)[:3]) * 255).astype(int))
            if len(pts) > 1:
                cv2.polylines(canvas, [pts], False, color, 2)

        # 显示轨迹画布（无原视频）
        cv2.imshow(win_name, canvas)
        if cv2.waitKey(int(1000/FPS_DISPLAY)) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('top','front'):
        print("用法: python fish_track_norfair.py [top|front]")
        sys.exit(1)
    mode = sys.argv[1]
    video = 'top_view.mp4' if mode=='top' else 'front_view.mp4'
    track_video(video, mode)