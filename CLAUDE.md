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
