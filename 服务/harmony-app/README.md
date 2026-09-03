# 墨光 · 鸿蒙原生客户端

> Lumina 墨光教育平台 · HarmonyOS NEXT 原生实现（ArkTS / ArkUI）

## 📱 平台定位

鸿蒙原生客户端，面向搭载 HarmonyOS NEXT 的手机/平板设备，为校园信创场景提供原生级体验。

**与 mobile-app（iOS/Android）的关系**：
- **mobile-app** = React Native / Expo SDK 52 → 覆盖 iOS 与 Android
- **harmony-app** = ArkTS / ArkUI 原生 → 覆盖 HarmonyOS NEXT（华为设备）
- **两端共用同一套后端 API 契约**（174 paths / 215 ops · 20 模块），差异仅在 UI 框架与平台特性

**为什么不用 RN/Expo 直接跑鸿蒙**：
> Expo 官方不支持鸿蒙。虽然存在 RNOH（React Native Open Harmony）桥接方案，但依赖替换成本高、部分原生模块缺失。考虑到鸿蒙在校园信创场景的战略价值，直接采用 **原生 ArkTS/ArkUI** 方案，获得最佳性能与系统能力（分布式通知 / 平行视界 / 多窗口 / 小艺语音）。

## 🏗️ 项目结构

```
harmony-app/
├── AppScope/                      # 应用级配置
│   ├── app.json5                  # bundleName / 版本 / 图标
│   └── resources/                 # 应用级资源
├── entry/                         # 入口模块（HAP）
│   └── src/main/
│       ├── ets/                   # ArkTS 源码
│       │   ├── entry/
│       │   │   └── EntryAbility.ets      # UIAbility 入口
│       │   ├── pages/
│       │   │   ├── Index.ets             # 登录页
│       │   │   ├── Home.ets              # 主页（5 Tab）
│       │   │   ├── LiveRoom.ets          # 直播观看
│       │   │   ├── Learning.ets          # 学习广场（D-06）
│       │   │   ├── Videos.ets            # 视频库（D-08）
│       │   │   └── Profile.ets           # 个人中心
│       │   ├── common/
│       │   │   └── constants.ets         # 设计系统 + 类型定义
│       │   └── model/
│       │       └── ApiClient.ets         # API 客户端
│       ├── resources/                    # 模块级资源
│       └── module.json5                  # 模块配置 + 权限
├── build-profile.json5                   # 构建配置
├── hvigorfile.ts                         # 构建脚本
├── oh-package.json5                      # 依赖管理
└── README.md
```

## 🎨 设计系统

复用 Lumina 既有视觉规范（`CLAUDE.md` §Design System）：

| Token | 色值 | 用途 |
|-------|------|------|
| 宣纸色 | `#FAF6EC` | 主背景 |
| 墨色 | `#0F1020` | 主文字 |
| 钴蓝 | `#3D46C9` | 品牌强调 |
| 荧光黄 | `#F5B800` | 签名效果 |
| 警示红 | `#E85D3A` | 批注/警示 |
| 成长绿 | `#2A7F4F` | 成功/正向 |
| AI 紫 | `#7C3AED` | AI 模块 |

## 🔌 API 契约

对齐 `服务/lumina-app/` 单体应用（174 paths / 215 ops）：

| 端点 | 用途 | 页面 |
|------|------|------|
| `POST /api/v1/auth/login` | OAuth2 密码登录 | Index |
| `GET /api/v1/courses` | 我的课程列表 | Home · CoursePane |
| `GET /api/v1/courses/{id}/live-rooms` | 直播房间列表 | Home · LivePane |
| `GET /api/v1/learning/paths` | 学习路径 | Learning |
| `GET /api/v1/learning/xp` | 用户 XP | Learning / Home |
| `POST /api/v1/checkin` | 每日打卡 | Learning |
| `GET /api/v1/learning/badges` | 徽章墙 | Learning |
| `GET /api/v1/videos` | 视频列表 | Videos |
| `GET /api/v1/users/me` | 当前用户 | Profile |

**API_BASE**：`entry/src/main/ets/common/constants.ets` 中配置，默认 `http://127.0.0.1:8080`，生产环境替换为正式域名。

## 🛠️ 开发环境

### 必需

| 工具 | 版本 | 用途 |
|------|------|------|
| DevEco Studio | NEXT（4.x+） | 鸿蒙官方 IDE |
| HarmonyOS SDK | API 11+ | 编译与运行 |
| Node.js | 18+ | ohpm 包管理 |
| ohpm | 最新 | 鸿蒙包管理器（DevEco 自带） |

### 安装步骤

1. **安装 DevEco Studio**
   - 从 [华为开发者联盟](https://developer.huawei.com/consumer/cn/deveco-studio/) 下载
   - 安装时勾选 HarmonyOS SDK（API 11 或以上）

2. **克隆项目**
   ```bash
   git clone https://github.com/yuan50697105/lumina-edu.git
   cd edu/服务/harmony-app
   ```

3. **DevEco 打开项目**
   - File → Open → 选择 `服务/harmony-app/` 目录
   - 等待 Sync 完成（自动下载 ohpm 依赖）

4. **启动后端**（另一个终端）
   ```bash
   cd 服务/lumina-app
   uvicorn app.main:app --port 8080 --host 127.0.0.1
   ```

5. **运行 App**
   - 真机：USB 连接华为设备，开启开发者模式 → Run
   - 模拟器：DevEco → Tools → Device Manager → 创建 Phone 模拟器 → Run

## 📋 页面功能

### Index（登录页）
- 邮箱/密码登录（OAuth2 password flow）
- 测试账号提示（teacher/student/admin）
- 登录成功 → 跳 Home

### Home（主页 · 5 Tab）
- **首页**：欢迎卡 + XP 概览 + 快捷入口
- **课程**：课程列表（title/code/teacher）
- **直播**：直播房间列表 + 状态标签
- **学习**：入口 → Learning / Videos
- **我的**：入口 → Profile

### LiveRoom（直播观看）
- HLS 播放占位（实际接入 AVPlayer）
- 举手 / 答题 / 聊天
- 在线人数显示

### Learning（学习广场 · D-06）
- XP 卡 + 等级 + 连续打卡
- 每日打卡按钮（+10XP）
- 学习路径列表（category/difficulty/node_count）
- 徽章墙（4 列网格）

### Videos（视频库 · D-08）
- 视频搜索
- 视频列表（封面/标题/时长/观看数）

### Profile（个人中心）
- 用户信息卡（头像/姓名/邮箱/角色）
- 功能列表（课程/作业/成绩/成就/通知/历史/设置/关于）
- 退出登录

## 🔧 鸿蒙特性待接入

本版本为**基础功能对齐**，以下鸿蒙特性待 Phase 2 接入：

| 特性 | 说明 | 优先级 |
|------|------|------|
| **分布式通知** | 跨设备消息流转 | P1 |
| **平行视界** | 平板双栏（课程目录 + 详情） | P1 |
| **多窗口** | PC/平板多任务并行 | P2 |
| **Floating Window** | 视频后台小窗播放 | P2 |
| **元服务卡片** | 桌面 2×2 今日课表 | P2 |
| **小艺语音** | 语音播报作业截止/课程提醒 | P3 |
| **AVPlayer** | 真实 HLS 视频播放 | P1 |
| **车机适配** | 音频课程 + D 档安全限制 | P3 |

## 🧪 测试

| 测试类型 | 工具 | 范围 |
|---------|------|------|
| 组件单元测试 | @ohos/hypium | constants / ApiClient 纯逻辑 |
| UI 测试 | DevEco Previewer | 页面布局与交互 |
| 真机冒烟 | 华为设备 | 登录 → 课程 → 直播 → 学习广场 |

## 📦 构建发布

```bash
# 调试包（签名默认 debug）
hvigorw assembleHap --mode module -p module=entry@default -p product=default

# 发布包（需配置 release 签名）
hvigorw assembleHap --mode project -p product=release
```

生成产物位于 `entry/build/default/outputs/default/entry-default-signed.hap`。

## 🔗 相关资源

- [HarmonyOS 开发者文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/arkts-basic-syntax-overview-V5)
- [ArkUI 声明式语法](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/arkts-declarative-ui-overview-V5)
- [DevEco Studio 下载](https://developer.huawei.com/consumer/cn/deveco-studio/)
- Lumina 后端：`服务/lumina-app/`（FastAPI · 174 paths / 215 ops · 20 模块）
- 移动端（iOS/Android）：`服务/mobile-app/`（Expo RN SDK 52）

## 📄 License

Apache-2.0 · Lumina 教育团队
