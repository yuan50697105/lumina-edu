# ============================================
# Lumina 墨光 · 移动端（Expo / React Native）
# WBS 2.9 前端移动端开发 + 埋点
# ============================================

跨端 APP 骨架，功能与 Web 端对齐，复用同一后端契约（9 个微服务 + Nginx 网关 + 统一埋点 `/api/v1/events`）。

## 页面

| 页面 | 功能 | 后端端点 |
|------|------|---------|
| 登录 | 学号/邮箱 + 密码（device=mobile）| `POST /auth/login` |
| 首页 | 全部课程 / 我的课程 切换 + 下拉刷新、退出 | `GET /courses`、`/courses/me/enrolled` |
| 课程详情 | 课程信息、章节列表、选课/退课 | `GET /courses/{id}`、`/courses/{id}/chapters`、`POST|DELETE /courses/{id}/enroll` |
| AI 导师 | SSE 流式对话（XHR 增量读取，适配 RN 无 ReadableStream）| `POST /ai/chat` |
| 成绩单 | GPA / 总学分 / 课程明细 | `GET /grades/me` |

## 埋点（对齐 Web tracker.ts 契约）

`src/utils/tracker.ts`：事件 `POST {API_BASE}/api/v1/events`（`event_tracking` 表）。
- 无 `sendBeacon`/`localStorage` → 用 fetch 实时上报；失败进**内存队列**，下轮上报前 flush（进程内重试）
- `page.view`（页面进入时）、`element.click`（显式调用）、`auth.login`、`course.enroll/unenroll`、`ai.chat.send/done`、`grade.view`
- session_id 进程内随机 UUID；登录用户由 `lumina-mobile-auth` user.id 带入，JWT 权威覆盖

## 运行

前置：Expo 工具链（未含在本仓库，需 `.meteor` 无 —— 见下）与后端服务在线。

```bash
cd 服务/mobile-app
npm install            # 或 yarn
npm run start          # Expo dev server，扫码 / 模拟器打开
```

### API 地址

`src/config.ts` 的 `API_BASE`：
- iOS 模拟器：`http://localhost:8080`
- Android 模拟器：`http://10.0.2.2:8080`
- 真机：宿主机局域网 IP（后端需允许外网访问）

### 类型检查

```bash
npm run typecheck      # tsc --noEmit（需先 npm install）
```

## ⚠️ 工程状态说明

本仓库开发环境**无 React Native 构建工具链**（npm/node_modules 未安装），因此：

- 交付为**完整可编译的代码骨架**（TS 类型/导航/请求/埋点已对齐后端契约）
- 类型检查与真机构建验证需在安装依赖后的 RN 环境执行：`npm install && npm run typecheck`
- 集成到 CI 时，建议代码评审通过后由具备 RN 环境的节点跑 typecheck 门禁

## 目录

```
mobile-app/
├── App.tsx                 # 导航 + 登录守卫
├── app.json                # Expo 配置
├── src/
│   ├── config.ts           # API_BASE（模拟器/真机）
│   ├── navigation.ts       # 导航类型
│   ├── api/client.ts       # fetch 封装（324 JWT 注入 · 401 登出）
│   ├── api/types.ts        # 后端契约类型（与 Web 对齐）
│   ├── store/auth.ts       # zustand + AsyncStorage 持久化
│   ├── utils/tracker.ts    # 埋点 SDK（fetch + 内存队列）
│   └── pages/              # 登录/首页/课程详情/AI 对话/成绩单
└── package.json
```