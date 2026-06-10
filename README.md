# 🔭 SuperScope

**OSINT Username Scanner — Find where a username exists across the internet.**

SuperScope is a modern async username scanner with a browser engine for JavaScript-heavy platforms, AI-powered analysis, proxy rotation, and comprehensive Chinese platform support.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/github-makismkuo/superscope-0d9488)](https://github.com/makismkuo/superscope)

---

## ✨ Features

- **🔍 200+ Platforms**: Check usernames across social networks, coding platforms, forums, and more
- **🇨🇳 Chinese Platform Support**: Weibo, Zhihu, Xiaohongshu, Douyin, Bilibili, and others
- **🌐 Browser Engine**: Playwright-based engine for JS-rendered platforms (Weibo, Zhihu, etc.)
- **🤖 AI Analysis**: LLM-powered report generation (OpenAI-compatible API)
- **🔄 Proxy Rotation**: SOCKS5/HTTP proxy pool with auto Tor detection
- **🔗 Cross-Platform Correlation**: Smart matching via avatar hashes, bios, emails, and display names
- **🧩 Username Variants**: Leet speak, separators, number suffixes, and prefix generation
- **📊 Rich Reports**: JSON, HTML, TXT, and interactive web UI with graphs
- **⚡ Async Architecture**: Concurrent checks with configurable timeouts and retries
- **🖥️ Web UI**: Standalone web interface (FastAPI or pure http.server fallback)

---

## 🚀 Quick Start

### Installation

```bash
# Basic install
pip install superscope

# With browser engine (for Chinese platforms)
pip install superscope[playwright]
playwright install chromium

# With AI analysis
pip install superscope[openai]

# Everything
pip install superscope[all]
```

### Scan a Username

```bash
# Basic scan (all platforms)
superscope scan johndoe

# Scan with browser engine for Chinese platforms
superscope scan johndoe --browser

# Scan specific platforms
superscope scan johndoe -p github,twitter,weibo

# Filter by country or tags
superscope scan johndoe --country cn
superscope scan johndoe --tags social,china

# Top 30 platforms only
superscope scan johndoe --top 30

# Save results
superscope scan johndoe -o report.json
superscope scan johndoe -o report.html

# With proxy
superscope scan johndoe --proxy socks5://127.0.0.1:9050

# Tor mode (auto-detect)
superscope scan johndoe --tor

# AI analysis (requires OPENAI_API_KEY)
superscope scan johndoe --ai

# Multiple usernames
superscope scan johndoe janedoe bob

# Verbose output
superscope scan johndoe -vv
```

### Launch Web UI

```bash
superscope web
# Opens at http://127.0.0.1:8080

# Custom host/port
superscope web --host 0.0.0.0 --port 9000
```

### Update Platform Database

```bash
superscope db-update
superscope db-update --force
```

---

## 📋 Examples

### Basic Scan Report

```bash
$ superscope scan johndoe

SuperScope v0.1.0 — Enhanced OSINT Username Scanner

Scanning username: johndoe
Platforms: 28 total (23 HTTP, 5 browser)
Timeout: 15s, Retries: 3

  ✓ github                found
  ✓ twitter               found
  — reddit                not_found
  ✓ linkedin              found
  ✓ instagram             found
  ✓ weibo                 found
  ...

Results for johndoe
  Found: 8  Not found: 12  Errors: 3

┌──────────────┬──────────┬──────────┬──────────────────┬──────────┬──────────────────────┐
│ Platform     │ Status   │ Name     │ Bio              │ Location │ URL                  │
├──────────────┼──────────┼──────────┼──────────────────┼──────────┼──────────────────────┤
│ github       │ ✓ Found  │ John Doe │ Full-stack dev   │ NYC      │ https://github.com/… │
│ twitter      │ ✓ Found  │ @johndoe │ I tweet about…   │          │ https://twitter.com/… │
│ linkedin     │ ✓ Found  │ John Doe │ Software Eng...  │ New York │ https://linkedin.com/… │
│ weibo        │ ✓ Found  │ 约翰多   │ 程序员           │ 北京     │ https://weibo.com/u/… │
└──────────────┴──────────┴──────────┴──────────────────┴──────────┴──────────────────────┘

Cross-Platform Correlations: 2 group(s)
  github ↔ linkedin (confidence: 0.55, matched by: display_name, bio_similarity)
  twitter ↔ weibo (confidence: 0.3, matched by: bio_similarity)
```

### AI-Powered Analysis

```bash
$ export OPENAI_API_KEY=sk-...
$ superscope scan johndoe --ai --top 30

🤖 AI Analysis
┌─────────────────────────────────────────────────────────────┐
│ Username 'johndoe' appears across 8 platforms with a        │
│ moderate digital footprint. The user has consistent naming   │
│ across GitHub, LinkedIn, and Twitter, suggesting a real      │
│ professional identity. Weibo presence indicates Chinese      │
│ market engagement. Profile bios show technical focus.        │
│                                                              │
│ Risk Assessment: MEDIUM                                      │
│ Multiple platforms with consistent identity make this user   │
│ more easily identifiable.                                    │
│                                                              │
│ Recommendations:                                             │
│ • Review privacy settings on all found platforms             │
│ • Consider using different usernames across platforms        │
│ • Remove personally identifying info from bios where possible│
└─────────────────────────────────────────────────────────────┘
```

### Save HTML Report

```bash
superscope scan johndoe -o report.html --browser
# Opens a beautiful standalone HTML report with all findings
```

---

## 🇨🇳 Chinese Platform Support

SuperScope features built-in support for Chinese platforms via its Playwright browser engine:

| Platform     | Type        | Requires Browser | URL Pattern                              |
|-------------|-------------|:----------------:|------------------------------------------|
| Weibo       | Microblog   | ✅               | `weibo.com/u/{username}`                |
| Zhihu       | Q&A         | ✅               | `zhihu.com/people/{username}`           |
| Xiaohongshu | Lifestyle   | ✅               | `xiaohongshu.com/user/profile/{username}`|
| Douyin      | Short Video | ✅               | `douyin.com/user/{username}`            |
| Bilibili    | Video       | ✅               | `space.bilibili.com/{username}`         |
| Baidu Tieba | Forum       | ❌               | `tieba.baidu.com/home/main?un={username}`|
| QQ/Qzone    | Social      | ❌               | `user.qzone.qq.com/{username}`          |

> **Note**: Chinese platforms require the browser engine. Install with:
> ```bash
> pip install superscope[playwright]
> playwright install chromium
> ```

---

## ✨ Feature Highlights

## 🏗️ Architecture

```
superscope/
├── cli.py              # Click CLI: scan, web, db-update
├── web/
│   └── app.py          # Web UI (FastAPI + http.server fallback)
├── engine/
│   ├── checker.py      # Async HTTP checker (httpx)
│   ├── browser.py      # Playwright browser engine
│   └── proxy.py        # Proxy manager with Tor detection
├── analysis/
│   ├── correlator.py   # Cross-platform identity correlation
│   ├── variants.py     # Username variant generation
│   └── ai_report.py    # LLM-powered analysis
├── db/
│   ├── sites.py        # Platform database loader/filter
│   ├── updater.py      # Remote registry updater
│   └── sites.json      # Platform definitions (28 platforms)
└── utils/
    └── helpers.py      # Domain extraction, text similarity, hashing
```

### Data Flow

```
Username ──► SiteDatabase (filter by tags/country/top)
                │
                ├── HTTP platforms ──► CheckerEngine (concurrent async checks)
                │                           │
                │                           └──► CheckResult (found/not_found/error)
                │
                └── Browser platforms ──► BrowserEngine (Playwright)
                                             │
                                             └──► CheckResult
                                                    │
                                                    ├── Correlator (cross-platform matching)
                                                    │       │
                                                    │       └── CorrelationResult
                                                    │
                                                    ├── AiReporter (LLM analysis)
                                                    │       │
                                                    │       └── AiReport
                                                    │
                                                    └── Rich display + file export
```

---

## ⚙️ Configuration

### Environment Variables

| Variable          | Description                          | Default             |
|-------------------|--------------------------------------|---------------------|
| `OPENAI_API_KEY`  | API key for AI analysis              | —                   |
| `OPENAI_MODEL`    | LLM model for analysis               | `gpt-4o-mini`       |
| `OPENAI_API_BASE` | Custom API endpoint                  | `https://api.openai.com/v1` |

### Proxy Support

```bash
# SOCKS5 proxy
superscope scan johndoe --proxy socks5://127.0.0.1:9050

# HTTP proxy
superscope scan johndoe --proxy http://proxy.example.com:8080

# Authenticated proxy
superscope scan johndoe --proxy http://user:pass@proxy:8080

# Auto Tor detection
superscope scan johndoe --tor
```

---

## 🛠️ Development

```bash
# Clone and install in development mode
git clone https://github.com/makismkuo/superscope.git
cd superscope
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy superscope

# Formatting
ruff format superscope/
```

### Building from Source

```bash
pip install build
python -m build
pip install dist/superscope-*.whl
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to help:

1. **Add platforms**: Edit `superscope/db/sites.json` with new platform definitions
2. **Improve detection**: Add checkers to `superscope/engine/checker.py`
3. **Browser profiles**: Add Playwright profiles in `superscope/engine/browser.py`
4. **Fix issues**: Check the [issue tracker](https://github.com/makismkuo/superscope/issues)
5. **Documentation**: Improve this README or add inline docs

### Adding a New Platform

1. Add an entry to `superscope/db/sites.json`:
   ```json
   {
     "name": "yourplatform",
     "url_template": "https://yourplatform.com/{username}",
     "engine": "http",
     "tags": ["social", "your-region"],
     "country": "global",
     "rank": 50,
     "category": "social"
   }
   ```
2. For browser-required platforms, add a `BrowserProfile` in `browser.py`
3. Test: `superscope scan testuser -p yourplatform`

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Nous Research](https://nousresearch.com) — AI research and development
- All open-source contributors who make OSINT tools better

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/makismkuo">makismkuo</a></sub>
</p>
