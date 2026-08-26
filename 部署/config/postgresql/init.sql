-- ============================================
-- Lumina 墨光 - PostgreSQL 初始化脚本
-- 创建基础表结构，首次启动时自动执行
-- ============================================

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 用户模块
-- ============================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id    VARCHAR(20) UNIQUE,
    name          VARCHAR(50) NOT NULL,
    email         VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'student'
                  CHECK (role IN ('student', 'teacher', 'admin')),
    department    VARCHAR(100),
    grade         VARCHAR(10),
    avatar_url    VARCHAR(500),
    bio           TEXT,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 用户索引
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);

-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(500) UNIQUE NOT NULL,
    device        VARCHAR(20) DEFAULT 'web',
    ip_address    VARCHAR(45),
    user_agent    TEXT,
    expires_at    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- 课程模块
-- ============================================

-- 课程表
CREATE TABLE IF NOT EXISTS courses (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code           VARCHAR(20) UNIQUE NOT NULL,
    title          VARCHAR(200) NOT NULL,
    description    TEXT,
    teacher_id     UUID REFERENCES users(id),
    department     VARCHAR(100),
    credits        DECIMAL(3,1),
    semester       VARCHAR(20) NOT NULL,
    schedule       JSONB,
    students_count INTEGER DEFAULT 0,
    status         VARCHAR(20) DEFAULT 'draft'
                   CHECK (status IN ('draft', 'published', 'archived')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 课程索引
CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester);
CREATE INDEX IF NOT EXISTS idx_courses_teacher ON courses(teacher_id);
CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department);

-- 选课表
CREATE TABLE IF NOT EXISTS enrollments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    role        VARCHAR(20) DEFAULT 'student'
                CHECK (role IN ('student', 'teacher', 'ta')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status      VARCHAR(20) DEFAULT 'active'
                CHECK (status IN ('active', 'dropped', 'completed')),
    UNIQUE (user_id, course_id)
);

-- 章节表
CREATE TABLE IF NOT EXISTS chapters (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title       VARCHAR(200) NOT NULL,
    content     TEXT,
    order_num   INTEGER DEFAULT 0,
    resources   JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- 作业模块
-- ============================================

-- 作业表
CREATE TABLE IF NOT EXISTS assignments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id    UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    due_at       TIMESTAMPTZ,
    max_score    INTEGER DEFAULT 100,
    ai_grading   BOOLEAN DEFAULT false,
    rubric       JSONB,
    ai_model     VARCHAR(50),
    status       VARCHAR(20) DEFAULT 'published'
                 CHECK (status IN ('draft', 'published', 'closed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 提交表
CREATE TABLE IF NOT EXISTS submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_urls       JSONB,
    text_answer     TEXT,
    submission_note TEXT,
    late            BOOLEAN DEFAULT false,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 提交索引
CREATE INDEX IF NOT EXISTS idx_sub_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_sub_student ON submissions(student_id);

-- ============================================
-- 成绩模块
-- ============================================

-- 成绩表
CREATE TABLE IF NOT EXISTS grades (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
    total_score   DECIMAL(5,2),
    grade_letter  VARCHAR(2),
    feedback      TEXT,
    rubric_scores JSONB,
    graded_by     VARCHAR(10) DEFAULT 'teacher'
                  CHECK (graded_by IN ('teacher', 'ai')),
    grader_id     UUID REFERENCES users(id),
    ai_model      VARCHAR(50),
    confidence    DECIMAL(3,2),
    graded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- AI 模块
-- ============================================

-- AI 对话表
CREATE TABLE IF NOT EXISTS ai_conversations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title             VARCHAR(200),
    model             VARCHAR(50),
    context_course_id UUID,
    context_chapter_id UUID,
    message_count     INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AI 对话索引
CREATE INDEX IF NOT EXISTS idx_ai_conv_user ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conv_updated ON ai_conversations(updated_at DESC);

-- AI 消息表
CREATE TABLE IF NOT EXISTS ai_messages (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role               VARCHAR(20) NOT NULL
                       CHECK (role IN ('user', 'assistant', 'system')),
    content            TEXT,
    attachments        JSONB,
    prompt_tokens      INTEGER DEFAULT 0,
    completion_tokens  INTEGER DEFAULT 0,
    latency_ms         INTEGER DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- 埋点数据表（监控埋点）
-- ============================================

-- 事件埋点表
CREATE TABLE IF NOT EXISTS event_tracking (
    id         BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    user_id    UUID,
    session_id VARCHAR(100),
    course_id  UUID,
    properties JSONB,
    page_url   VARCHAR(500),
    user_agent TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 埋点索引
CREATE INDEX IF NOT EXISTS idx_event_name ON event_tracking(event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_user ON event_tracking(user_id, created_at DESC);

-- 接口访问日志表
CREATE TABLE IF NOT EXISTS api_logs (
    id          BIGSERIAL PRIMARY KEY,
    method      VARCHAR(10) NOT NULL,
    path        VARCHAR(500) NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    user_id     UUID,
    request_id  VARCHAR(100),
    error_message TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 接口日志索引
CREATE INDEX IF NOT EXISTS idx_api_logs_created ON api_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_path ON api_logs(path, created_at DESC);

-- ============================================
-- 初始数据（演示账户）
-- ============================================

-- 管理员账户
INSERT INTO users (student_id, name, email, password_hash, role, department)
VALUES
  ('admin', '系统管理员', 'admin@lumina.edu',
   crypt('Admin@123456', gen_salt('bf')), 'admin', '信息中心')
ON CONFLICT (email) DO NOTHING;

-- 演示教师
INSERT INTO users (student_id, name, email, password_hash, role, department)
VALUES
  ('T1001', '王建国', 'wjg@lumina.edu',
   crypt('Teacher@123', gen_salt('bf')), 'teacher', '计算机科学与技术'),
  ('T1002', '李慧', 'lihui@lumina.edu',
   crypt('Teacher@123', gen_salt('bf')), 'teacher', '数学系')
ON CONFLICT (email) DO NOTHING;

-- 演示学生
INSERT INTO users (student_id, name, email, password_hash, role, department, grade)
VALUES
  ('2023010001', '林清', 'linqing@lumina.edu',
   crypt('Student@123', gen_salt('bf')), 'student', '计算机科学与技术', '2023'),
  ('2023010002', '陈曦', 'chenxi@lumina.edu',
   crypt('Student@123', gen_salt('bf')), 'student', '计算机科学与技术', '2023')
ON CONFLICT (email) DO NOTHING;