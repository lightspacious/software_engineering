import cv2
import numpy as np
import pandas as pd
import trackpy as tp
import matplotlib.pyplot as plt

# —— 配置参数 ——
VIDEO_PATH   = 'top_view2.mp4'  # 视频路径（俯视角）
MIN_AREA     = 200             # 忽略较小的轮廓区域（像素面积）
SEARCH_RANGE = 15              # Trackpy 连续帧之间的最大移动距离
MEMORY       = 10               # 允许追踪对象在最多3帧内缺失后仍连接轨迹
FPS_DISPLAY  = 30              # 视频播放帧率
MAX_LEN      = 20              # 每条轨迹保留的最近帧数（即滑动窗口长度）

def id_to_color(pid):
    np.random.seed(pid)  # 每个ID生成固定颜色
    return tuple(int(x) for x in np.random.randint(0, 255, size=3))


# —— 1. 读取视频 & 背景分割 ——
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise IOError(f"无法打开视频文件: {VIDEO_PATH}")

# 获取视频宽高
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# 创建背景建模器
fgbg = cv2.createBackgroundSubtractorMOG2(
    history=500, varThreshold=50, detectShadows=False
)

records = []     # 保存所有检测到的质心点
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # 转灰度图
    fg = fgbg.apply(gray)  # 背景建模
    _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)  # 二值化
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)))  # 去噪声
    
    cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 找轮廓

    for c in cnts:
        if cv2.contourArea(c) < MIN_AREA:
            continue
        M = cv2.moments(c)
        cx = int(M['m10']/M['m00'])  # 质心 x
        cy = int(M['m01']/M['m00'])  # 质心 y
        records.append({'frame': frame_idx, 'x': cx, 'y': cy})
    
    frame_idx += 1

cap.release()

# 构建 DataFrame 供 Trackpy 使用
df = pd.DataFrame(records)

# —— 2. Trackpy 串帧追踪 ——
t = tp.link_df(df, SEARCH_RANGE, memory=MEMORY)  # 粒子追踪
t = tp.filter_stubs(t, threshold=5)              # 滤除长度过短的轨迹

# —— 粒子颜色配置 —— 
unique_ids = sorted(t['particle'].unique())
cmap = plt.get_cmap('hsv', len(unique_ids))  # 使用 HSV 颜色映射
color_map = {
    pid: tuple(int(c*255) for c in cmap(i)[:3])  # 转为 BGR 颜色值（OpenCV使用）
    for i, pid in enumerate(unique_ids)
}
# color_map = {pid: id_to_color(pid) for pid in unique_ids}
# 可以替换 cmap 为 plt.get_cmap('jet'), 'tab10', 'rainbow' 等

# —— 3. 轨迹绘制 —— 
#trail = np.zeros((h, w, 3), dtype=np.uint8)  # 黑色背景画布
trail = np.full((h, w, 3), (139, 0, 0), dtype=np.uint8)  # 初始化为深蓝色背景
# 若想更换背景颜色，例如白色： trail.fill(255)
# 或自定义蓝色： trail[:] = (255, 255, 200)

cv2.namedWindow('Trail_Top', cv2.WINDOW_NORMAL)

# 遍历所有帧，动态绘制轨迹
for i in range(frame_idx):
    # trail.fill(0)  # 每帧清空画布；更改此处即可修改“画布颜色”
    trail[:] = (139, 0, 0)
    for pid in unique_ids:
        recent = t[
            (t.particle == pid) &
            (t.frame <= i) &
            (t.frame > i - MAX_LEN)
        ]
        pts = recent[['x', 'y']].values.astype(np.int32)
        if len(pts) > 1:
            # 绘制轨迹
            cv2.polylines(trail, [pts], False, color_map[pid], 2)
    cv2.imshow('Trail_Top', trail)
    if cv2.waitKey(int(1000/FPS_DISPLAY)) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()