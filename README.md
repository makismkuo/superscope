# 🔭 SuperScope

**扔一个名字出去，三秒后你看到的是这个人在互联网上的一切。**

一个命令，扫遍200+平台。这不是装逼——你每天在多少网站注册过，你自己都记不清。SuperScope帮你把那些账号翻出来，一个不漏。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-black.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/makismkuo/superscope?style=social)](https://github.com/makismkuo/superscope)

```bash
pip install superscope
superscope scan 用户名
```

---

## 🤯 你为什么要试一次？

**查自己** — 搜你常用的用户名，看看互联网上有多少你早已遗忘的账号。你可能会发现：十年前注册的论坛还在、某个平台的个人资料挂着你的手机号、你的邮箱已经在暗网上流通了。

**查合作对象** — 群里那个"大佬"到底是谁？一个命令，扒出他的技术栈、社交圈、职业轨迹。知乎答主是不是真专家？GitHub上的star是不是刷的？三分钟出答案。

**查网友** — 顶着美女头像跟你聊天的，对应的微博/豆瓣/贴吧账号是什么画风？网络身份能不能对上？

**查面试者** — 简历上的"全栈工程师"在GitHub上有几个项目？StackOverflow回答质量如何？技术博客多久没更新了？

**查邮箱泄露** — 你的邮箱在哪些网站注册过？被数据泄露波及过没有？
```bash
superscope scan youremail@gmail.com --id-type email
```

---

## 🔥 跟同类工具比

| 功能 | Maigret | SuperScope |
|------|:-------:|:----------:|
| HTTP 站点扫描 | 3000+ | 200+（持续增加） |
| 国内平台（微博/知乎/小红书/B站） | ❌ | ✅ Playwright 浏览器引擎 |
| 邮箱搜索 | ❌ | ✅ Gravatar/HIBP/EmailRep/LeakCheck |
| 用户名变体生成 | ❌ | ✅ leet/前缀/后缀/数字 |
| AI 分析报告 | ❌ | ✅ LLM 自动摘要 |
| 跨平台关联合并 | ❌ | ✅ 头像 hash + bio 相似度 |
| 代理轮换 + Tor | ⚠️ | ✅ 内置自动检测 |
| Web 可视化页面 | ❌ | ✅ FastAPI + 实时进度 |
| 搜索结果导出 | TXT | ✅ JSON/HTML/TXT/Graph |

---

## 🚀 30 秒上手

```bash
# 安装
pip install superscope

# 扫用户名
superscope scan 用户名

# 扫邮箱
superscope scan someone@email.com --id-type email

# 扫国内平台（需要装 Playwright）
pip install superscope[playwright]
playwright install chromium
superscope scan 用户名 --browser --tags china

# 生成漂亮报告
superscope scan 用户名 -o report.html

# 打开可视化页面
superscope web
```

更多用法：`superscope scan --help`

---

## 🇨🇳 国内平台专项支持

很多 OSINT 工具在中国水土不服——被墙、JS 渲染、验证码拦截。SuperScope 的浏览器引擎专门解决这个问题。

| 平台 | 类型 | 浏览器 | 备注 |
|------|:----:|:------:|------|
| 微博 Weibo | 社交 | ✅ | |
| 知乎 Zhihu | 问答 | ✅ | |
| 小红书 Xiaohongshu | 生活方式 | ✅ | |
| 抖音 Douyin | 短视频 | ✅ | |
| B站 Bilibili | 视频 | ✅ | |
| 百度贴吧 Baidu Tieba | 论坛 | ❌ | |
| QQ空间 | 社交 | ❌ | |

---

## 🧠 AI 分析

需要 `OPENAI_API_KEY` 环境变量，自动把扫描结果整理成人类可读的调查报告：

```bash
export OPENAI_API_KEY=sk-...
superscope scan 用户名 --ai
```
```
🤖 AI Analysis
┌─────────────────────────────────────────────────────────────┐
│ 该用户名在 8 个平台有注册记录，数字足迹中等。GitHub、    │
│ LinkedIn、Twitter 信息一致，确认是真实个人身份。          │
│ 微博账号表明有中国市场参与。Profile 内容偏向技术方向。    │
│                                                           │
│ 风险等级: 中                                             │
│ 多个平台使用相同用户名，容易被跨平台关联追踪。           │
│                                                           │
│ 建议:                                                     │
│ • 检查各平台隐私设置                                      │
│ • 不同平台使用不同用户名                                  │
│ • 删除 Profile 中的个人信息                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ 架构

```
Username ──► SiteDatabase ──┬── HTTP platforms ──► CheckerEngine ──► CheckResult
                             │                                           │
                             └── Browser platforms ──► BrowserEngine ────┤
                                                                         │
                                                                         ├── Correlator
                                                                         ├── AiReporter
                                                                         └── Report (JSON/HTML/TXT/Web)
```

---

## ⚙️ 配置

```bash
# 代理扫描
superscope scan 用户名 --proxy socks5://127.0.0.1:9050

# Tor 模式
superscope scan 用户名 --tor

# 筛选平台
superscope scan 用户名 --tags social,china
superscope scan 用户名 --country cn
superscope scan 用户名 --top 30

# 多用户批量扫
superscope scan user1 user2 user3
```

| 环境变量 | 用途 |
|----------|------|
| `OPENAI_API_KEY` | AI 分析 API 密钥 |
| `OPENAI_MODEL` | 模型选择（默认 gpt-4o-mini） |
| `OPENAI_API_BASE` | 自定义 API 端点 |

---

## 🤝 贡献代码

加个新平台只需要 3 步：

1. 在 `superscope/db/sites.json` 加一条记录
2. 运行 `superscope scan testuser -p 你的平台名` 测试
3. 提 PR

```json
{
  "name": "你的平台",
  "url_template": "https://你的平台.com/{username}",
  "engine": "http",
  "tags": ["social"],
  "category": "social"
}
```

---

## 📄 License

MIT — 随便用。

---

**好用的话顺手点个 ⭐，让更多人看到。** 你的 star 就是这破项目活下去的口粮。

<p align="center">
  <a href="https://github.com/makismkuo/superscope">github.com/makismkuo/superscope</a>
</p>
