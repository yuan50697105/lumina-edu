# Lumina 墨光 - 教育应用 UI 设计系统

面向高校师生的跨端教学协作平台 UI 设计原型 + 技术文档系统。

## 📱 项目概述

Lumina（墨光）是一个完整的教育应用 UI 设计系统，覆盖学生、教师、管理员三类用户，支持移动端、Web 端、桌面端三种终端形态，并配套完整的技术设计文档。

### 核心特性

- ✅ **五端覆盖**：📱 手机 / 📲 平板 / 🌐 Web / 🖥️ 桌面 / 🤖 AI
- ✅ **三类用户**：学生 / 教师 / 管理员
- ✅ **AI 原生**：集成国产大模型（通义千问、智谱 GLM、讯飞星火、豆包等）
- ✅ **双层模型选择**：管理端配置模型池 + 用户端自主选择
- ✅ **统一设计语言**：荧光笔签名效果、宣纸质感配色、跨端一致体验
- ✅ **完整技术文档**：PRD v1.3 · TDD v1.3 · API v1.4 · DB v1.4 · OPS v1.3 · QA v1.3 · UG v1.1

## 📂 项目结构

```
edu/
├── README.md                          # 本文件
├── .gitignore                         # Git 忽略规则
│
├── 原型/                              # 设计原型 + 文档
│   ├── lumina-00-index.html           # 📋 索引导航（入口）
│   ├── lumina-prd.html                # 📋 产品需求文档 PRD v1.3
│   ├── lumina-tdd.html                # 📋 技术设计文档 TDD v1.3
│   ├── lumina-api.html                # 📋 API 接口文档 v1.0
│   ├── lumina-api-openapi.yaml        # 📋 OpenAPI 3.1 规范
│   ├── lumina-database.html           # 📋 数据库设计文档 v1.0
│   ├── lumina-operations.html         # 📋 部署运维手册 v1.0
│   ├── lumina-testcases.html          # 📋 测试用例文档 v1.0
│   ├── lumina-userguide.html          # 📋 用户手册 v1.0
│   ├── lumina-launch-wbs.html         # 📋 上线 WBS v1.0
│   ├── lumina-wbs-pending.html        # 📋 未实现内容落地 WBS v1.1
│   │
│   ├── APP/phone/      (8 文件)       # 📱 手机 APP 原型
│   ├── APP/tablet/     (6 文件)       # 📲 平板 APP 原型
│   ├── Web/            (7 文件)       # 🌐 浏览器端原型
│   ├── PC/             (7 文件)       # 🖥️ 桌面端原型
│   └── AI/             (3 文件)       # 🤖 AI 模块原型
│
├── 部署/                             # Docker 部署方案（环境搭建）
│   ├── docker-compose.yml            # 服务编排（PG/Redis/单体应用/Nginx）
│   ├── .env.example                  # 环境变量模板
│   ├── config/                       # Nginx/MySQL 配置
│   ├── scripts/                      # 启停/备份/监控脚本
│   └── README.md                     # 部署使用说明
│
├── 服务/                             # 单体应用 + 前端
│   ├── lumina-app/                   # ✅ 单体 FastAPI（11 模块 · 77 端点 · 30 表）
│   ├── web-frontend/                 # ✅ Web 前端（React 18 + TS + Vite）
│   └── mobile-app/                   # ✅ 移动端前端（React Native / Expo）
│
├── 开发进度.md                       # 📈 WBS 开发进度追踪
│
└── scripts/                           # 工具脚本
    ├── yuque-sync.py                  # 🔌 语雀同步工具
    ├── yuque-config.example.json      # 配置模板
    └── README.md                      # 脚本使用说明
```

## 📊 项目统计

| 维度 | 数据 |
|------|------|
| **原型文件** | 40 个 HTML |
| **平台目录** | 5 个（phone/tablet/Web/PC/AI）|
| **界面页面** | 160+ 个 |
| **设计表面** | 6 个（学生/教师 × 移动/Web/桌面）|
| **后端模块** | 11 个业务模块（用户/课程/作业/成绩/直播/协作/AI 网关·对话·批阅/埋点/日志）|
| **文档** | PRD v1.3 + TDD v1.3 + API v1.4 + DB v1.4 + OPS v1.3 + QA v1.3 + UG v1.1 + WBS v1.1 + WBS-P v1.1 + 索引 |
| **API 接口** | 77 个端点（11 模块 · JWT · SSE 流式 · 直播课堂 · 协作工具）|
| **数据表** | 30 张（单体应用）|

## 📖 文档体系

| 文档 | 说明 | 文件 |
|------|------|------|
| 📋 **设计索引** | 原型导航入口，按平台分类 | `lumina-00-index.html` |
| 📋 **PRD v1.3** | 产品需求文档，18 章 | `lumina-prd.html` |
| 📋 **TDD v1.3** | 技术设计文档，18 章 | `lumina-tdd.html` |
| 📋 **API v1.4** | API 接口文档，12 章 · 77 端点 | `lumina-api.html` |
| 📋 **OpenAPI 3.1** | 机器可读 API 规范（YAML · 60 路径） | `lumina-api-openapi.yaml` |
| 📋 **DB v1.4** | 数据库设计文档，11 章 · 30 表 | `lumina-database.html` |
| 📋 **OPS v1.3** | 部署运维手册，10 章 | `lumina-operations.html` |
| 📋 **QA v1.3** | 测试用例文档，10 章 · 125 用例 | `lumina-testcases.html` |
| 📋 **UG v1.1** | 用户手册，10 章 · 3 角色 | `lumina-userguide.html` |
| 📋 **WBS v1.1** | 上线工作分解结构，10 周轻量方案 | `lumina-launch-wbs.html` |
| 📋 **WBS-P v1.1** | 未实现内容落地 WBS：M4 上线 + 收口认证 + V1.1 演进 | `lumina-wbs-pending.html` |

## 🎨 设计系统

### 配色方案

| 色彩 | 色值 | 用途 |
|------|------|------|
| **宣纸色** | `#FAF6EC` | 主背景 |
| **墨色** | `#0F1020` | 主文字 |
| **钴蓝** | `#3D46C9` | 品牌强调色 |
| **荧光黄** | `#F5B800` | 签名效果 |
| **警示红** | `#E85D3A` | 批注/警示 |
| **成长绿** | `#2A7F4F` | 成功/正向 |
| **AI 紫** | `#7C3AED` | AI 模块强调 |

### 字体系统

- **Fraunces** - Display 标题字体（SIL OFL 1.1）
- **Inter** - Body 正文字体（SIL OFL 1.1）
- **JetBrains Mono** - Mono 数字/代码字体（SIL OFL 1.1）
- **PingFang SC / Songti SC** - 中文 fallback（系统字体）

### 签名效果

荧光笔签名：`linear-gradient(180deg, transparent 62%, var(--highlighter) 62%, var(--highlighter) 88%, transparent 88%)`

## 🤖 AI 能力

### 国产模型池

| 模型 | 厂商 | 用途 | 成本 |
|------|------|------|------|
| 通义千问 Qwen-Max | 阿里云 | 主力 LLM | ¥0.02/千token |
| 智谱 GLM-4 | 智谱 AI | 复杂推理 | ¥0.05/千token |
| 讯飞星火 V4 | 科大讯飞 | 教育专用 | ¥0.03/千token |
| 豆包 Lite | 字节跳动 | 轻量快速 | ¥0.005/千token |
| 通义千问-VL | 阿里云 | 多模态视觉 | ¥0.08/千token |
| 讯飞语音 V3 | 科大讯飞 | 语音识别 | ¥0.33/分钟 |
| 百川 Embedding | 百川智能 | 文本嵌入 | ¥0.0007/千token |
| Kimi | 月之暗面 | 长文本 | ¥0.06/千token |

### 双层模型选择

1. **管理端配置**：管理员配置可用模型池（启用/禁用/配额/预算）
2. **用户端选择**：师生根据场景自主选择模型
3. **智能路由**：系统根据任务类型自动推荐最优模型

## 📱 平台适配

| 维度 | 📱 手机 | 📲 平板 | 🌐 Web | 🖥️ 桌面 |
|------|--------|--------|--------|--------|
| 屏幕尺寸 | ≤ 480px | 768-1024px | > 1024px | > 1280px |
| 导航结构 | 底部 5 Tab | 侧边栏 | 侧边栏 | 侧边栏 + 面包屑 |
| 布局方式 | 单列卡片 | 多列网格 | 多列网格 | 宽屏多面板 |
| 信息密度 | 紧凑优先 | 丰富展示 | 完整功能 | 专业工具 |

## 🔌 语雀同步

项目支持将文档同步到语雀知识库：

```bash
# 安装依赖
pip install requests beautifulsoup4 markdownify

# 设置 Token
export YUQUE_TOKEN="your_token"

# 运行同步
python scripts/yuque-sync.py
```

详见 `scripts/README.md`

## 🚀 使用方式

### 查看设计稿

1. 在浏览器中打开 `原型/lumina-00-index.html`
2. 通过索引页面导航到各个设计稿
3. 每个 HTML 文件可独立打开查看

### 快速部署（单体应用 · 轻量方案）

单体架构：11 个业务模块合并为 1 个 `lumina-app` API 容器，Docker Compose 一键部署，无需 K8s：

```bash
# 1. 进入部署目录
cd 部署

# 2. 配置环境变量（修改密码）
cp .env.example .env

# 3. 启动所有服务
./scripts/start.sh

# 4. 查看服务状态
./scripts/status.sh

# 5. 查看运行监控（API 请求/用户行为埋点）
./scripts/monitor.sh
```

已编排服务：MySQL 9.7 · Redis · lumina-app 单体（:8080 · 11 模块 · 77 端点）· Nginx(80/443)

详见 `部署/README.md`

### 查看文档

| 文档 | 打开方式 |
|------|----------|
| 设计索引 | `原型/lumina-00-index.html` |
| PRD 文档 | `原型/lumina-prd.html` |
| TDD 文档 | `原型/lumina-tdd.html` |
| API 文档 | `原型/lumina-api.html` |
| OpenAPI 规范 | `原型/lumina-api-openapi.yaml` |
| 数据库设计 | `原型/lumina-database.html` |
| 部署运维 | `原型/lumina-operations.html` |
| 测试用例 | `原型/lumina-testcases.html` |
| 用户手册 | `原型/lumina-userguide.html` |
| 上线 WBS | `原型/lumina-launch-wbs.html` |
| 未实现内容 WBS | `原型/lumina-wbs-pending.html` |

## 📋 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| **v1.0** | 2026-08-25 | 初始发布，24 个原型文件 |
| **v1.1** | 2026-08-25 | AI 模块新增，国产模型集成 |
| **v1.2** | 2026-08-25 | 移动端双模式适配（手机+平板） |
| **v1.3** | 2026-08-25 | 按平台目录重组，5 目录 33 文件 |
| **TDD v1.1** | 2026-08-31 | 单体架构对齐 · 去除微服务组件 |
| **API v1.0** | 2026-08-25 | API 接口文档发布，42 端点 |
| **OpenAPI 3.1** | 2026-08-25 | OpenAPI 规范文件，可生成 SDK/Mock |
| **DB v1.0** | 2026-08-25 | 数据库设计文档发布，24 表 |
| **OPS v1.0** | 2026-08-25 | 部署运维手册发布，K8s 部署 |
| **QA v1.0** | 2026-08-25 | 测试用例文档发布，156 用例 |
| **UG v1.0** | 2026-08-25 | 用户手册发布，3 角色指南 |
| **WBS v1.0** | 2026-08-26 | 上线工作分解结构发布，12 周计划 |
| **部署 v1.0** | 2026-08-26 | Docker Compose 轻量部署方案：服务编排 + 脚本 |
| **用户服务 v0.1** | 2026-08-26 | user-service 开发完成（认证·资料·监控埋点）|
| **课程服务 v0.1** | 2026-08-26 | course-service 开发完成（课程·章节·选课·公告·埋点）|
| **作业服务 v0.1** | 2026-08-26 | assignment-service 开发完成（作业·提交·批阅·埋点）|
| **成绩服务 v0.1** | 2026-08-26 | grade-service 开发完成（成绩汇总·成绩单·统计·埋点）|
| **AI 网关 v0.1** | 2026-08-26 | ai-gateway-service 开发完成（模型池·智能路由·用量）|
| **单体应用 v1.0** | 2026-08-26 | 9 微服务合并为单体 lumina-app（44 端点 · 9 模块 · 17 表 · 1 容器部署）|
| **单元测试 v1.0** | 2026-08-26 | 单体应用单元测试 76 通过 · 4 跳过；M2 里程碑达成 |
| **TDD v1.1** | 2026-08-31 | 技术设计文档单体架构对齐，去除微服务组件 |
| **API v1.2** | 2026-08-31 | API 文档生产基准升级，MySQL 9.7 · 44 端点 |
| **DB v1.2** | 2026-08-31 | 数据库文档 MySQL 9.7 口径，17 表 |
| **OPS v1.2** | 2026-08-31 | 运维手册重写为单体 Docker Compose 4 服务 |
| **QA v1.2** | 2026-08-31 | 单测基线 81 用例（bcrypt 修复后 4 跳过转通过） |
| **TDD v1.3** | 2026-08-31 | 协作模块落地同步 · 11 模块 · 77 端点 · 30 表 |
| **API v1.4** | 2026-08-31 | 协作模块章节（08 · 27 端点）· OpenAPI collab 路径 60 paths |
| **DB v1.4** | 2026-08-31 | 协作 8 表章节 · 30 表 · 11 章结构 |
| **OPS v1.3** | 2026-08-31 | 协作服务快照 · 11 模块 · 30 表 |
| **QA v1.3** | 2026-08-31 | 单测 125 用例（协作 +16 · 全部通过） |
| **WBS v1.1** | 2026-08-26 | 上线计划轻量方案更新；阶段三/四执行资产就绪（本机 MySQL 实测；真实上线待 Docker 生产环境）|
| **WBS-P v1.1** | 2026-08-31 | 未实现内容落地规划：M4 上线 + 收口认证 + V1.1 演进（33 任务包 · T0 相对周轴）|

## 📄 许可证

- **字体**：SIL OFL 1.1（Fraunces, Inter, JetBrains Mono）
- **图标**：MIT License（Feather Icons © Cole Bemis）
- **设计系统**：内部项目，商用友好

## 🤝 贡献

本项目为教学演示项目，欢迎提出建议和改进意见。

## 📧 联系

如有问题或建议，请通过 GitHub Issues 反馈。

---

**Lumina 墨光** · 让教学回归本质 ✨
