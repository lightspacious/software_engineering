from flask import Flask, render_template, request, redirect, url_for,flash,session,abort
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
import random
import string

app = Flask(__name__)
app.secret_key = '123456789'

# 配置 MySQL 数据库连接
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

@app.route('/')
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
            return render_template('login.html', error="Invalid username or password")
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

@app.route('/admin')
def admin():
    if 'identity' not in session:
        return redirect(url_for('login'))
    if session['identity'] != '2':  # 仅管理员可以访问
        return "<script>alert('您无权限访问该页面！');window.history.back();</script>"
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)