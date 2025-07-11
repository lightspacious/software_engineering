from sklearn.decomposition import PCA
# from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from flask import Flask, render_template, request, redirect, url_for,flash,session,abort, jsonify, Response, stream_with_context
from flask_cors import CORS # 用于处理跨域请求，开发时可能需要
import os
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
import random
import string
import psutil

import requests
import base64
import cv2
import tempfile
import json
import time

app = Flask(__name__)
app.secret_key = '123456789'

#鱼类识别api_key  secret_key  赠送 10000 次
API_KEY = "sI7jkJ8is6ei4xQWRoOfCKBU"
SECRET_KEY = "ezsAUibMpFUR63cN5AmoQ6ZceFrdopXp"


# 设置管理员身份###############################
# @app.before_request
# def fake_login_as_admin():
#     session['username'] = '1'
#     session['identity'] = '1'
# 用于避开登陆界面并获得管理员权限##################

# 配置 MySQL 数据库连接
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/ocean_user'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:001108@localhost/ocean user'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 用户模型
class User(db.Model):
    __tablename__ = 'user'
    userid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    identity = db.Column(db.CHAR(1), nullable=False)
    online = db.Column(db.Boolean, default=False, nullable=False)
    mail = db.Column(db.String(255))
    # farm = db.Column(db.Integer)
CORS(app)

# @app.route('/')
def index():
    return redirect(url_for('login')) 


# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        passwd = request.form['password']
        user = User.query.filter_by(username=uname).first()
        if user and user.password == passwd:
            user.online = True  # 设置为在线
            session['username'] = uname
            session['identity'] = user.identity  # 传递身份
            db.session.commit()  # 保存状态
            return redirect(url_for('main_info')) 
        else:
            return render_template('login.html', error="账号不存在或密码错误")
    return render_template('login.html')

#跳转注册页面
@app.route('/sign')
def sign_up():
    return render_template('sign.html')  

#跳转找回密码页面
@app.route('/forgot')
def forgot_password():
    return render_template('forgot.html')  

#注册
@app.route('/signinsign', methods=['GET', 'POST'])
def signinsign_up():
    if request.method == 'POST':
        username = request.form.get('signusername')
        password = request.form.get('signpassword')
        email = request.form.get('signemail')
        identity = request.form.get('identity')  # 获取用户类型
        code = request.form.get('code')  # 获取特权码

        if not username or not password or not email:
            return render_template('sign.html', error="请填写所有字段")
        
        # 验证特权码（仅对养殖户和管理员有效）
        if identity == '1':  # 养殖户
            if not code:
                return render_template('sign.html', error="请输入特权码")
            # 根据身份生成特权码
            if code != "13579":
                return render_template('sign.html', error="特权码不正确")
        if identity == '2':  #或管理员
            if not code:
                return render_template('sign.html', error="请输入特权码")
            # 根据身份生成特权码
            if code != "02468":
                return render_template('sign.html', error="特权码不正确")

        # 检查用户是否已存在
        if User.query.filter_by(username=username).first():
            return render_template('sign.html', error="用户名已存在")
        
        # 随机生成唯一的userid
        while True:
            userid = ''.join(random.choices(string.digits, k=6))  # 生成6位随机数字
            if not User.query.filter_by(userid=userid).first():  # 确保userid不重复
                break

        # 添加新用户（身份identity设为'1'，在线状态online设为'0'）
        new_user = User(
            userid=userid,
            username=username,
            password=password,
            identity=identity,
            online=False,
            mail=email
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('sign.html')

# @app.route('/')
@app.route('/main_info')
def main_info():
    if 'identity' not in session:
        return redirect(url_for('login'))
    return render_template('main_info.html')

@app.route('/underwater')
def underwater():
    #权限判断
   
    if 'identity' not in session:
        return redirect(url_for('login'))
    if session['identity'] not in ['1', '2']:  # 普通用户无权访问
        return "<script>alert('您无权限访问该页面！');window.history.back();</script>"

    # 1. 读取 CSV 数据
    df = pd.read_csv('Fish.csv')

    # —— 环形图需要的统计数据 —— 
    counts = df['Species'].value_counts()
    species_data = [
        {'name': name, 'value': int(count)}
        for name, count in counts.items()
    ]
    species_total = int(counts.sum())

    # —— 3D 气泡图需要的完整记录 & 菜单列表 —— 
    species_list = sorted(df['Species'].unique())
    fish_records = df[['Species','Weight(g)','Length1(cm)','Width(cm)']]\
                   .rename(columns={
                       'Species': 'species',  
                       'Weight(g)': 'weight',
                       'Length1(cm)': 'length',
                       'Width(cm)': 'width'
                   })\
                   .to_dict(orient='records')

    # 统一传入模板
    return render_template(
        'underwater.html',
        # 环形图
        species_data=species_data,
        species_total=species_total,
        # 3D 气泡图
        species_list=species_list,
        fish_records=fish_records
    )

@app.route('/smart_center')
def smart_center():


    if 'identity' not in session:
        return redirect(url_for('login'))
    if session['identity'] not in ['1', '2']:  # 普通用户无权访问
        return "<script>alert('您无权限访问该页面！');window.history.back();</script>"
    return render_template('smart_center.html')

@app.route('/')
@app.route('/data_center')
def data_center():


    if 'identity' not in session:
        return redirect(url_for('login'))
    if session['identity'] not in ['1', '2']:  # 普通用户无权访问
        return "<script>alert('您无权限访问该页面！');window.history.back();</script>"
    return render_template('data_center.html')

@app.route('/admin')
def admin():
    if 'identity' not in session:
        return redirect(url_for('login'))
    if session['identity'] != '2':  # 仅管理员可以访问
        return "<script>alert('您无权限访问该页面！');window.history.back();</script>"

    # 查询所有用户数据
    users = User.query.all()
    return render_template('admin.html', users=users)

# 获取用户信息
@app.route('/get_user', methods=['GET'])
def get_user():
    try:
        user_id = request.args.get('userid')
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID参数'})

        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        # 返回用户信息（不包括密码）
        return jsonify({
            'success': True,
            'user': {
                'userid': user.userid,
                'username': user.username,
                'identity': user.identity,
                'mail': user.mail
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户信息失败: {str(e)}'})


# 编辑用户
@app.route('/edit_user', methods=['POST'])
def edit_user():
    try:
        data = request.form
        user_id = data.get('userid')
        username = data.get('username')
        identity = data.get('identity')

        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        print(user.username, user.identity)
        # 更新用户信息
        user.username = username
        user.identity = identity
        session['identity'] = identity
        session['username'] = username
        print(user.username,user.identity)

        db.session.commit()
        return jsonify({'success': True, 'message': '用户信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新用户信息失败: {str(e)}'})


# 删除用户
@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        user_id = request.form.get('userid')

        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        # 删除用户
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': '用户删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除用户失败: {str(e)}'})


def generate_dummy_devices():
    """生成模拟设备数据"""
    devices = []
    device_types = ['摄像机', '灯光', '清洁刷', '传感器']
    for i in range(4):
        devices.append({
            'type': device_types[i],
            'device_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=12)),
            'status': '正常' if random.random() > 0.1 else '异常',
            'version': f'V0.1.{random.randint(1, 5)}',
            'temperature': f'{round(random.uniform(35.0, 45.0), 2)}℃'
        })
    return devices
#smart_center app.py修改部分开始


@app.route('/logout')
def logout():
    if 'username' in session:
        # 获取当前用户
        username = session['username']
        # 查找用户并设置在线状态为 False
        user = User.query.filter_by(username=username).first()
        if user:
            user.online = False
            db.session.commit()
    # 清除会话
    session.clear()
    return redirect(url_for('login'))

#异常检测逻辑
def detect_anomalies_with_data(df):
    data_with_anomalies = []
    for idx, row in df.iterrows():
        issues = []
        is_anomaly = False # 标记该行数据整体是否异常

        # 水温检测
        try:
            water_temp = float(row['水温(℃)'])
            if not (15 <= water_temp <= 35):
                issues.append(f"水温异常: {water_temp}℃")
                is_anomaly = True
        except (ValueError, TypeError):
            issues.append("水温数据无效")
            is_anomaly = True

        # pH检测
        try:
            ph_value = float(row['pH(无量纲)'])
            if not (6.5 <= ph_value <= 8.5):
                issues.append(f"pH异常: {ph_value}")
                is_anomaly = True
        except (ValueError, TypeError):
            issues.append("pH数据无效")
            is_anomaly = True

        # 溶解氧检测
        try:
            dissolved_oxygen = float(row['溶解氧(mg/L)'])
            if dissolved_oxygen < 5:
                issues.append(f"溶解氧过低: {dissolved_oxygen} mg/L")
                is_anomaly = True
        except (ValueError, TypeError):
            issues.append("溶解氧数据无效")
            is_anomaly = True

        # 藻密度缺失检测 (示例)
        if pd.isnull(row.get('藻密度(cells/L)')) or str(row.get('藻密度(cells/L)')).strip() == '--':
            issues.append("藻密度缺失")
            # is_anomaly = True # 根据你的需求决定缺失是否算作需要高亮的异常

        # 准备每一行的数据，包括原始值和异常信息
        # 确保所有预期的列都存在，即使它们是 None 或 NaN
        data_point = {
            "监测时间": row.get("监测时间"),
            "断面名称": row.get("断面名称"),
            "水温": row.get('水温(℃)'), # 发送原始值
            "pH": row.get('pH(无量纲)'),    # 发送原始值
            "溶解氧": row.get('溶解氧(mg/L)'),# 发送原始值
            "藻密度": row.get('藻密度(cells/L)'),
            "is_anomaly": is_anomaly,
            "issues": issues if issues else ["正常"] # 如果没有问题，则为正常
        }
        data_with_anomalies.append(data_point)
    return data_with_anomalies

# --- API 接口 ---
@app.route("/get_water_quality_data", methods=['GET'])
def get_water_quality_data():
    
    province = request.args.get('province')
    basin = request.args.get('basin')
    section = request.args.get('section')
    month = '2021-04'
    file_name = f"{section}.csv"

    # 构造文件路径
    file_path = os.path.join("static\dataset\水质数据\data_smart", province, basin, section, month, file_name)
    
    # 检查文件是否存在
    if os.path.exists(file_path):
        # 读取 CSV 文件并返回数据
        df = pd.read_csv(file_path)
        # 转换数值列，处理可能的错误
        df['水温(℃)'] = pd.to_numeric(df['水温(℃)'], errors='coerce')
        df['pH(无量纲)'] = pd.to_numeric(df['pH(无量纲)'], errors='coerce')
        df['溶解氧(mg/L)'] = pd.to_numeric(df['溶解氧(mg/L)'], errors='coerce')
       
        # 进行异常检测并将结果附加到数据中
        processed_data = detect_anomalies_with_data(df)
        return jsonify(processed_data)
    else :
        return jsonify({"error": "CSV file not found"}), 404
  
@app.route('/get_data', methods=['GET'])
def get_data():
    province = request.args.get('province')
    basin = request.args.get('basin')
    section = request.args.get('section')
    month = '2021-04'
    file_name = f"{section}.csv"

    # 构造文件路径
    file_path = os.path.join("static\dataset\水质数据\data_smart", province, basin, section, month, file_name)
    print(file_path)
    
    # 检查文件是否存在
    if os.path.exists(file_path):
        # 读取 CSV 文件并返回数据
        data = pd.read_csv(file_path)
        return jsonify(data.to_dict(orient='records'))
    else:
        return jsonify({"error": "Data not found"}), 404

@app.route('/get_fish_data')
def get_fish_data():
    df = pd.read_csv('Fish.csv')  # 确保文件路径正确
    # print(df.columns

    df.columns = [col.lower().strip().replace('(g)', '').replace('(cm)', '').replace(' ', '') for col in df.columns]
    # df = df[['species', 'length1', 'weight', 'width']]
    # df = df.rename(columns={
    #     'length1': 'length'
    # })
    return jsonify(df.to_dict(orient='records'))

@app.route('/get_pca_data')
def get_pca_data():
    try:
        # 1. 读取CSV文件
        csv_path = "Fish.csv"
        df = pd.read_csv(csv_path, encoding='utf-8-sig', sep=',')

        # 2. PCA数据准备
        features = ['Weight(g)', 'Length1(cm)', 'Length2(cm)', 'Length3(cm)', 'Height(cm)', 'Width(cm)']
        df_pca = df.dropna(subset=features).copy()
        
        # 3. 数据标准化和PCA降维
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_pca[features])
        
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        # 4. 构建返回数据
        pca_data = []
        for i, row in df_pca.iterrows():
            pca_data.append({
                "species": row['Species'],
                "pc1": float(X_pca[i, 0]),
                "pc2": float(X_pca[i, 1])
            })

        # # 5. 异常检测
        # dbscan = DBSCAN(eps=0.5, min_samples=5)
        # labels = dbscan.fit_predict(X_pca)
        # outliers = df_pca[labels == -1].to_dict('records')

        return jsonify({
            "success": True,
            "pca_data": pca_data,
            # "outliers": outliers,
            "explained_variance": pca.explained_variance_ratio_.tolist()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    

@app.route('/perform_pca', methods=['POST'])
def perform_pca():
    try:
        # 1. 获取 JSON 数据并转为 DataFrame
        json_data = request.get_json()
        data = json_data['fish_data']
        df = pd.DataFrame(data)
        # print("收到的数据列：", data)
        print("收到的数据列：", df.columns.tolist())

        # 2. 字段名统一处理（小写）
        df.columns = [col.lower() for col in df.columns]

        # 3. 提取用于 PCA 的列
        features = ['length1','length2','length3', 'weight', 'width','height']
        df_pca = df.dropna(subset=features).copy()
        X = df_pca[features].astype(float)

        # 4. 执行标准化和 PCA
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        # 5. 构建返回结果
        result = []
        for i, row in df_pca.iterrows():
            result.append({
                'species': row.get('species', 'Unknown'),
                'pc1': float(X_pca[i, 0]),
                'pc2': float(X_pca[i, 1])
            })

        return jsonify({
            'success': True,
            'pca_data': result,
            'explained_variance': pca.explained_variance_ratio_.tolist()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/hard_status')
def get_hardstatus():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
    # GPU 示例：暂时用随机数模拟（可以接入 NVIDIA SMI 等工具）
    gpu_percent = 30 + random.randint(-5, 5)  # 假设值

    return jsonify({
        'cpu': cpu_percent,
        'mem': mem_percent,
        'gpu': gpu_percent
    })


# @app.route('/offline', methods=['POST'])
# def offline():
#     if 'username' in session:
#         username = session['username']
#         user = User.query.filter_by(username=username).first()
#         if user:
#             user.online = False
#             db.session.commit()
#         return '', 204
#     return '', 401

def get_access_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"
    response = requests.post(url).json()
    return response.get("access_token")

def recognize_animal(image_base64):
    access_token = get_access_token()
    url = f"https://aip.baidubce.com/rest/2.0/image-classify/v1/animal?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        "image": image_base64,
        "top_num": 1,
        "baike_num": 1
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json()

def analyze_fish(result):
    try:
        name = result["result"][0]["name"]
        fish_id = f"fish-{random.randint(1000, 9999)}"
        length = round(random.uniform(18, 45), 1)
        weight = round(length * random.uniform(15, 25), 1)
        has_disease = random.random() < 0.2
        disease = random.choice(["鳃部发白", "体表溃疡", "眼球混浊", "肠炎"]) if has_disease else ""
        has_anomaly = random.random() < 0.2
        anomaly = random.choice(["翻肚行为", "游动缓慢", "体表擦伤", "颜色发白", "体型瘦小"]) if has_anomaly else ""

        return {
            "编号": fish_id,
            "识别结果": name,
            "推测体长": f"{length} cm",
            "推测体重": f"{weight} g",
            "健康状态": "患病 - " + disease if has_disease else "健康",
            "异常状态": anomaly if has_anomaly else "正常"
        }

    except Exception as e:
        return {"error": "识别失败", "detail": str(e)}


@app.route("/stream_analyze_video")
def stream_analyze_video():
    video_path = request.args.get("video_path", "static/movie/1.mp4")

    def generate():
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        interval = int(fps * 3)
        frame_id = 0

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break
                if frame_id % interval == 0:
                    _, buffer = cv2.imencode('.jpg', frame)
                    img_base64 = base64.b64encode(buffer).decode()

                    result = recognize_animal(img_base64)
                    analysis = analyze_fish(result)
                    analysis["时间点"] = f"{frame_id // fps:.1f}s"
                    analysis["frame"] = img_base64

                    yield f"data: {json.dumps(analysis)}\n\n"
                    time.sleep(1)
                frame_id += 1
        except GeneratorExit:
            print("客户端主动关闭 SSE")
        finally:
            cap.release()

    return Response(stream_with_context(generate()), content_type='text/event-stream')

#smart_center app.py修改部分结束



# underwater 鱼类运动轨迹追踪部分 start####################

def draw_axes(image, length_ratio=0.25, tick_count=5, origin_padding=(50, 50), scale=1.0):
    """
    在图像左下角绘制坐标轴，自动适配图像尺寸。
    - length_ratio: 坐标轴长度占图像宽/高的比例（0~1）
    - tick_count: 刻度数
    - origin_padding: 距离左/下边缘的像素偏移
    - scale: 像素→物理单位的比例尺（每 scale 像素 = 1 单位）
    """
    h, w = image.shape[:2]
    ox, oy = origin_padding
    x0, y0 = ox, h - oy  # 左下角为原点

    axis_length_x = int(w * length_ratio)
    axis_length_y = int(h * length_ratio)

    tick_step_x = axis_length_x // tick_count
    tick_step_y = axis_length_y // tick_count

    color = (0, 0, 0)  # 黑色坐标轴
    font = cv2.FONT_HERSHEY_SIMPLEX

    # X 轴
    cv2.arrowedLine(image, (x0, y0), (x0 + axis_length_x, y0), color, 1, tipLength=0.02)
    for i in range(tick_count + 1):
        x = x0 + i * tick_step_x
        cv2.line(image, (x, y0 - 5), (x, y0 + 5), color, 1)
        cv2.putText(image, f"{int(i * tick_step_x / scale)}", (x - 15, y0 - 15), font, 0.4, color, 1)

    # Y 轴
    cv2.arrowedLine(image, (x0, y0), (x0, y0 - axis_length_y), color, 1, tipLength=0.02)
    for i in range(tick_count + 1):
        y = y0 - i * tick_step_y
        cv2.line(image, (x0 - 5, y), (x0 + 5, y), color, 1)
        cv2.putText(image, f"{int(i * tick_step_y / scale)}", (x0 + 10, y + 11), font, 0.4, color, 1)

# —— 视频追踪轨迹流函数（封装后可复用） ——
def fish_track_stream(video_path='top_view.mp4', max_len=20, memory=30, min_area=200, fps=30, search_range=20):
    import cv2
    import numpy as np
    import pandas as pd
    import trackpy as tp

    def id_to_color(pid):
        np.random.seed(pid)
        return tuple(int(x) for x in np.random.randint(0, 255, size=3))

    def preprocess_tracking(video_path, memory, min_area):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("无法打开视频")

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

        records = []
        frames = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fg = fgbg.apply(gray)
            _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)))
            cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in cnts:
                if cv2.contourArea(c) < min_area:
                    continue
                M = cv2.moments(c)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                records.append({'frame': frame_idx, 'x': cx, 'y': cy})
            frame_idx += 1
            frames.append(frame)

        cap.release()
        df = pd.DataFrame(records)
        t = tp.link_df(df, search_range, memory=memory)
        t = tp.filter_stubs(t, threshold=5)

        unique_ids = sorted(t['particle'].unique())
        color_map = {pid: id_to_color(pid) for pid in unique_ids}
        return frames, t, color_map, w, h

    def stream_generator():
        frames, t, color_map, w, h = preprocess_tracking(video_path, memory, min_area)
        frame_idx = len(frames)
        trail = np.full((h, w, 3), (255, 255, 255), dtype=np.uint8)  # 白色背景
        # 调整为统一大小
        # OUTPUT_SIZE = (640, 480)  
        # trail = np.full((OUTPUT_SIZE[1], OUTPUT_SIZE[0], 3), (255, 255, 255), dtype=np.uint8) # 白色背景
        i = 0
        while True:
            trail[:] = (255, 255, 255)
            # for pid in color_map:
            #     recent = t[(t.particle == pid) & (t.frame <= i) & (t.frame > i - max_len)]
            #     pts = recent[['x', 'y']].values.astype(np.int32)
            #     if len(pts) > 1:
            #         cv2.polylines(trail, [pts], False, color_map[pid], 2)
            for pid in color_map:
                recent = t[(t.particle == pid) & (t.frame <= i) & (t.frame > i - max_len)]
                recent_sorted = recent.reset_index(drop=True).sort_values(by='frame')  # 确保按时间顺序画

                for j, row in enumerate(recent_sorted.itertuples()):
                    x, y = int(row.x), int(row.y)

                    # 帧越新，weight 越大
                    weight = (j + 1) / len(recent_sorted)  # 0~1之间
                    radius = int(2 + 4 * weight)           # 半径：2~6 像素
                    alpha = 0.2 + 0.8 * weight             # 透明度：0.2~1.0

                    # 原始颜色
                    color = np.array(color_map[pid], dtype=np.float32)
                    blended_color = (1 - alpha) * np.array([139, 0, 0]) + alpha * color  # 混入背景色
                    blended_color = tuple(map(int, blended_color))

                    # 画圆点（越新越亮、越大）
                    cv2.circle(trail, (x, y), radius, blended_color, -1)
            # 添加坐标轴
            draw_axes(trail, length_ratio=1, tick_count=10, origin_padding=(0, 1), scale=20.0)   

            # 编码发送
            ret, jpeg = cv2.imencode('.jpg', trail)
            if not ret:
                continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            i = (i + 1) % frame_idx
            cv2.waitKey(int(1000 / fps))

    return stream_generator

# 俯视轨迹
@app.route('/video_feed_top')
def video_feed_top():
    return Response(
        fish_track_stream(video_path='top_view2.mp4')(),  # 调用返回生成器
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# 正视轨迹
@app.route('/video_feed_front')
def video_feed_front():
    return Response(
        fish_track_stream(video_path='front_view2.mp4')(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# underwater 鱼类运动轨迹追踪部分 end####################


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5200, debug=True)