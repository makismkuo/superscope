# 🔭 SuperScope

**扔一个用户名，3秒扫遍全网——找到这个人在所有平台的痕迹。**

一个名字，200+ 个平台，30 秒出结果。SuperScope 能告诉你一个用户名在哪里注册过、在哪里活跃、暴露了什么信息。查自己、查合作对象、查网友，一个命令搞定。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-black.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/makismkuo/superscope?style=social)](https://github.com/makismkuo/superscope)

```bash
pip install superscope
superscope scan 用户名
```

---

## 🤯 它到底能做什么？

### 查你自己

搜一下你的常用用户名，看看在互联网上留下了多少脚印——你会发现有些账号自己都忘了。

```bash
superscope scan yourname
```
```
Results for yourname
  Found: 12  Not found: 16  Errors: 2

  github        ✓ Found     https://github.com/yourname
  twitter       ✓ Found     https://twitter.com/yourname
  instagram     ✓ Found     https://instagram.com/yourname
  steam         ✓ Found     https://steamcommunity.com/id/yourname
  ...
```

### 查合作对象

跟你对接的人到底什么背景？一个用户名，技术栈、社交圈、职业经历全搜出来。

### 查网友

群里的"大佬"真货还是装的？能不能对上多平台身份？

### 查邮箱泄露

```bash
superscope scan youremail@gmail.com --id-type email
```

你的邮箱在哪些网站注册过？有没有被泄露？

---

## 🔥 跟同类工具比强在哪？

| 功能 | Maigret | SuperScope |
|------|:-------:|:----------:|
| HTTP 站点扫描 | ✅ 3000+ | ✅ 200+（持续增加） |
| 国内平台（微博/知乎/小红书/B站） | ❌ | ✅ Playwright 浏览器引擎 |
| 邮箱搜索 | ❌ | ✅ Gravatar/HIBP/EmailRep/LeakCheck |
| 用户名变体生成 | ❌ | ✅ leet/前缀/后缀/数字 |
| AI 分析报告 | ❌ | ✅ LLM 自动摘要 |
| 跨平台关联合并 | ❌ | ✅ 头像 hash + bio 相似度 |
| 代理轮换 + Tor | ⚠️ | ✅ 内置自动检测 |
| Web 可视化页面 | ❌ | ✅ FastAPI + 实时进度 |
| 搜索结果导出 | ✅ TXT | ✅ JSON/HTML/TXT/Graph |

**不是说Maigret不好**——它做了6年，3000+站点，OSINT圈标杆。SuperScope的目标不是取代，而是在它没做好的地方补上：**国内平台、浏览器引擎、AI分析、跨平台关联**。

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

MIT — 随便用、随便改、随便发。

---

<p align="center">
  <sub>🔭 <a href="https://github.com/makismkuo/superscope">github.com/makismkuo/superscope</a></sub>
</p>
<p align="center">
  <sub>好用的话点个 ⭐，让更多人看到</sub>
</p>
