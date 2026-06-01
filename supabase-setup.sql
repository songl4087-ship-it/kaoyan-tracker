-- 在 Supabase SQL Editor 中执行此脚本来创建表

CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT '题',
    total INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    start_date TEXT NOT NULL,
    deadline TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE daily_logs (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    actual INTEGER,
    UNIQUE(task_id, date)
);

CREATE TABLE weekly_rests (
    id BIGSERIAL PRIMARY KEY,
    week_start TEXT NOT NULL UNIQUE,
    rest_date TEXT NOT NULL
);

-- 开启 Row Level Security 但允许匿名访问（个人工具，无需登录）
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_rests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on tasks" ON tasks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on daily_logs" ON daily_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on weekly_rests" ON weekly_rests FOR ALL USING (true) WITH CHECK (true);
