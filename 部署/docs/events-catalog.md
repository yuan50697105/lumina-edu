# Lumina 墨光 · 埋点事件目录

> 自动生成：`python 部署/scripts/events_catalog.py`（阶段三 3.2 埋点数据验证依据）

## 事件命名规范
`namespace.action`（点分小写）；允许命名空间：ai, announcement, assignment, auth, chapter, chat, conversation, course, element, enrollment, gateway, grade, model, page, provider, session, submission, system, user

## 全量事件清单

| 事件 | 端 | 出现位置 |
|------|----|---------|
| `ai.call` | 后端 | routers/ai_gateway.py |
| `ai.call_recorded` | 后端 | instrumentation.py |
| `ai.chat.done` | 前端 | mobile-app/src/pages/AIChat.tsx, web-frontend/src/pages/AIChat.tsx |
| `ai.chat.open` | 前端 | mobile-app/src/pages/CourseDetail.tsx |
| `ai.chat.send` | 前端 | mobile-app/src/pages/AIChat.tsx, web-frontend/src/pages/AIChat.tsx |
| `ai.chat_done` | 后端 | instrumentation.py |
| `ai.chat_error` | 后端 | instrumentation.py |
| `ai.chat_start` | 后端 | instrumentation.py |
| `ai.conversation_delete` | 后端 | instrumentation.py |
| `ai.conversation_list` | 后端 | instrumentation.py |
| `ai.conversation_view` | 后端 | instrumentation.py |
| `ai.grade_done` | 后端 | instrumentation.py |
| `ai.grade_error` | 后端 | instrumentation.py |
| `ai.grade_start` | 后端 | instrumentation.py |
| `ai.model_registered` | 后端 | instrumentation.py |
| `ai.model_updated` | 后端 | instrumentation.py |
| `ai.models_view` | 后端 | instrumentation.py |
| `ai.route` | 后端 | instrumentation.py |
| `ai.usage_view` | 后端 | instrumentation.py |
| `announcement.created` | 后端 | instrumentation.py |
| `assignment.created` | 后端 | instrumentation.py |
| `assignment.graded` | 后端 | instrumentation.py |
| `assignment.submitted` | 后端 | instrumentation.py |
| `assignment.updated` | 后端 | instrumentation.py |
| `assignment.view` | 后端 | instrumentation.py |
| `auth.login` | 前端 | mobile-app/src/pages/Login.tsx, web-frontend/src/pages/Login.tsx |
| `auth.login_fail` | 前端 | mobile-app/src/pages/Login.tsx, web-frontend/src/pages/Login.tsx |
| `auth.logout` | 前端 | web-frontend/src/components/Layout.tsx |
| `chapter.created` | 后端 | instrumentation.py |
| `chapter.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/CourseDetail.tsx |
| `course.created` | 后端 | instrumentation.py |
| `course.drop` | 后端 | instrumentation.py |
| `course.enroll` | 前端/后端 | instrumentation.py, mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `course.unenroll` | 前端 | mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `course.updated` | 后端 | instrumentation.py |
| `course.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Home.tsx |
| `element.click` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/utils/tracker.ts |
| `grade.recorded` | 后端 | instrumentation.py |
| `grade.statistics` | 后端 | instrumentation.py |
| `grade.updated` | 后端 | instrumentation.py |
| `grade.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Grades.tsx |
| `model.register` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `model.toggle` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `page.view` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/components/Layout.tsx |
| `user.login` | 后端 | instrumentation.py |
| `user.login_fail` | 后端 | instrumentation.py |
| `user.logout` | 前端/后端 | mobile-app/src/pages/Home.tsx, instrumentation.py |
| `user.password_change` | 后端 | instrumentation.py |
| `user.profile_update` | 后端 | instrumentation.py |
| `user.register` | 后端 | instrumentation.py |
| `user.token_refresh` | 后端 | instrumentation.py |
| `user.view` | 后端 | instrumentation.py |

## 前端产生的业务事件（3.2 联调验证清单）

- `ai.chat.done`
- `ai.chat.open`
- `ai.chat.send`
- `auth.login`
- `auth.login_fail`
- `auth.logout`
- `chapter.view`
- `course.enroll`
- `course.unenroll`
- `course.view`
- `element.click`
- `grade.view`
- `model.register`
- `model.toggle`
- `page.view`
- `user.logout`

## 后端埋点常量（Instrumentation）

- `ai.call`
- `ai.call_recorded`
- `ai.chat_done`
- `ai.chat_error`
- `ai.chat_start`
- `ai.conversation_delete`
- `ai.conversation_list`
- `ai.conversation_view`
- `ai.grade_done`
- `ai.grade_error`
- `ai.grade_start`
- `ai.model_registered`
- `ai.model_updated`
- `ai.models_view`
- `ai.route`
- `ai.usage_view`
- `announcement.created`
- `assignment.created`
- `assignment.graded`
- `assignment.submitted`
- `assignment.updated`
- `assignment.view`
- `chapter.created`
- `chapter.view`
- `course.created`
- `course.drop`
- `course.enroll`
- `course.updated`
- `course.view`
- `grade.recorded`
- `grade.statistics`
- `grade.updated`
- `grade.view`
- `user.login`
- `user.login_fail`
- `user.logout`
- `user.password_change`
- `user.profile_update`
- `user.register`
- `user.token_refresh`
- `user.view`

## 前端页面视图覆盖（trackPageView 参数）

- `ai_chat`
- `course_detail`
- `grades`
- `home`