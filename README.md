# Lumina 墨光 - 教育应用 UI 设计系统

面向高校师生的跨端教学协作平台 UI 设计原型系统。

## 📱 项目概述

Lumina（墨光）是一个完整的教育应用 UI 设计系统，覆盖学生、教师、管理员三类用户，支持移动端、Web 端、桌面端三种终端形态。

### 核心特性

- ✅ **六端覆盖**：学生/教师/管理员 × 移动/Web/桌面
- ✅ **双模式适配**：所有移动端支持手机+平板自适应（📱↔📲）
- ✅ **AI 原生**：集成国产大模型（通义千问、智谱 GLM、讯飞星火等）
- ✅ **双层模型选择**：管理端配置模型池 + 用户端自主选择
- ✅ **统一设计语言**：荧光笔签名效果、宣纸质感配色、跨端一致体验

## 📂 项目结构

```
edu/
├── 原型/                          # UI 设计原型文件
│   ├── lumina-00-index.html      # 索引入口（导航所有设计稿）
│   ├── lumina-prd.html           # 产品需求文档 PRD v1.2
│   │
│   ├── 设计基础                    # 01-02
│   │   ├── lumina-01-design-system.html
│   │   └── lumina-02-shared.html
│   │
│   ├── 学生端                      # 03-05
│   │   ├── lumina-03-student-mobile.html      📱↔📲
│   │   ├── lumina-04-student-web.html
│   │   └── lumina-05-student-desktop.html
│   │
│   ├── 教师端                      # 06-08
│   │   ├── lumina-06-teacher-mobile.html      📱↔📲
│   │   ├── lumina-07-teacher-web.html
│   │   └── lumina-08-teacher-desktop.html
│   │
│   ├── 学生协作                    # 09-11
│   │   ├── lumina-09-student-collaboration-mobile.html  📱↔📲
│   │   ├── lumina-10-student-collaboration-web.html
│   │   └── lumina-11-student-collaboration-desktop.html
│   │
│   ├── 教师深度功能                 # 12-14
│   │   ├── lumina-12-teacher-deep-mobile.html  📱↔📲
│   │   ├── lumina-13-teacher-deep-web.html
│   │   └── lumina-14-teacher-deep-desktop.html
│   │
│   ├── 管理端                      # 15-17
│   │   ├── lumina-15-admin-web.html
│   │   ├── lumina-16-admin-desktop.html
│   │   └── lumina-17-admin-mobile.html         📱↔📲
│   │
│   └── AI 模块（国产模型）          # 18-20
│       ├── lumina-18-ai-student.html           📱↔📲
│       ├── lumina-19-ai-teacher.html
│       └── lumina-20-ai-admin.html             模型池管理
│
├── .gitignore
└── README.md
```

## 🎨 设计系统

### 配色方案

- **宣纸色** `--ricepaper: #FAF6EC` - 主背景
- **墨色** `--inkwell: #0F1020` - 主文字
- **钴蓝** `--cobalt: #3D46C9` - 品牌强调色
- **荧光黄** `--highlighter: #F5B800` - 签名效果
- **警示红** `--correction: #E85D3A` - 批注/警示
- **成长绿** `--growth: #2A7F4F` - 成功/正向

### 字体系统

- **Fraunces** - Display 标题字体（SIL OFL 1.1）
- **Inter** - Body 正文字体（SIL OFL 1.1）
- **JetBrains Mono** - Mono 数字/代码字体（SIL OFL 1.1）
- **PingFang SC / Songti SC** - 中文 fallback（系统字体）

### 图标库

- **Feather Icons** - 260+ 线性图标（MIT License）
- 所有图标采用 inline SVG 形式嵌入

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

### 双层模型选择

1. **管理端配置**：管理员配置可用模型池（启用/禁用/配额/预算）
2. **用户端选择**：师生根据场景自主选择模型
3. **智能路由**：系统根据任务类型自动推荐最优模型

## 📱 双模式适配

所有移动端原型支持手机+平板双模式自适应：

| 维度 | 📱 手机模式 | 📲 平板模式 |
|------|-----------|-----------|
| 屏幕尺寸 | ≤ 480px | 768-1024px |
| 导航结构 | 底部 5 Tab | 侧边栏导航 |
| 布局方式 | 单列卡片 | 多列网格（2-3 栏） |
| 信息密度 | 紧凑优先 | 丰富展示 |

### 响应式断点

- **Mobile**: < 480px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 📊 项目统计

- **总文件数**：28 个 HTML 文件
- **总大小**：1.5 MB
- **设计表面**：6 个（学生/教师/管理员 × 移动/Web/桌面）
- **功能模块**：20 个
- **界面页面**：160+ 个

## 🚀 使用方式

### 查看设计稿

1. 在浏览器中打开 `原型/lumina-00-index.html`
2. 通过索引页面导航到各个设计稿
3. 每个 HTML 文件可独立打开查看

### 查看 PRD 文档

打开 `原型/lumina-prd.html` 查看完整产品需求文档（v1.2）

## 📋 版本历史

- **v1.0** (2026-08-25) - 初始发布，24 个原型文件
- **v1.1** (2026-08-25) - AI 模块新增，国产模型集成
- **v1.2** (2026-08-25) - 移动端双模式适配（手机+平板）

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
