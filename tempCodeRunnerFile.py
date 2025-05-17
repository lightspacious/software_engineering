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
        print(user.username,user.identity)

        db.session.commit()
        return jsonify({'success': True, 'message': '用户信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新用户信息失败: {str(e)}'})