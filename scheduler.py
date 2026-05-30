import math
from datetime import date, timedelta
import models


def get_week_start(d):
    return d - timedelta(days=d.weekday())


def count_future_rest_days(start, end):
    """计算从 start 到 end 之间预计的休息日数量"""
    rest_days = models.get_rest_days()
    confirmed_rests = set()
    for r in rest_days:
        rd = date.fromisoformat(r['rest_date'])
        if start <= rd <= end:
            confirmed_rests.add(rd)

    count = len(confirmed_rests)

    current = start
    while current <= end:
        ws = get_week_start(current)
        week_end = ws + timedelta(days=6)
        if ws not in {get_week_start(d) for d in confirmed_rests}:
            effective_start = max(current, ws)
            effective_end = min(end, week_end)
            if effective_start <= effective_end:
                days_in_week = (effective_end - effective_start).days + 1
                if days_in_week >= 3:
                    count += 1
        current = week_end + timedelta(days=1)

    return count


def calculate_daily_plan(task, today=None):
    """计算某个任务今天应该做多少"""
    if today is None:
        today = date.today()

    remaining = task['total'] - task['completed']
    if remaining <= 0:
        return 0

    deadline = date.fromisoformat(task['deadline'])
    start_date = date.fromisoformat(task['start_date'])

    if today < start_date:
        return 0

    if today > deadline:
        return remaining

    if models.is_rest_day(today.isoformat()):
        return 0

    days_left = (deadline - today).days + 1
    if days_left <= 0:
        return remaining

    rest_days = count_future_rest_days(today, deadline)
    working_days = days_left - rest_days

    if working_days <= 0:
        working_days = 1

    daily_amount = math.ceil(remaining / working_days)
    return daily_amount


def get_today_plan(today=None):
    """获取今日所有任务的计划"""
    if today is None:
        today = date.today()

    tasks = models.get_all_tasks()
    plans = []

    for task in tasks:
        daily_amount = calculate_daily_plan(task, today)
        log = models.get_daily_log(task['id'], today.isoformat())
        plans.append({
            'task': task,
            'planned': daily_amount,
            'actual': log['actual'] if log else None,
            'is_rest_day': models.is_rest_day(today.isoformat()),
            'checked_in': log is not None and log['actual'] is not None,
        })

    return plans
