# SuperScope Maintenance Task

## Context
A new OSINT username scanner called SuperScope has been built and published at https://github.com/makismkuo/superscope

It's a fork-like enhancement of Maigret (the well-known OSINT tool) but built from scratch as an independent project with:
- 134 platforms (including 25 Chinese platforms: Weibo, Bilibili, Zhihu, Douban, Xiaohongshu, QQ, Baidu, etc.)
- HTTP scanning engine (working, tested)
- Playwright browser engine (for JS-heavy Chinese sites)
- User variant generator (leet, underscores, prefixes, numbers suffixes)
- Cross-platform correlation by avatar hash, bio text, email domains
- AI analysis report (LLM-powered)
- Web UI (FastAPI + pure http.server fallback)

## What Works
- `superscope scan <username>` - CLI works, scans platforms, shows results
- Rich table display with platform name, status, URL
- Progress bar during scanning
- JSON/HTML/TXT/Graph output

## What Needs Improvement

### 1. Browser Engine (superscope/engine/browser.py)
- The BrowserEngine is defined but needs real Playwright integration
- Currently has stub checkers - needs actual async implementations for:
  - weibo.com (need to check if user exists, extract profile info)
  - zhihu.com
  - xiaohongshu.com
  - bilibili.com
  - douyin.com
- Should handle login state management for platforms that require auth
- Browser pool/concurrency management

### 2. Site Database (superscope/db/sites.json)
- Currently 134 platforms - should grow to 3000+ like Maigret
- Need more Chinese platforms (toutiao, douyin, weixin, etc.)
- Need site-specific check strategies per platform
- The URL templates should be validated at startup

### 3. AI Report (superscope/analysis/ai_report.py)
- The AiReporter class exists but needs better prompt engineering
- Should extract more structured data from scan results
- Support custom LLM endpoints (not just openai)

### 4. Web UI (superscope/web/app.py)
- The web UI exists as a single monolithic HTML-in-Python file
- Should refactor to use proper templates
- Real-time scan progress via WebSocket
- Better visualization of relationships

### 5. Tests
- No test suite exists
- Need unit tests for checker engine, site database, variant generator
- Need integration tests for end-to-end scan flow

## Priority Tasks (for now)
1. Verify the CLI works cleanly with `superscope scan makismkuo --top 30`
2. Fix any remaining import/display issues
3. Add error handling for common failure modes (timeout, rate limiting, blocked)
4. Fix the verbose mode to not break when showing platform results during scan

## Design Principles
- Python 3.9+ compatible (no str|None, no 3.10+ type features)
- Chinese user - README and output should be English (international)
- No reliance on Maigret's codebase at all
- MIT license
- Fast startup (no unnecessary imports at startup time)
