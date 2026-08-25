#!/usr/bin/env python3
"""
Lumina 墨光 · 语雀同步工具
将 PRD / 索引 / 设计规范同步到语雀知识库

使用方法：
1. 获取语雀 Token：https://www.yuque.com/settings/tokens
2. 配置下方 YUQUE_CONFIG
3. 运行：python scripts/yuque-sync.py

依赖安装：pip install requests beautifulsoup4 markdownify
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# ============================================================
# 配置区 - 请修改以下配置
# ============================================================
YUQUE_CONFIG = {
    "token": os.environ.get("YUQUE_TOKEN", ""),  # 语雀 Token（建议用环境变量）
    "base_url": "https://www.yuque.com/api/v2",
    "repo_namespace": "",  # 知识库命名空间，如 "yourname/lumina"
    # 文档映射：本地文件 → 语雀文档 slug
    "docs": {
        "prd": {
            "local": "原型/lumina-prd.html",
            "slug": "lumina-prd",
            "title": "Lumina 墨光 · 产品需求文档 PRD",
        },
        "index": {
            "local": "原型/lumina-00-index.html",
            "slug": "lumina-index",
            "title": "Lumina 墨光 · 设计索引",
        },
        "specs": {
            "local": "原型/lumina-00-index.html",  # 从索引提取设计规范部分
            "slug": "lumina-specs",
            "title": "Lumina 墨光 · 设计规范",
        },
    },
}


# ============================================================
# 工具函数
# ============================================================

def strip_html_styles(html_content):
    """移除 HTML 中的 <style> 标签和内联样式"""
    soup = BeautifulSoup(html_content, "html.parser")
    for style in soup.find_all("style"):
        style.decompose()
    for tag in soup.find_all(style=True):
        del tag["style"]
    return str(soup)


def html_to_yuque_markdown(html_content, doc_type="generic"):
    """将 HTML 转换为语雀兼容的 Markdown"""
    soup = BeautifulSoup(html_content, "html.parser")

    # 移除 script 和 style
    for tag in soup.find_all(["script", "style", "link"]):
        tag.decompose()

    # 提取正文内容
    body = soup.find("body")
    if body:
        content = str(body)
    else:
        content = str(soup)

    # 转换为 Markdown
    markdown = md(
        content,
        heading_style="atx",
        bullets="-",
        strip=["img"],  # 图片暂时跳过
        convert=["p", "h1", "h2", "h3", "h4", "ul", "ol", "li", "table", "tr", "td", "th", "a", "strong", "em", "code", "pre", "blockquote"],
    )

    # 清理多余空行
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # 添加元信息头
    header = f"""<!-- 本文档由 Lumina 同步工具自动生成 -->
<!-- 源文件：{doc_type} -->
<!-- 同步时间：$(date) -->

"""
    return header + markdown.strip()


def extract_specs_section(html_content):
    """从索引页提取设计规范部分"""
    soup = BeautifulSoup(html_content, "html.parser")

    # 查找设计规范 section
    specs_section = None
    for section in soup.find_all("section"):
        header = section.find("h2")
        if header and ("设计规范" in header.text or "Specs" in header.text):
            specs_section = section
            break

    if specs_section:
        return str(specs_section)

    # 备选：查找调色板/字体相关内容
    result = []
    for card in soup.find_all(["div", "section"]):
        text = card.get_text()
        if any(kw in text for kw in ["调色板", "Palette", "Typography", "字体", "Signature"]):
            result.append(str(card))

    return "\n".join(result[:3]) if result else ""


class YuqueClient:
    """语雀 API 客户端"""

    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "X-Auth-Token": token,
            "Content-Type": "application/json",
            "User-Agent": "Lumina-Sync/1.0",
        }

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_user(self):
        """获取当前用户信息"""
        return self._request("GET", "/user")

    def get_repo(self, namespace):
        """获取知识库信息"""
        return self._request("GET", f"/repos/{namespace}")

    def list_docs(self, namespace):
        """列出知识库中的文档"""
        return self._request("GET", f"/repos/{namespace}/docs")

    def get_doc(self, namespace, slug):
        """获取文档详情"""
        try:
            return self._request("GET", f"/repos/{namespace}/docs/{slug}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_doc(self, namespace, title, slug, body, format="markdown"):
        """创建文档"""
        data = {
            "title": title,
            "slug": slug,
            "body": body,
            "format": format,
        }
        return self._request("POST", f"/repos/{namespace}/docs", data)

    def update_doc(self, namespace, doc_id, title, body, format="markdown"):
        """更新文档"""
        data = {
            "title": title,
            "body": body,
            "format": format,
        }
        return self._request("PUT", f"/repos/{namespace}/docs/{doc_id}", data)

    def sync_doc(self, namespace, slug, title, body, format="markdown"):
        """同步文档（存在则更新，不存在则创建）"""
        existing = self.get_doc(namespace, slug)
        if existing:
            doc_id = existing["data"]["id"]
            result = self.update_doc(namespace, doc_id, title, body, format)
            return {"action": "updated", "doc": result["data"]}
        else:
            result = self.create_doc(namespace, title, slug, body, format)
            return {"action": "created", "doc": result["data"]}


# ============================================================
# 主流程
# ============================================================

def main():
    # 检查配置
    if not YUQUE_CONFIG["token"]:
        print("=" * 60)
        print("❌ 未配置语雀 Token")
        print()
        print("请按以下步骤配置：")
        print("1. 访问 https://www.yuque.com/settings/tokens")
        print("2. 创建新 Token（勾选读写权限）")
        print("3. 设置环境变量：")
        print("   export YUQUE_TOKEN='your_token_here'")
        print("   或修改脚本中的 YUQUE_CONFIG['token']")
        print()
        print("4. 配置知识库命名空间：")
        print("   修改 YUQUE_CONFIG['repo_namespace']")
        print("   格式：'用户名/知识库名' 或 '团队/知识库名'")
        print("=" * 60)
        return

    if not YUQUE_CONFIG["repo_namespace"]:
        print("❌ 未配置知识库命名空间 (repo_namespace)")
        print("格式示例：'yourname/lumina' 或 'team/design'")
        return

    # 初始化客户端
    client = YuqueClient(YUQUE_CONFIG["token"], YUQUE_CONFIG["base_url"])
    namespace = YUQUE_CONFIG["repo_namespace"]

    # 验证连接
    print("🔌 连接语雀...")
    try:
        user = client.get_user()
        print(f"✅ 已登录：{user['data']['name']} (@{user['data']['login']})")
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        return

    # 验证知识库
    try:
        repo = client.get_repo(namespace)
        print(f"📚 知识库：{repo['data']['name']} ({namespace})")
    except Exception as e:
        print(f"❌ 知识库访问失败：{e}")
        print(f"   请确认 namespace '{namespace}' 正确且有写入权限")
        return

    print()
    print("=" * 60)
    print("🚀 开始同步...")
    print("=" * 60)

    # 同步每个文档
    results = []
    base_dir = Path(__file__).parent.parent

    for doc_key, doc_config in YUQUE_CONFIG["docs"].items():
        local_path = base_dir / doc_config["local"]
        if not local_path.exists():
            print(f"⚠️  跳过 {doc_key}：文件不存在 {local_path}")
            continue

        print(f"\n📄 处理 {doc_key}...")
        print(f"   源文件：{local_path}")

        # 读取 HTML
        with open(local_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # 转换
        if doc_key == "specs":
            content = extract_specs_section(html_content)
            markdown = "# Lumina 墨光 · 设计规范\n\n" + md(content, heading_style="atx")
        else:
            markdown = html_to_yuque_markdown(html_content, doc_key)

        # 同步
        try:
            result = client.sync_doc(
                namespace,
                doc_config["slug"],
                doc_config["title"],
                markdown,
            )
            action = result["action"]
            doc_url = f"https://www.yuque.com/{namespace}/{doc_config['slug']}"
            print(f"   ✅ {'更新' if action == 'updated' else '创建'}成功")
            print(f"   🔗 {doc_url}")
            results.append({"key": doc_key, "action": action, "url": doc_url})
        except Exception as e:
            print(f"   ❌ 失败：{e}")
            results.append({"key": doc_key, "action": "failed", "error": str(e)})

    # 汇总
    print()
    print("=" * 60)
    print("📊 同步结果")
    print("=" * 60)
    for r in results:
        status = "✅" if r["action"] in ("created", "updated") else "❌"
        action_text = {"created": "新建", "updated": "更新", "failed": "失败"}.get(r["action"], r["action"])
        print(f"  {status} {r['key']}: {action_text}")
        if "url" in r:
            print(f"     {r['url']}")

    success = sum(1 for r in results if r["action"] in ("created", "updated"))
    print()
    print(f"🎉 完成！{success}/{len(results)} 个文档同步成功")


if __name__ == "__main__":
    main()
