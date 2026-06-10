"""Rule-based persona analyzer — determines what type of person a target is
based on their platform presence and extracted profile data."""

import re
from typing import Any, Dict, List, Optional


# Persona rules: (description, matching_platforms, weight)
PERSONA_RULES = [
    {
        "type": "开发者 / 程序员",
        "description": "技术背景深厚，活跃于开发社区",
        "platforms": {"github", "gitlab", "stackoverflow", "hackernews", "devto", "kaggle"},
        "min_match": 2,
        "weight": 10,
    },
    {
        "type": "游戏玩家",
        "description": "重度游戏爱好者，Steam/Twitch活跃",
        "platforms": {"steam", "twitch", "roblox", "osu"},
        "min_match": 1,
        "weight": 8,
    },
    {
        "type": "社交媒体达人 / 内容创作者",
        "description": "多平台社交活跃，可能是KOL/博主",
        "platforms": {"instagram", "tiktok", "youtube", "twitter", "xiaohongshu"},
        "min_match": 2,
        "weight": 9,
    },
    {
        "type": "设计师 / 创意工作者",
        "description": "活跃于创意设计平台",
        "platforms": {"dribbble", "behance", "pinterest", "deviantart"},
        "min_match": 1,
        "weight": 7,
    },
    {
        "type": "技术爱好者 / 极客",
        "description": "关注技术趋势，喜欢捣鼓",
        "platforms": {"github", "hackernews", "reddit", "stackoverflow", "medium"},
        "min_match": 2,
        "weight": 6,
    },
    {
        "type": "音乐爱好者",
        "description": "音乐平台活跃用户",
        "platforms": {"spotify", "soundcloud", "lastfm"},
        "min_match": 1,
        "weight": 5,
    },
    {
        "type": "国内社交用户",
        "description": "活跃于中文互联网社交平台",
        "platforms": {"weibo", "zhihu", "bilibili", "douban", "qq", "baidu"},
        "min_match": 2,
        "weight": 8,
    },
    {
        "type": "职业人士",
        "description": "有职业社交账号，可能是白领/管理层",
        "platforms": {"linkedin", "xing", "indeed"},
        "min_match": 1,
        "weight": 7,
    },
    {
        "type": "投资者 / 交易者",
        "description": "关注金融市场",
        "platforms": {"tradingview", "coinbase", "binance", "polymarket"},
        "min_match": 1,
        "weight": 5,
    },
    {
        "type": "安全 / 黑客",
        "description": "安全研究背景",
        "platforms": {"hackerone", "bugcrowd", "tryhackme", "hackthebox", "keybase"},
        "min_match": 1,
        "weight": 6,
    },
    {
        "type": "购物达人 / 买家",
        "description": "电商平台活跃",
        "platforms": {"ebay", "amazon", "taobao", "mercado"},
        "min_match": 1,
        "weight": 4,
    },
]


class PersonaAnalyzer:
    """Rule-based persona and profile analyzer.

    Takes scan results and determines:
    - Persona type(s) based on platform presence
    - Extracted bio info (name, location, bio, email)
    """

    def analyze(
        self,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze scan results and produce a persona/profile.

        Args:
            results: List of scan result dicts (with ``platform``, ``status``, ``data`` keys).

        Returns:
            Dict with keys:
            - ``personas``: list of matched persona types with scores
            - ``dominant_persona``: the single best-matching persona
            - ``profile``: extracted profile information
        """
        found_platforms: Dict[str, Dict[str, Any]] = {}
        bio_data: Dict[str, List[str]] = {
            "names": [],
            "locations": [],
            "bios": [],
            "emails": [],
            "urls": [],
        }

        for r in results:
            if r.get("status") != "found":
                continue
            plat = r.get("platform", "")
            found_platforms[plat] = r.get("data") or {}

            # Extract bio info from platform data
            data = r.get("data") or {}
            if data.get("name"):
                bio_data["names"].append(str(data["name"]))
            if data.get("location"):
                bio_data["locations"].append(str(data["location"]))
            if data.get("bio"):
                bio_data["bios"].append(str(data["bio"]))
            if data.get("email"):
                bio_data["emails"].append(str(data["email"]))
            if data.get("url"):
                bio_data["urls"].append(str(data["url"]))

        # Score personas
        persona_scores: List[Dict[str, Any]] = []
        for rule in PERSONA_RULES:
            matched = found_platforms.keys() & rule["platforms"]
            if len(matched) >= rule["min_match"]:
                score = rule["weight"] * len(matched)
                persona_scores.append({
                    "type": rule["type"],
                    "description": rule["description"],
                    "match_count": len(matched),
                    "matched_platforms": sorted(matched),
                    "score": score,
                })

        # Sort by score descending
        persona_scores.sort(key=lambda x: x["score"], reverse=True)

        # Dominant persona
        dominant_persona = persona_scores[0] if persona_scores else {
            "type": "未知 / 普通用户",
            "description": "没有足够平台数据来判断类型",
            "match_count": 0,
            "matched_platforms": [],
            "score": 0,
        }

        return {
            "personas": persona_scores,
            "dominant_persona": dominant_persona,
            "profile": self._build_profile(bio_data),
        }

    @staticmethod
    def _build_profile(bio_data: Dict[str, List[str]]) -> Dict[str, Any]:
        """Build a consolidated profile from scattered bio data."""
        profile: Dict[str, Any] = {
            "possible_names": list(dict.fromkeys(bio_data["names"])),  # dedup, preserve order
            "possible_locations": list(dict.fromkeys(bio_data["locations"])),
            "bios": list(dict.fromkeys(bio_data["bios"])),
            "emails": list(dict.fromkeys(bio_data["emails"])),
        }
        return profile
