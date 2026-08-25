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
- ✅ **完整技术文档**：PRD v1.3 + TDD v1.0 + 设计索引

## 📂 项目结构

```
edu/
├── README.md                          # 本文件
├── .gitignore                         # Git 忽略规则
│
├── 原型/                              # 设计原型 + 文档
│   ├── lumina-00-index.html           # 📋 索引导航（入口）
│   ├── lumina-prd.html                # 📋 产品需求文档 PRD v1.3
│   ├── lumina-tdd.html                # 📋 技术设计文档 TDD v1.0
│   ├── lumina-api.html                # 📋 API 接口文档 v1.0
│   ├── lumina-api-openapi.yaml        # 📋 OpenAPI 3.1 规范
│   │
│   ├── APP/phone/      (8 文件)       # 📱 手机 APP 原型
│   ├── APP/tablet/     (6 文件)       # 📲 平板 APP 原型
│   ├── Web/            (7 文件)       # 🌐 浏览器端原型
│   ├── PC/             (7 文件)       # 🖥️ 桌面端原型
│   └── AI/             (3 文件)       # 🤖 AI 模块原型
│
└── scripts/                           # 工具脚本
    ├── yuque-sync.py                  # 🔌 语雀同步工具
    ├── yuque-config.example.json      # 配置模板
    └── README.md                      # 脚本使用说明
```

## 📊 项目统计

| 维度 | 数据 |
|------|------|
| **原型文件** | 33 个 HTML |
| **平台目录** | 5 个（phone/tablet/Web/PC/AI）|
| **界面页面** | 160+ 个 |
| **设计表面** | 6 个（学生/教师 × 移动/Web/桌面）|
| **功能模块** | 20+ 个 |
| **文档** | PRD v1.3 + TDD v1.0 + API v1.0 + 索引 |
| **API 接口** | 42 个端点（8 模块 · JWT · WebSocket）|

## 📖 文档体系

| 文档 | 说明 | 文件 |
|------|------|------|
| 📋 **设计索引** | 原型导航入口，按平台分类 | `lumina-00-index.html` |
| 📋 **PRD v1.3** | 产品需求文档，18 章 | `lumina-prd.html` |
| 📋 **TDD v1.0** | 技术设计文档，18 章 | `lumina-tdd.html` |
| 📋 **API v1.0** | API 接口文档，11 章 · 42 端点 | `lumina-api.html` |
| 📋 **OpenAPI 3.1** | 机器可读 API 规范（YAML） | `lumina-api-openapi.yaml` |

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

### 查看文档

| 文档 | 打开方式 |
|------|----------|
| 设计索引 | `原型/lumina-00-index.html` |
| PRD 文档 | `原型/lumina-prd.html` |
| TDD 文档 | `原型/lumina-tdd.html` |
| API 文档 | `原型/lumina-api.html` |
| OpenAPI 规范 | `原型/lumina-api-openapi.yaml` |

## 📋 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| **v1.0** | 2026-08-25 | 初始发布，24 个原型文件 |
| **v1.1** | 2026-08-25 | AI 模块新增，国产模型集成 |
| **v1.2** | 2026-08-25 | 移动端双模式适配（手机+平板） |
| **v1.3** | 2026-08-25 | 按平台目录重组，5 目录 33 文件 |
| **TDD v1.0** | 2026-08-25 | 技术设计文档发布 |
| **API v1.0** | 2026-08-25 | API 接口文档发布，42 端点 |
| **OpenAPI 3.1** | 2026-08-25 | OpenAPI 规范文件，可生成 SDK/Mock |

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
