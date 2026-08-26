# Lumina 墨光 · web-frontend Web 端（React 18 + TypeScript + Vite）

响应式 SPA：登录/课程/章节/AI 导师（SSE 流式）/成绩单/模型池配置（运营端）+ 埋点 SDK。

## 技术栈

React 18.3 · TypeScript 5.6 · Vite 5 · React Router v6 · Zustand（认证）· 原生 fetch

## 页面

| 路径 | 说明 |
|------|------|
| `/login` | 登录（学号/邮箱 + 密码 → JWT 双令牌） |
| `/` | 首页：我的课程 + 课程广场 |
| `/courses/:id` | 课程详情（章节 + 选课/退课） |
| `/ai` | AI 导师：苏格拉底式 SSE 流式对话 + 会话历史 |
| `/grades` | 成绩单（GPA / 学分 / 课程明细） |
| `/admin/models` | 模型池配置（运营端）：供应商 + 模型注册/启停/协议风格 |

## 埋点 SDK（`src/utils/tracker.ts`）

- **页面访问**：路由变化 → `page.view` 事件（session_id + page_url + user_id）
- **元素点击**：全局捕获 `data-track="…"` 属性 → `element.click` 事件
- **发送**：优先 `sendBeacon`，回退 `fetch keepalive`，失败入 `localStorage` 队列下次重试
- **端点**：`POST /api/v1/events`（事件结构对齐 `event_tracking` 表；由 2.10 埋点收集服务消费）

## 本地运行

```bash
cd ../服务/web-frontend
npm install
npm run dev      # http://localhost:5173（/api 代理到 http://localhost:8080）
```

需先启动后端：`部署/docker compose up -d` 或本地起 user-service（:8080）。

## 构建

```bash
npm run build    # 产物 dist/（tsc 类型检查 + vite）
npm run preview  # 本地预览
```

## 测试

无运行时 UI 测试框架；类型安全由 `npm run build` 的 `tsc -b` 保证。埋点/API 层联调见 2.12。

## 部署

`Dockerfile` 多阶段：node 构建 → nginx 托管 `dist/`。随 2.12 联调接入 compose/Nginx。