from flask import Flask, render_template, jsonify,request
from flask_cors import CORS # 用于处理跨域请求，开发时可能需要

import os
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/')
@app.route('/main_info')
def main_info():
    return render_template('main_info.html')

@app.route('/underwater')
def underwater():
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
    return render_template('smart_center.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

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
    # print(df.columns)

    df.columns = [col.lower().strip().replace('(g)', '').replace('(cm)', '').replace(' ', '') for col in df.columns]
    df = df[['species', 'length1', 'weight', 'width']]
    df = df.rename(columns={
        'length1': 'length'
    })
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)