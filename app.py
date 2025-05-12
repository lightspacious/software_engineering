from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/main_info')
def main_info():
    return render_template('main_info.html')

@app.route('/underwater')
def underwater():
    return render_template('underwater.html')

@app.route('/smart_center')
def smart_center():
    return render_template('smart_center.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
