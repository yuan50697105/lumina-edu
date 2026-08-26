# Lumina 墨光 · 埋点事件目录

> 自动生成：`python 部署/scripts/events_catalog.py`（阶段三 3.2 埋点数据验证依据）

## 事件命名规范
`namespace.action`（点分小写）；允许命名空间：ai, announcement, assignment, auth, chapter, chat, conversation, course, element, enrollment, gateway, grade, model, page, provider, session, submission, system, user

## 全量事件清单

| 事件 | 端 | 出现位置 |
|------|----|---------|
| `ai.call` | 后端 | modules/ai_gateway/routers.py |
| `ai.call_recorded` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `ai.chat.done` | 前端 | mobile-app/src/pages/AIChat.tsx, web-frontend/src/pages/AIChat.tsx |
| `ai.chat.open` | 前端 | mobile-app/src/pages/CourseDetail.tsx |
| `ai.chat.send` | 前端 | mobile-app/src/pages/AIChat.tsx, web-frontend/src/pages/AIChat.tsx |
| `ai.chat_done` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.chat_error` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.chat_start` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.conversation_delete` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.conversation_list` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.conversation_view` | 后端 | instrumentation.py, modules/ai_chat/instrumentation.py |
| `ai.grade_done` | 后端 | instrumentation.py, modules/ai_grade/instrumentation.py |
| `ai.grade_error` | 后端 | instrumentation.py, modules/ai_grade/instrumentation.py |
| `ai.grade_start` | 后端 | instrumentation.py, modules/ai_grade/instrumentation.py |
| `ai.model_registered` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `ai.model_updated` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `ai.models_view` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `ai.route` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `ai.usage_view` | 后端 | instrumentation.py, modules/ai_gateway/instrumentation.py |
| `announcement.created` | 后端 | instrumentation.py, modules/course/instrumentation.py |
| `assignment.created` | 后端 | instrumentation.py, modules/assignment/instrumentation.py |
| `assignment.graded` | 后端 | instrumentation.py, modules/assignment/instrumentation.py |
| `assignment.submitted` | 后端 | instrumentation.py, modules/assignment/instrumentation.py |
| `assignment.updated` | 后端 | instrumentation.py, modules/assignment/instrumentation.py |
| `assignment.view` | 后端 | instrumentation.py, modules/assignment/instrumentation.py |
| `auth.login` | 前端 | mobile-app/src/pages/Login.tsx, web-frontend/src/pages/Login.tsx |
| `auth.login_fail` | 前端 | mobile-app/src/pages/Login.tsx, web-frontend/src/pages/Login.tsx |
| `auth.logout` | 前端 | web-frontend/src/components/Layout.tsx |
| `chapter.created` | 后端 | instrumentation.py, modules/course/instrumentation.py |
| `chapter.view` | 前端/后端 | instrumentation.py, modules/course/instrumentation.py, mobile-app/src/pages/CourseDetail.tsx |
| `course.created` | 后端 | instrumentation.py, modules/course/instrumentation.py |
| `course.drop` | 后端 | instrumentation.py, modules/course/instrumentation.py |
| `course.enroll` | 前端/后端 | instrumentation.py, modules/course/instrumentation.py, mobile-app/src/pages/CourseDetail.tsx |
| `course.unenroll` | 前端 | mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `course.updated` | 后端 | instrumentation.py, modules/course/instrumentation.py |
| `course.view` | 前端/后端 | instrumentation.py, modules/course/instrumentation.py, mobile-app/src/pages/Home.tsx |
| `element.click` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/utils/tracker.ts |
| `grade.recorded` | 后端 | instrumentation.py, modules/grade/instrumentation.py |
| `grade.statistics` | 后端 | instrumentation.py, modules/grade/instrumentation.py |
| `grade.updated` | 后端 | instrumentation.py, modules/grade/instrumentation.py |
| `grade.view` | 前端/后端 | instrumentation.py, modules/grade/instrumentation.py, mobile-app/src/pages/Grades.tsx |
| `model.register` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `model.toggle` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `page.view` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/components/Layout.tsx |
| `user.login` | 后端 | instrumentation.py |
| `user.login_fail` | 后端 | instrumentation.py |
| `user.logout` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Home.tsx |
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


## 前端页面视图覆盖（trackPageView 参数）

- `ai_chat`
- `course_detail`
- `grades`
- `home`