# Lumina 墨光 · 埋点事件目录

> 自动生成：`python 部署/scripts/events_catalog.py`（阶段三 3.2 埋点数据验证依据）

## 事件命名规范
`namespace.action`（点分小写）；允许命名空间：ai, announcement, assignment, auth, chapter, chat, collab, conversation, course, element, enrollment, exam, gateway, grade, live, model, notif, page, provider, session, submission, system, user

## 全量事件清单

| 事件 | 端 | 出现位置 |
|------|----|---------|
| `ai.call` | 后端 | modules/ai_gateway/routers.py |
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
| `auth.login_fail` | 前端 | mobile-app/src/pages/Login.tsx |
| `auth.logout` | 前端 | web-frontend/src/components/Layout.tsx |
| `chapter.created` | 后端 | instrumentation.py |
| `chapter.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/CourseDetail.tsx |
| `collab.card_create` | 前端 | web-frontend/src/pages/GroupDetail.tsx |
| `collab.card_move` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `collab.column_add` | 前端 | web-frontend/src/pages/GroupDetail.tsx |
| `collab.file_download` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `collab.file_upload` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `collab.group_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Groups.tsx |
| `collab.group_join` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx, web-frontend/src/pages/Groups.tsx |
| `collab.group_leave` | 后端 | instrumentation.py |
| `collab.group_list` | 前端 | web-frontend/src/pages/Groups.tsx |
| `collab.group_view` | 前端 | web-frontend/src/pages/GroupDetail.tsx |
| `collab.project_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `collab.project_open` | 前端 | web-frontend/src/pages/GroupDetail.tsx |
| `collab.reply_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `collab.topic_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/GroupDetail.tsx |
| `course.created` | 后端 | instrumentation.py |
| `course.drop` | 后端 | instrumentation.py |
| `course.enroll` | 前端/后端 | instrumentation.py, mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `course.unenroll` | 前端 | mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `course.updated` | 后端 | instrumentation.py |
| `course.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Home.tsx |
| `element.click` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/utils/tracker.ts |
| `exam.attempt_list` | 后端 | instrumentation.py |
| `exam.attempt_start` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.attempt_submit` | 前端/后端 | instrumentation.py, web-frontend/src/pages/ExamTaking.tsx |
| `exam.attempt_view` | 前端/后端 | instrumentation.py, web-frontend/src/pages/ExamTaking.tsx |
| `exam.manual_grade` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.paper_add_question` | 前端 | web-frontend/src/pages/Exam.tsx |
| `exam.paper_close` | 后端 | instrumentation.py |
| `exam.paper_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.paper_delete` | 后端 | instrumentation.py |
| `exam.paper_generate` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.paper_publish` | 后端 | instrumentation.py |
| `exam.paper_update` | 后端 | instrumentation.py |
| `exam.paper_view` | 后端 | instrumentation.py |
| `exam.question_create` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.question_delete` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `exam.question_update` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Exam.tsx |
| `grade.recorded` | 后端 | instrumentation.py |
| `grade.statistics` | 后端 | instrumentation.py |
| `grade.updated` | 后端 | instrumentation.py |
| `grade.view` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Grades.tsx |
| `live.call` | 后端 | instrumentation.py |
| `live.call_respond` | 后端 | instrumentation.py |
| `live.chat` | 后端 | instrumentation.py |
| `live.join` | 后端 | instrumentation.py |
| `live.leave` | 后端 | instrumentation.py |
| `live.quiz_answer` | 后端 | instrumentation.py |
| `live.quiz_close` | 后端 | instrumentation.py |
| `live.quiz_start` | 后端 | instrumentation.py |
| `live.raise_hand` | 后端 | instrumentation.py |
| `live.room_create` | 前端/后端 | instrumentation.py, mobile-app/src/pages/CourseDetail.tsx, web-frontend/src/pages/CourseDetail.tsx |
| `live.room_end` | 后端 | instrumentation.py |
| `live.room_start` | 后端 | instrumentation.py |
| `live.room_view` | 前端 | mobile-app/src/pages/CourseDetail.tsx, mobile-app/src/pages/LiveRoom.tsx, web-frontend/src/pages/LiveRoom.tsx |
| `model.register` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `model.toggle` | 前端 | web-frontend/src/pages/AdminModels.tsx |
| `notif.read` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Dashboard.tsx |
| `notif.read_all` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Dashboard.tsx |
| `notif.view` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Dashboard.tsx |
| `page.view` | 前端 | mobile-app/src/utils/tracker.ts, web-frontend/src/components/Layout.tsx |
| `user.login` | 后端 | instrumentation.py |
| `user.login_fail` | 后端 | instrumentation.py |
| `user.logout` | 前端/后端 | instrumentation.py, mobile-app/src/pages/Home.tsx |
| `user.password_change` | 后端 | instrumentation.py |
| `user.profile_update` | 后端 | instrumentation.py |
| `user.register` | 前端/后端 | instrumentation.py, web-frontend/src/pages/Login.tsx |
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
- `collab.card_create`
- `collab.card_move`
- `collab.column_add`
- `collab.file_download`
- `collab.file_upload`
- `collab.group_create`
- `collab.group_join`
- `collab.group_list`
- `collab.group_view`
- `collab.project_create`
- `collab.project_open`
- `collab.reply_create`
- `collab.topic_create`
- `course.enroll`
- `course.unenroll`
- `course.view`
- `element.click`
- `exam.attempt_start`
- `exam.attempt_submit`
- `exam.attempt_view`
- `exam.manual_grade`
- `exam.paper_add_question`
- `exam.paper_create`
- `exam.paper_generate`
- `exam.question_create`
- `exam.question_delete`
- `exam.question_update`
- `grade.view`
- `live.room_create`
- `live.room_view`
- `model.register`
- `model.toggle`
- `notif.read`
- `notif.read_all`
- `notif.view`
- `page.view`
- `user.logout`
- `user.register`

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
- `collab.group_leave`
- `course.created`
- `course.drop`
- `course.updated`
- `exam.attempt_list`
- `exam.paper_close`
- `exam.paper_delete`
- `exam.paper_publish`
- `exam.paper_update`
- `exam.paper_view`
- `grade.recorded`
- `grade.statistics`
- `grade.updated`
- `live.call`
- `live.call_respond`
- `live.chat`
- `live.join`
- `live.leave`
- `live.quiz_answer`
- `live.quiz_close`
- `live.quiz_start`
- `live.raise_hand`
- `live.room_end`
- `live.room_start`
- `user.login`
- `user.login_fail`
- `user.password_change`
- `user.profile_update`
- `user.token_refresh`
- `user.view`

## 前端页面视图覆盖（trackPageView 参数）

- `ai_chat`
- `course_detail`
- `grades`
- `home`
- `live_room`