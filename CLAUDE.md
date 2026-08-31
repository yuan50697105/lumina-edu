# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lumina (墨光) 教育应用 UI 设计系统 - 面向高校师生的跨端教学协作平台。本项目为设计原型 + 技术文档 + FastAPI 单体应用（`服务/lumina-app/`）。单体快照：77 RESTful 端点 · 11 模块 · 30 表（模块：user / course / assignment / grade / live / collab / ai_gateway / ai_chat / ai_grade / analytics / logs）。

## Directory Structure

```
edu/
├── 原型/                    # 设计原型 + 技术文档
│   ├── lumina-00-index.html    # 索引导航页（入口）
│   ├── lumina-prd.html         # 产品需求文档 v1.3
│   ├── lumina-tdd.html         # 技术设计文档 v1.0
│   ├── lumina-api.html         # API 接口文档 v1.0
│   ├── lumina-api-openapi.yaml # OpenAPI 3.1 规范
│   ├── lumina-database.html    # 数据库设计文档 v1.0
│   ├── lumina-operations.html  # 部署运维手册 v1.0
│   ├── lumina-testcases.html   # 测试用例文档 v1.0
│   ├── lumina-userguide.html   # 用户手册 v1.0
│   ├── lumina-launch-wbs.html  # 上线 WBS v1.1
│   │
│   ├── APP/phone/  (8 files)   # 手机 APP 原型
│   ├── APP/tablet/ (6 files)   # 平板 APP 原型
│   ├── Web/        (7 files)   # 浏览器端原型
│   ├── PC/         (7 files)   # 桌面端原型
│   └── AI/         (3 files)   # AI 模块原型
│
├── 服务/                   # 单体应用 + 前端
│   ├── lumina-app/             # ✅ 单体 FastAPI（11 模块 · 77 端点 · 30 表）
│   │   ├── app/                # 应用代码（main.py / models.py / security.py ...）
│   │   │   └── modules/        # 11 业务模块：user/course/assignment/grade/live/collab/ai_gateway/ai_chat/ai_grade/analytics/logs
│   │   ├── tests/              # 单元测试（125 passed）
│   │   ├── requirements.txt    # Python 依赖
│   │   └── Dockerfile          # API 容器镜像
│   ├── web-frontend/           # Web 前端（React 18 + TS + Vite）
│   └── mobile-app/             # 移动端前端（React Native / Expo）
│
├── 部署/                   # Docker 部署方案（环境搭建）
│   ├── docker-compose.yml      # 服务编排（MySQL/Redis/lumina-app/Nginx）
│   ├── .env.example            # 环境变量模板
│   ├── config/                 # Nginx/MySQL 配置
│   ├── scripts/                # 启停/备份/监控/契约核对脚本
│   ├── docs/                   # UAT 验收清单 / events-catalog / 上线检查清单
│   └── README.md               # 部署使用说明
│
└── scripts/                 # 工具脚本
    ├── yuque-sync.py           # 语雀同步工具
    └── README.md               # 脚本使用说明
```

## Common Commands

### Viewing Prototypes
All prototype files are standalone HTML. Open directly in browser:
```bash
# Open index page
open 原型/lumina-00-index.html

# Or use any browser
chrome 原型/lumina-prd.html
```

### Running the Monolith Application (单体应用)
单体应用为 FastAPI，位于 `服务/lumina-app/`，启动命令：
```bash
# 进入单体应用目录
cd 服务/lumina-app

# 启动 API 服务（默认端口 8080）
uvicorn app.main:app --port 8080
```

### Running Unit Tests (单元测试)
```bash
PYTHONIOENCODING=utf-8 服务/lumina-app/.venv/Scripts/python.exe -m pytest 服务/lumina-app/tests -q
```

### Yuque Sync (语雀同步)
```bash
# Install dependencies
pip install requests beautifulsoup4 markdownify

# Set token
export YUQUE_TOKEN="your_token"

# Run sync
python scripts/yuque-sync.py
```

### Test Accounts（测试账号 / Demo）

本地联调、冒烟与前端开发使用的演示账号（由 `部署/scripts/seed_demo.py` 种子生成，幂等可重复运行；默认密码 `Demo@2026`，可用 `--demo-password xxxx` 覆盖）：

| 角色 | 账号 | 默认密码 | 说明 |
|------|------|----------|------|
| 管理员 | `admin@lumina.edu` | `Demo@2026` | 系统管理员：模型池管理、绕过课程权限控制 |
| 教师 | `teacher@lumina.edu` | `Demo@2026` | 授课教师（工号 `T20260001`）：建课程/直播、点名、发答题、批阅 |
| 学生 | `student@lumina.edu` | `Demo@2026` | 已选课学生（学号 `20260001`）：加入直播、举手、作答 |
| 未选课学生 | `nouser@lumina.edu` | `Demo@2026` | **未选任何课程**，用于越权测试（直播加入 403、课程权限校验） |

> ⚠️ 仅演示/联调使用，生产环境必须更换。上层应用连本机 MySQL 时用 `root/root`（见环境变量说明）。

运行前端体验直播：
```bash
# 后端（需先起 MySQL）
cd 服务/lumina-app && uvicorn app.main:app --port 8080 --host 127.0.0.1
# 前端 dev（已配置 5173 → 127.0.0.1:8080 代理）
cd 服务/web-frontend && npm run dev   # 打开 http://localhost:5173
```

### 🎥 直播演示流（开播真实画面，可选）

未接媒体服务器时，开播返回 `mock://` 占位（无画面，仅课堂协作逻辑）。要「开播即有真实画面」，用本地 mediamtx 演示：

```bash
# ① 一键起流：MediaMTX + ffmpeg 推演示课堂画面（默认房间 key=roomdemo）
部署/stream/start_demo_stream.bat          # 停止：stop_demo_stream.bat
# ② 后端 .env 已配置（服务/lumina-app/.env，gitignored）：
#    LIVE_STREAM_BASE=http://127.0.0.1:8888/live
#    LIVE_STREAM_PROXY=true        # stream_url 走同源 /media 反代
# ③ 教师登录 → 冒烟测试课程 → 「直播演示间（固定流 roomdemo）」→ 开播
```
- 任意房间推流：`部署/stream/start_demo_stream.bat <room的 stream_key>`
- 详情见 `部署/stream/README.md`；生产接入见「运维手册」媒体反代说明

### 📱 移动端直播演示（Expo）

移动端（`服务/mobile-app/`，RN/Expo）直播页功能对齐 Web。本地连接后端：

```bash
# ① 后端（需先起 MySQL）；若手机真机访问，--host 0.0.0.0
cd 服务/lumina-app && uvicorn app.main:app --port 8080 --host 0.0.0.0
# ② 移动端 API 地址（电脑上回环仅模拟器可用）：
#    iOS 模拟器 → http://127.0.0.1:8080（默认）
#    Android 模拟器 → http://10.0.2.2:8080
#    真机 → http://<电脑局域网IP>:8080
#    修改：mobile-app/src/config.ts 的 API_BASE
cd 服务/mobile-app && npm install && npx expo start
```

- 开播真实画面：先起 `部署/stream/start_demo_stream.bat`（HLS 同源 `/media` 反代已配），再进「直播演示间」开播
- HLS 播放：`expo-video`（原生播放器）；仅房间 `status==='live'` 时拉流，`mock://` 为未接媒体服务器占位

### 🆕 平台支持矩阵（含鸿蒙）

| 端 | 现状 | 说明 |
|----|------|------|
| iOS / Android | ✅ 已实现 | `服务/mobile-app/`（React Native / Expo SDK 52） |
| Web | ✅ 已实现 | `服务/web-frontend/`（React 18 + Vite） |
| 桌面 | 🟡 原型 | `原型/PC/`（Electron 方案规划中，TDD §3.2） |
| 鸿蒙 HarmonyOS | ⏳ 演进评估 | **Expo 官方不支持鸿蒙**；WBS D-09 三路线评估：原生 ArkTS／ArkUI 独立客户端（DevEco，移动端 6 页 · 推荐）· RNOH bare 迁移 · uni-app；不阻塞 M4 |

> 详见 `原型/lumina-wbs-pending.html` v1.1 D-09 任务包。

## Design System

### Color Palette
- **宣纸色**: `#FAF6EC` (主背景)
- **墨色**: `#0F1020` (主文字)
- **钴蓝**: `#3D46C9` (品牌强调色)
- **荧光黄**: `#F5B800` (签名效果)
- **警示红**: `#E85D3A` (批注/警示)
- **成长绿**: `#2A7F4F` (成功/正向)
- **AI 紫**: `#7C3AED` (AI 模块强调)

### Typography
- **Fraunces** - Display 标题字体
- **Inter** - Body 正文字体
- **JetBrains Mono** - Mono 数字/代码字体
- **PingFang SC / Songti SC** - 中文 fallback

### Signature Effect (荧光笔签名)
```css
background: linear-gradient(
  180deg,
  transparent 62%,
  var(--highlighter) 62%,
  var(--highlighter) 88%,
  transparent 92%
);
```

## Documentation Architecture

项目包含 9 个核心文档，形成完整文档体系：

1. **PRD** (产品需求) - 用户画像、功能模块、验收标准
2. **TDD** (技术设计) - 架构、单体应用（11 模块）、数据库、API 规范
3. **API** (接口文档) - 77 个 RESTful 端点
4. **OpenAPI** (机器可读) - YAML 格式 API 规范
5. **Database** (数据库) - 30 表、ER 模型、分区策略
6. **Operations** (运维) - Docker Compose 部署、监控告警、Runbook
7. **Test Cases** (测试) - 125 用例、80% 覆盖率
8. **User Guide** (用户手册) - 3 角色指南、FAQ
9. **WBS v1.1** (上线计划) - 10 周轻量方案

所有文档使用统一的 Lumina 视觉风格，可直接在浏览器中打开查看。

单体应用 `服务/lumina-app/` 快照：77 端点 · 11 模块 · 30 表 · 单元测试 125 通过。

## Platform Coverage

| 平台 | 目录 | 文件数 | 说明 |
|------|------|--------|------|
| 📱 手机 | APP/phone/ | 8 | 学生/教师移动端 |
| 📲 平板 | APP/tablet/ | 6 | 大屏触控优化 |
| 🌐 Web | Web/ | 7 | 浏览器端 |
| 🖥️ 桌面 | PC/ | 7 | 桌面客户端 |
| 🤖 AI | AI/ | 3 | AI 功能模块 |

**总计**: 40 个 HTML 原型文件

## Git Workflow

- 主分支: `master`
- 远程仓库: https://github.com/yuan50697105/lumina-edu
- 提交规范: `docs: 描述变更内容`
- 所有变更及时推送，保持同步

## Key Conventions

1. **文件命名**: `lumina-{编号}-{功能}.html` (如 `lumina-03-student-mobile.html`)
2. **文档版本**: 每个文档独立版本号 (v1.0, v1.1 等)
3. **视觉一致**: 所有 HTML 文档使用相同的 CSS 变量和样式
4. **中文优先**: 所有文档内容使用简体中文
5. **HTML 格式**: 原型和文档均为纯 HTML，无外部依赖（字体除外）

## ⚠️ Mandatory Workflows (强制工作流)

**本项目包含 5 个强制工作流，必须根据任务类型选择对应流程：**

---

### 📋 工作流 1：需求工作流 (Requirement Workflow)

**适用场景**：创建新文档、创建新原型、需求定义

| 步骤 | 操作 | 检查点 |
|------|------|--------|
| 1. 需求分析 | 明确文档/原型的目标、范围、用户 | ✅ 需求清晰 |
| 2. 结构设计 | 设计章节结构、内容大纲、交互流程 | ✅ 结构合理 |
| 3. 创建文档 | 使用 Lumina 模板创建 HTML，填充内容 | ✅ 视觉一致 |
| 4. 更新索引 | 更新索引页 + README + 统计数据 | ✅ 索引同步 |
| 5. 验证提交 | 浏览器检查，提交推送 | ✅ 功能正常 |
| **6. 团队审核** | **审核团队评审，确认通过** | **✅ 审核通过** |

**产出物**：
- 📄 新文档（HTML 格式）
- 📱 新原型（HTML 格式）
- 📝 更新后的索引页和 README

**👥 团队审核流程**：
```
审核前准备：
- [ ] 文档/原型已完成自测
- [ ] 所有链接可正常访问
- [ ] 视觉风格与现有文档一致
- [ ] 已更新索引页和 README

审核内容：
- [ ] 需求覆盖完整性
- [ ] 内容准确性
- [ ] 结构逻辑性
- [ ] 视觉一致性
- [ ] 用户体验友好性

审核结果：
✅ 通过 → 提交推送
🔄 需修改 → 返回步骤 3 修改后重新审核
❌ 不通过 → 返回步骤 1 重新分析需求
```

**快速命令**：
```bash
# 审核通过后提交
git add -A && git commit -m "docs: 新增 xxx 文档 v1.0 (已审核)" && git push origin master
```

---

### 📐 工作流 2：规划工作流 (Planning Workflow)

**适用场景**：架构设计、技术方案、任务分解、WBS 规划

| 步骤 | 操作 | 产出物 |
|------|------|--------|
| 1. 需求收集 | 明确目标、范围、约束、依赖 | 📝 需求清单 |
| 2. 方案设计 | 技术方案、架构设计、数据结构 | 📐 设计文档 |
| 3. 任务分解 | WBS 分解、时间估算、资源规划 | 📊 WBS 文档 |
| 4. 评审确认 | 方案评审、风险评估、里程碑确认 | ✅ 评审通过 |
| 5. 文档输出 | 输出 PRD/TDD/WBS 等规划文档 | 📄 规划文档集 |
| **6. 团队审核** | **审核团队评审，确认通过** | **✅ 审核通过** |

**规划文档检查清单**：
- [ ] 目标明确、范围清晰
- [ ] 技术方案可行
- [ ] 任务分解完整
- [ ] 时间估算合理
- [ ] 风险已识别
- [ ] 里程碑已定义

**👥 团队审核流程**：
```
审核前准备：
- [ ] 规划文档已完成自检
- [ ] 技术方案已验证可行性
- [ ] WBS 任务分解完整
- [ ] 时间估算有依据

审核内容：
- [ ] 技术方案合理性
- [ ] 架构设计可扩展性
- [ ] 任务分解完整性
- [ ] 时间估算准确性
- [ ] 风险应对措施
- [ ] 资源分配合理性

审核结果：
✅ 通过 → 进入开发执行阶段
🔄 需调整 → 返回步骤 2-3 调整后重新审核
❌ 不通过 → 返回步骤 1 重新收集需求
```

---

### 🔨 工作流 3：开发执行工作流 (Development Workflow)

**适用场景**：代码实现、脚本开发、功能开发

| 步骤 | 操作 | 检查点 |
|------|------|--------|
| 1. 环境准备 | 确认依赖、配置、开发环境 | ✅ 环境就绪 |
| 2. 代码编写 | 实现功能、编写逻辑、处理异常 | ✅ 代码规范 |
| 3. 单元测试 | 编写测试、运行测试、覆盖率检查 | ✅ 测试通过 |
| 4. 集成测试 | 端到端测试、接口测试、性能测试 | ✅ 集成正常 |
| 5. 代码审查 | 自审代码、优化重构、文档注释 | ✅ 质量达标 |
| 6. 开发进度更新 | 更新 `开发进度.md`：任务状态、提交 ID、验证结果（如「待办 → 完成」） | ✅ 进度同步 |
| 7. 提交推送 | 增量提交、清晰注释、及时推送 | ✅ 版本可追溯 |
| **8. 团队审核** | **审核团队评审，确认通过** | **✅ 审核通过** |

**开发规范**：
- 📁 脚本放在 `scripts/` 目录
- 🐍 Python 脚本遵循 PEP 8
- 📝 函数/类必须有文档字符串
- 🧪 核心功能必须有单元测试
- 🔒 敏感信息使用环境变量
- 📈 **每个 WBS 任务完成后必须更新 `开发进度.md`**（与代码同次提交），不允许带着积压进度提交

**👥 团队审核流程**：
```
审核前准备：
- [ ] 代码已完成自测
- [ ] 单元测试覆盖率达标（≥80%）
- [ ] 集成测试通过
- [ ] 代码已自审优化
- [ ] 文档注释完整
- [ ] 开发进度.md 已更新（任务状态 + 提交 ID + 验证结果）

审核内容：
- [ ] 代码质量（规范性、可读性）
- [ ] 功能完整性
- [ ] 测试覆盖率
- [ ] 性能表现
- [ ] 安全性检查
- [ ] 文档完整性
- [ ] 进度记录准确性（开发进度.md 与提交一致）

审核结果：
✅ 通过 → 合并代码，进入验证阶段
🔄 需修改 → 返回步骤 2-5 修改后重新审核
❌ 不通过 → 重新评估方案，返回步骤 1
```

**增量提交示例**：
```bash
# 完成一个功能模块
git add scripts/xxx.py
git commit -m "feat: 实现 xxx 功能"
git push origin master

# 添加测试
git add tests/test_xxx.py
git commit -m "test: 添加 xxx 单元测试"
git push origin master

# 同步 WBS 进度（必须）
git add 开发进度.md
git commit -m "docs: WBS x.x 完成：xxx 功能，提交 ID 跟踪"
git push origin master

# 审核通过后合并
git commit -m "release: xxx 功能已通过团队审核"
git push origin master
```

---

### ✅ 工作流 4：收尾验证工作流 (Verification Workflow)

**适用场景**：文档完成、代码交付、上线前检查、阶段验收

| 步骤 | 操作 | 检查点 |
|------|------|--------|
| 1. 完整性检查 | 所有计划内容是否完成 | ✅ 内容完整 |
| 2. 一致性检查 | 视觉风格、术语、版本号一致 | ✅ 风格统一 |
| 3. 功能测试 | 所有功能可用、无 Bug | ✅ 功能正常 |
| 4. 链接检查 | 所有链接可访问、无死链 | ✅ 链接有效 |
| 5. 索引同步 | 索引页、README、统计数字更新 | ✅ 索引最新 |
| 6. 最终提交 | 完整提交信息，标注版本号 | ✅ 版本清晰 |
| 7. 交付确认 | GitHub 检查、浏览器验证 | ✅ 交付成功 |
| **8. 团队审核** | **审核团队最终验收** | **✅ 审核通过** |

**验证检查清单**：
- [ ] 所有计划内容已完成
- [ ] 视觉风格完全一致
- [ ] 所有功能可正常使用
- [ ] 所有链接可正常访问
- [ ] 索引页已更新
- [ ] README 已更新
- [ ] 版本号已更新
- [ ] 统计数据准确
- [ ] 测试全部通过
- [ ] 提交信息完整清晰
- [ ] 远程仓库已同步

**👥 团队审核流程**：
```
审核前准备：
- [ ] 所有验证检查项已通过
- [ ] 文档/代码已提交到远程仓库
- [ ] 版本号已正确标注
- [ ] 变更日志已编写

审核内容：
- [ ] 交付物完整性
- [ ] 质量标准达成
- [ ] 文档规范性
- [ ] 用户体验
- [ ] 上线准备度
- [ ] 回滚方案（如适用）

审核结果：
✅ 通过 → 正式发布，项目收尾
🔄 需完善 → 返回步骤 1-6 完善后重新审核
❌ 不通过 → 重新评估，可能需要返工
```

**最终提交格式**：
```bash
git commit -m "release: 完成 xxx v1.0 (已通过团队审核)

变更内容：
- 新增 xxx 功能
- 完成 xxx 章节
- 修复 xxx 问题

验证结果：
- ✅ 完整性检查通过
- ✅ 功能测试通过
- ✅ 链接检查通过
- ✅ 索引同步完成
- ✅ 团队审核通过

版本号：v1.0
文档编号：DOC-LUMINA-2026-xxx"
```

---

### 🔄 工作流 5：变更工作流 (Change Workflow)

**适用场景**：修改/更新已有文档、原型、代码、配置（非新建）。新建产物走需求/规划工作流；本工作流专管「改已有的」。

| 步骤 | 操作 | 检查点 |
|------|------|--------|
| 1. 变更分析 | 明确变更对象、变更目标、**影响范围**（关联文件、索引、版本号、调用方） | ✅ 变更清晰 |
| 2. 影响评估 | 确认是否需要同步：版本号升级、索引页、README、开发进度、其它依赖模块 | ✅ 影响全覆盖 |
| 3. 方案实施 | 采用与既有产物一致的风格/约定进行修改；涉及数据结构/接口变动的先说明兼容性 | ✅ 风格一致 |
| 4. 回归验证 | 原有功能可用 + 新变更生效；相关测试、链接、埋点不受影响 | ✅ 无回归 |
| 5. 联动同步 | 更新受影响的索引、README、版本历史、`开发进度.md`（如涉及） | ✅ 联动完成 |
| 6. 提交推送 | 提交信息记录「变更前 → 变更后」，清晰可追溯 | ✅ 版本可追溯 |
| **7. 团队审核** | **审核团队评审变更必要性与质量，确认通过** | **✅ 审核通过** |

**变更提交格式**：
```bash
git commit -m "change: 修改 xxx（v1.x → v1.x+1）

变更前：...
变更后：...
影响范围：xxx / 索引 / README / 开发进度.md
验证结果：✅ 回归通过
审核：Claude 团队审核通过"
```

**👥 团队审核流程**：
```
审核前准备：
- [ ] 变更目标明确
- [ ] 影响范围已完整评估（文件 / 索引 / 版本号 / 进度）
- [ ] 变更已实施且风格一致
- [ ] 回归验证通过（原有功能未破坏）
- [ ] 索引 / README / 进度已联动更新

审核内容：
- [ ] 变更必要性（是否有更小改动方案）
- [ ] 变更准确性
- [ ] 影响评估完整性
- [ ] 回归验证充分性
- [ ] 文档同步一致性

审核结果：
✅ 通过 → 提交推送
🔄 需调整 → 返回步骤 3-4 调整后重新审核
❌ 不通过 → 返回步骤 1 重新分析变更
```

---

### 🚨 全局强制规则

1. **每次变更必须推送** - 不允许本地积压
2. **新增文档必须更新索引** - 索引页 + README
3. **保持视觉风格一致** - 使用统一 CSS 变量
4. **中文优先** - 所有文档使用简体中文
5. **版本号管理** - 每个文档独立版本号
6. **增量提交** - 大任务分多次提交，便于追溯
7. **开发进度同步** - 每个 WBS 任务完成后更新 `开发进度.md`（任务状态 + 提交 ID + 验证结果）

---

### 📊 工作流选择指南

| 任务类型 | 选择工作流 | 示例 |
|---------|-----------|------|
| **创建新文档** | 📋 需求工作流 | 新建 API 文档、用户手册 |
| **创建新原型** | 📋 需求工作流 | 新建手机原型、Web 原型 |
| **架构设计** | 📐 规划工作流 | 技术架构、数据库设计 |
| **任务规划** | 📐 规划工作流 | WBS 分解、时间估算 |
| **代码开发** | 🔨 开发执行工作流 | 新功能代码、脚本实现 |
| **功能测试** | 🔨 开发执行工作流 | 单元测试、集成测试 |
| **修改已有文档** | 🔄 变更工作流 | 更新 PRD/API 文档、修改原型页面 |
| **修改已有代码** | 🔄 变更工作流 | 修复 Bug、接口调整、配置变更 |
| **文档交付** | ✅ 收尾验证工作流 | 文档完成、版本发布 |
| **阶段验收** | ✅ 收尾验证工作流 | 上线前检查、项目复盘 |
