from flask import Flask, render_template, request, jsonify
from datetime import date
import models
import scheduler

app = Flask(__name__)


@app.before_request
def ensure_db():
    models.init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/today')
def api_today():
    today = date.today()
    plans = scheduler.get_today_plan(today)
    return jsonify({
        'date': today.isoformat(),
        'is_rest_day': models.is_rest_day(today.isoformat()),
        'plans': [{
            'task_id': p['task']['id'],
            'task_name': p['task']['name'],
            'unit': p['task']['unit'],
            'total': p['task']['total'],
            'completed': p['task']['completed'],
            'planned': p['planned'],
            'actual': p['actual'],
            'checked_in': p['checked_in'],
            'deadline': p['task']['deadline'],
        } for p in plans]
    })


@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    tasks = models.get_all_tasks()
    today = date.today()
    result = []
    for task in tasks:
        daily = scheduler.calculate_daily_plan(task, today)
        deadline = date.fromisoformat(task['deadline'])
        days_left = (deadline - today).days
        result.append({
            **task,
            'daily_plan': daily,
            'days_left': days_left,
            'progress': round(task['completed'] / task['total'] * 100, 1) if task['total'] > 0 else 0,
        })
    return jsonify(result)


@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    data = request.get_json()
    name = data.get('name', '').strip()
    unit = data.get('unit', '题').strip()
    total = int(data.get('total', 0))
    start_date = data.get('start_date', date.today().isoformat())
    deadline = data.get('deadline', '')

    if not name or total <= 0 or not deadline:
        return jsonify({'error': '请填写完整信息'}), 400

    task_id = models.create_task(name, unit, total, start_date, deadline)
    return jsonify({'id': task_id, 'message': '创建成功'}), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def api_get_task(task_id):
    task = models.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    today = date.today()
    daily = scheduler.calculate_daily_plan(task, today)
    logs = models.get_task_logs(task_id)

    return jsonify({
        **task,
        'daily_plan': daily,
        'logs': logs,
    })


@app.route('/api/tasks/<int:task_id>/checkin', methods=['POST'])
def api_checkin(task_id):
    task = models.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    data = request.get_json()
    actual = int(data.get('actual', 0))
    today = date.today().isoformat()

    models.checkin(task_id, today, actual)
    return jsonify({'message': '打卡成功', 'actual': actual})


@app.route('/api/tasks/<int:task_id>/rest', methods=['POST'])
def api_mark_rest(task_id):
    today = date.today().isoformat()
    models.set_rest_day(today)
    return jsonify({'message': '已标记今天为休息日', 'date': today})


@app.route('/api/rest', methods=['POST'])
def api_rest_today():
    today = date.today().isoformat()
    models.set_rest_day(today)
    return jsonify({'message': '已标记今天为休息日', 'date': today})


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    task = models.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    models.delete_task(task_id)
    return jsonify({'message': '删除成功'})


if __name__ == '__main__':
    models.init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)
