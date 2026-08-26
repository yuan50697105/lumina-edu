# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lumina (墨光) 教育应用 UI 设计系统 - 面向高校师生的跨端教学协作平台。本项目为纯设计原型 + 技术文档项目，不包含应用代码。

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

### Yuque Sync (语雀同步)
```bash
# Install dependencies
pip install requests beautifulsoup4 markdownify

# Set token
export YUQUE_TOKEN="your_token"

# Run sync
python scripts/yuque-sync.py
```

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
2. **TDD** (技术设计) - 架构、微服务、数据库、API 规范
3. **API** (接口文档) - 42 个 RESTful 端点
4. **OpenAPI** (机器可读) - YAML 格式 API 规范
5. **Database** (数据库) - 24 表、ER 模型、分区策略
6. **Operations** (运维) - K8s 部署、监控告警、Runbook
7. **Test Cases** (测试) - 156 用例、80% 覆盖率
8. **User Guide** (用户手册) - 3 角色指南、FAQ
9. **WBS** (上线计划) - 10 周轻量方案

所有文档使用统一的 Lumina 视觉风格，可直接在浏览器中打开查看。

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

**本项目包含 4 个强制工作流，必须根据任务类型选择对应流程：**

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

**产出物**：
- 📄 新文档（HTML 格式）
- 📱 新原型（HTML 格式）
- 📝 更新后的索引页和 README

**快速命令**：
```bash
git add -A && git commit -m "docs: 新增 xxx 文档 v1.0" && git push origin master
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

**规划文档检查清单**：
- [ ] 目标明确、范围清晰
- [ ] 技术方案可行
- [ ] 任务分解完整
- [ ] 时间估算合理
- [ ] 风险已识别
- [ ] 里程碑已定义

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
| 6. 提交推送 | 增量提交、清晰注释、及时推送 | ✅ 版本可追溯 |

**开发规范**：
- 📁 脚本放在 `scripts/` 目录
- 🐍 Python 脚本遵循 PEP 8
- 📝 函数/类必须有文档字符串
- 🧪 核心功能必须有单元测试
- 🔒 敏感信息使用环境变量

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

**最终提交格式**：
```bash
git commit -m "release: 完成 xxx v1.0

变更内容：
- 新增 xxx 功能
- 完成 xxx 章节
- 修复 xxx 问题

验证结果：
- ✅ 完整性检查通过
- ✅ 功能测试通过
- ✅ 链接检查通过
- ✅ 索引同步完成

版本号：v1.0
文档编号：DOC-LUMINA-2026-xxx"
```

---

### 🚨 全局强制规则

1. **每次变更必须推送** - 不允许本地积压
2. **新增文档必须更新索引** - 索引页 + README
3. **保持视觉风格一致** - 使用统一 CSS 变量
4. **中文优先** - 所有文档使用简体中文
5. **版本号管理** - 每个文档独立版本号
6. **增量提交** - 大任务分多次提交，便于追溯

---

### 📊 工作流选择指南

| 任务类型 | 选择工作流 | 示例 |
|---------|-----------|------|
| **创建新文档** | 📋 需求工作流 | 新建 API 文档、用户手册 |
| **创建新原型** | 📋 需求工作流 | 新建手机原型、Web 原型 |
| **架构设计** | 📐 规划工作流 | 技术架构、数据库设计 |
| **任务规划** | 📐 规划工作流 | WBS 分解、时间估算 |
| **代码开发** | 🔨 开发执行工作流 | Python 脚本、功能实现 |
| **功能测试** | 🔨 开发执行工作流 | 单元测试、集成测试 |
| **文档交付** | ✅ 收尾验证工作流 | 文档完成、版本发布 |
| **阶段验收** | ✅ 收尾验证工作流 | 上线前检查、项目复盘 |
