# Lumina 墨光 · UAT 验收清单（阶段三 3.6）

> 本清单对齐 **PRD v1.3** 核心场景与 **testcases 156 用例**，作为业务方（UAT 签字）的逐项验收依据。
> 自动化脚本：`部署/scripts/smoke_test.py`（全链路冒烟）· `部署/scripts/run_tests.py`（142 单测）·
> `部署/scripts/api_contract_check.py`（13→44→13 契约核对）· `部署/scripts/events_catalog.py`（52 事件目录）。

---

## 1. 用户认证与权限

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 1.1 | 学生登录 | 200 返回 access_token + user；JWT sub/role 正确 | smoke S2/S3 + unit test_security |
| 1.2 | 教师登录 | 同上（role=teacher） | smoke S2 |
| 1.3 | 管理员登录 | 同上（role=admin） | smoke S4 |
| 1.4 | 未授权访问 | 401 AUTH_TOKEN_MISSING；/users/me 无 token 返回 401 | run_tests integration |
| 1.5 | 越权拒绝 | student 访问 admin 端点返回 403 | run_tests integration |
| 1.6 | 令牌刷新 | POST /auth/refresh 正确更新 access_token | run_tests unit |

---

## 2. 课程与选课

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 2.1 | 教师建课 | 201 返回 course（code/title/semester/teacher.id） | smoke S5 |
| 2.2 | 新增章节 | 201 chapter；chapter 列表含新章节 | smoke S6 |
| 2.3 | 学生选课 | POST /enroll 200；students_count +1；重复选课 409 | smoke S7 + unit |
| 2.4 | 退课 | DELETE /enroll 200；students_count -1 | smoke S7 路径 |
| 2.5 | 课程列表 | GET /courses 200；含 code/title/teacher/semester | smoke Home load |
| 2.6 | 我的课程 | /courses/me/enrolled 只返回已选课程 | smoke Home load |

---

## 3. 作业提交与批阅

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 3.1 | 教师发布作业 | 201 assignment（title/max_score） | smoke S8 |
| 3.2 | 学生提交作业 | 201 submission（text_answer）；迟交自动标记为规则 | smoke S9 + unit |
| 3.3 | 教师批阅 | 200 grade（total_score/feedback） | smoke S10 |
| 3.4 | AI 批阅（可选） | POST /ai/grade 200；模型未配置时 502/SKIP | smoke S11 --ai |
| 3.5 | 提交列表 | GET submissions 教师可见；学生只看自己的 | run_tests integration |

---

## 4. 成绩管理

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 4.1 | 教师录入期末成绩 | 201 GradeRecord（final_score/semester）；自动计算 GPA | smoke S12 |
| 4.2 | 学生成绩单 | GET /grades/me：gpa/total_credits/courses[] 完整 | smoke S13 |
| 4.3 | 成绩统计 | /grades/statistics：平均/最高/最低/及格率/分布 | run_tests unit |
| 4.4 | 重复录入更新 | 同 student+semester upsert；旧成绩 before→after 记录埋点 | run_tests integration |

---

## 5. AI 模块（网关/对话/批阅）

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 5.1 | 模型池列表 | GET /ai/models 返回注册模型列表 | contract + integration |
| 5.2 | 运营注册模型 | POST /ai/gateway/models 201；含 api_style/protocol | run_tests gateway |
| 5.3 | AI 对话 SSE | POST /ai/chat 200；SSE 流式 token→done；conversation_id 更新 | smoke AIChat |
| 5.4 | 对话历史 | /ai/conversations 与 /{id} 消息可检索 | contract integration |
| 5.5 | 智能路由 | POST /gateway/route 按 task_type 选模型 | run_tests gateway |

---

## 6. 埋点与日志

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 6.1 | 前端埋点上报 | POST /events 202（含 page.view/auth.login 等）；events_catalog 52 事件命名合规 | smoke S14 + events_catalog |
| 6.2 | 埋点统计 | GET /events/stats 客数 distinct_users ≥ 0 | smoke S14 |
| 6.3 | 日志查询 | GET /logs/query（admin）：method/path/status/request_id 过滤有效 | smoke S15 + integration |
| 6.4 | 日志统计 | GET /logs/summary：total/errors/error_rate/top_paths | smoke S15 |
| 6.5 | 结构化 JSON 日志 | logs_service 安装 JsonFormatter：输出 JSONLines（中文/traceback/extra） | unit test_logs 16 条 |

---

## 7. 跨端体验

| # | 场景 | 通过条件 | 验证方式 |
|---|------|----------|----------|
| 7.1 | Web 页面功能完整 | 登录/首页/课程详情/AI 对话/成绩单均可操作 | contract + smoke |
| 7.2 | 移动端功能对齐 | 同上 5 页；埋点一致；API_BASE 模拟器/真机可配 | code review + README |
| 7.3 | 契约一致性 | 13 前端调用 ⊂ 44 后端端点 ⊂ Nginx 路由（全闭环） | api_contract_check |
| 7.4 | 单元测试基线 | 142 条通过，0 失败 | run_tests |

---

## ✅ UAT 签字区

| 审核方 | 意见 | 签字 | 日期 |
|--------|------|------|------|
| 业务方（教师） | | | |
| 业务方（学生代表） | | | |
| 运维负责人 | | | |
| 开发负责人 | | | |

**验收结论**：□ 通过 □ 有条件通过 □ 不通过

**遗留项**：
- 集成测试与真实冒烟（100+ 用例）待 MySQL/Docker 环境就绪后执行
- 移动端 `typecheck` 待 RN 工具链就绪后执行
- 性能测试（3.3）P99 指标待压测环境就绪后测量