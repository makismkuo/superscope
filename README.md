# 🔭 SuperScope

**扔一个名字，三秒后你看到的是这个人在互联网上的一切。**

一键扫遍 200+ 国内+国外平台，支持邮箱/用户名/手机号/Steam ID 搜索。开源免费，装了就甩不掉。

```bash
pip install superscope
superscope scan 用户名
```

---

## 🔥 这玩意儿能干什么？

| 场景 | 怎么做 | 结果 |
|------|--------|------|
| **查自己** | `superscope scan 你的用户名` | 把你遗忘了10年的账号全翻出来，看看哪些还挂着你的手机号 |
| **查合作对象** | `superscope scan 对方用户名` | GitHub/知乎/微博/豆瓣一网打尽，他是不是真大佬三分钟见分晓 |
| **查网友** | `superscope scan 对面昵称` | 顶着美女头像跟你聊天的人，对应的账号是什么画风？ |
| **查邮箱泄露** | `superscope scan 邮箱@xx.com --id-type email` | 你的邮箱在哪些站注册过？暗网上有没有你的信息？ |
| **查Steam** | `superscope scan 7656119... --id-type steam_id` | 这人Steam上都玩了什么，有没有开挂记录？ |

---

## 🚀 为什么是 SuperScope 而不是别的？

| 场景 | Maigret（同类工具） | SuperScope（就是不一样） |
|------|:------:|:----------:|
| ⏱ 安装速度 | 慢，依赖一堆 | **3秒 pip install** |
| 🇨🇳 微博/知乎/小红书/B站 | ❌ 不支持 | ✅ **浏览器引擎直扫，国内平台全覆盖** |
| 📧 搜邮箱 | ❌ 不支持 | ✅ Gravatar/HIBP/EmailRep/LeakCheck |
| 📱 搜手机号 | ❌ 不支持 | ✅ TrueCaller 集成 |
| 🎮 搜Steam ID | ❌ 不支持 | ✅ Steam Profile 查 |
| 🤖 AI分析报告 | ❌ 没有 | ✅ LLM自动出人物档案 |
| 🕸 Web UI可视化 | ❌ 纯终端 | ✅ 网页界面实时看结果 |
| 🧠 用户名变体自动生成 | ❌ 没有 | ✅ leet/前缀/后缀/数字一网打尽 |
| 🕵️ 代理/Tor内置 | ⚠️ 手动配置 | ✅ 自动检测开箱即用 |
| 📄 导出格式 | 只有TXT | ✅ JSON/HTML/TXT/Graph/网页 |

**一句话：Maigret能扫的SuperScope都能扫，Maigret扫不了的SuperScope也能扫。**

---

## ⚡ 3秒上手

```bash
# 安装
pip install superscope

# 搜用户名
superscope scan someone

# 搜邮箱（查泄露）
superscope scan you@gmail.com --id-type email

# 搜 Steam ID
superscope scan 76561198429152906 --id-type steam_id

# 搜手机号
superscope scan +8613800138000 --id-type phone

# 带上浏览器引擎（需要 Playwright），扫国内平台
pip install superscope[playwright]
python3 -m playwright install chromium
superscope scan someone --browser --tags china

# 启动 Web 界面
superscope web

# 生成 HTML 报告
superscope scan someone -o report.html
```

---

## 🧠 它能挖多深？

SuperScope 不是只查"这名字存不存在"那么简单。它还会：

- **自动生成变体** → `john_doe` → `john.doe` `johndoe_` `john_doe_official` `john_doe_2026` ...
- **跨平台关联** → 不同平台的头像hash、bio文本相似度匹配 → 发现伪装账号
- **AI 总结** → OpenAI/兼容API → 自动输出人物档案、风险评估、清理建议
- **代理/Tor 自动检测** → proxy 和 Tor 开箱即用，不用额外配置

---

## 🗺 平台覆盖

| 区域 | 平台 |
|------|------|
| 🌏 国际 | GitHub, Twitter/X, Reddit, Instagram, TikTok, Telegram, Steam, Hacker News, Stack Overflow, Medium, Dev.to, Keybase, GitLab, Bitbucket, Pinterest, Twitch, Spotify + 100+ |
| 🇨🇳 国内 | QQ空间、微博、知乎、Bilibili、小红书、豆瓣、百度、贴吧、CSDN、掘金、V2EX、SegmentFault、网易云音乐、虎嗅 + 更多浏览器引擎覆盖 |
| 📧 邮箱 | Gravatar, HaveIBeenPwned, EmailRep, LeakCheck |
| 📱 手机 | TrueCaller |

---

## 📦 安装

```bash
# 基础版（HTTP扫描）
pip install superscope

# 完整版（浏览器 + AI + Web）
pip install "superscope[all]"

# 浏览器引擎
pip install "superscope[playwright]"
python3 -m playwright install chromium

# 从源代码
git clone https://github.com/makismkuo/superscope.git
cd superscope && pip install -e .
```

---

## 🖥 Web UI

```bash
superscope web
```

打开浏览器访问 `http://127.0.0.1:8080` — 可视化搜索、实时进度、结果导出。不需要懂命令行也能用。

---

## 📄 输出格式

```bash
# 表格（默认）
superscope scan someone

# JSON（供程序处理）
superscope scan someone -f json

# HTML 报告
superscope scan someone -f html -o report.html

# 关系图
superscope scan someone -f graph

# 纯文本
superscope scan someone -f txt
```

---

## 👥 适用人群

- **HR/招聘** — 面试前扫一下，简历水分一秒现形
- **安全从业者** — 社工、红队、渗透测试标配
- **吃瓜群众** — 谁在群里装逼？一个命令扫原形
- **自媒体人** — 合作前查对方，避免被坑
- **所有人** — 查查自己，看看互联网上谁在冒充你

---

## 🙏 Acknowledgments

- All open-source contributors who make OSINT tools better

---

<p align="center">
  <b>MIT License</b> · 开源 · 免费 · 没有广告
  <br>
  <a href="https://github.com/makismkuo/superscope">GitHub</a>
</p>
