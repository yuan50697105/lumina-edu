# Lumina 墨光 · 语雀同步工具

将 Lumina 设计文档同步到语雀知识库。

## 📦 安装依赖

```bash
pip install requests beautifulsoup4 markdownify
```

## 🔧 配置

### 方式一：环境变量（推荐）

```bash
# 设置语雀 Token
export YUQUE_TOKEN="your_token_here"

# 运行同步
python scripts/yuque-sync.py
```

### 方式二：修改脚本配置

编辑 `scripts/yuque-sync.py`，修改 `YUQUE_CONFIG`：

```python
YUQUE_CONFIG = {
    "token": "your_token_here",
    "repo_namespace": "yourname/lumina",  # 你的知识库命名空间
    # ...
}
```

## 🚀 获取语雀 Token

1. 访问 https://www.yuque.com/settings/tokens
2. 点击「新建」
3. 填写名称（如 `Lumina Sync`）
4. 勾选权限：`读取` + `写入`
5. 创建并复制 Token

## 📚 配置知识库

### 获取知识库命名空间

1. 打开语雀知识库
2. 查看 URL：`https://www.yuque.com/{namespace}`
3. 复制 `{namespace}` 部分（如 `myteam/design`）

### 创建新知识库（可选）

如果没有现成的知识库，可以：
1. 访问 https://www.yuque.com/dashboard
2. 点击「新建知识库」
3. 填写名称（如 `Lumina 设计文档`）
4. 复制命名空间

## 📄 同步内容

| 文档 | 语雀 Slug | 说明 |
|------|-----------|------|
| PRD | `lumina-prd` | 产品需求文档 v1.3 |
| 设计索引 | `lumina-index` | 原型目录和导航 |
| 设计规范 | `lumina-specs` | 配色/字体/签名效果 |

## 🏃 运行

```bash
cd /d/projects/edu
python scripts/yuque-sync.py
```

输出示例：

```
🔌 连接语雀...
✅ 已登录：张三 (@zhangsan)
📚 知识库：Lumina 设计文档 (myteam/lumina)

============================================================
🚀 开始同步...
============================================================

📄 处理 prd...
   源文件：/d/projects/edu/原型/lumina-prd.html
   ✅ 更新成功
   🔗 https://www.yuque.com/myteam/lumina/lumina-prd

📄 处理 index...
   ✅ 创建成功
   🔗 https://www.yuque.com/myteam/lumina/lumina-index

📄 处理 specs...
   ✅ 创建成功
   🔗 https://www.yuque.com/myteam/lumina/lumina-specs

============================================================
📊 同步结果
============================================================
  ✅ prd: 更新
  ✅ index: 新建
  ✅ specs: 新建

🎉 完成！3/3 个文档同步成功
```

## ⚙️ 自定义配置

### 修改同步的文档

编辑 `scripts/yuque-sync.py` 中的 `YUQUE_CONFIG["docs"]`：

```python
"docs": {
    "my-doc": {
        "local": "原型/my-file.html",  # 本地文件路径
        "slug": "my-doc-slug",          # 语雀文档 slug
        "title": "我的文档标题",         # 文档标题
    },
}
```

### 自定义转换规则

修改 `html_to_yuque_markdown()` 函数，可以：
- 保留/移除特定 HTML 标签
- 调整 Markdown 格式
- 添加自定义元信息

## 🔒 安全提示

- **不要**将 Token 提交到 git
- 建议使用环境变量管理 Token
- `scripts/yuque-config.local.json` 已在 `.gitignore` 中排除

## 🐛 故障排除

### Token 无效

```
❌ 连接失败：401 Unauthorized
```

- 检查 Token 是否正确
- 确认 Token 未过期
- 验证 Token 有读写权限

### 知识库访问失败

```
❌ 知识库访问失败：404 Not Found
```

- 检查 `repo_namespace` 格式是否正确
- 确认你有该知识库的写入权限
- 尝试访问 `https://www.yuque.com/{namespace}` 确认存在

### 文档创建失败

```
❌ 失败：403 Forbidden
```

- 确认 Token 有写入权限
- 检查知识库是否允许 API 创建文档

## 📝 更新日志

- **2026-08-25** - 初始版本，支持 PRD/索引/规范同步
