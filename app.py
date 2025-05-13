from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)