import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import config


class BotStorage:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = config.DATA_FILE
        self.path = Path(path)
        self.data: Dict[str, Any] = {"chats": {}}
        self._load()
        self._ensure_globals()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"chats": {}}
        if "chats" not in self.data:
            self.data["chats"] = {}

    def _ensure_globals(self) -> None:
        changed = False
        if "guides" not in self.data or not isinstance(self.data.get("guides"), dict):
            combined = dict(getattr(config, "DEFAULT_GUIDES", {}))
            # migrate legacy per-chat guides if present
            for chat in self.data.get("chats", {}).values():
                settings = chat.get("settings") or {}
                legacy_guides = settings.get("guides")
                if isinstance(legacy_guides, dict):
                    combined.update(legacy_guides)
            self.data["guides"] = combined
            changed = True
        if "keywords" not in self.data or not isinstance(self.data.get("keywords"), list):
            self.data["keywords"] = list(getattr(config, "HELP_KEYWORDS", []))
            changed = True
        if "global_users" not in self.data or not isinstance(
            self.data.get("global_users"), dict
        ):
            global_users: Dict[str, Any] = {}
            # migrate legacy per-chat users
            for chat in self.data.get("chats", {}).values():
                legacy_users = chat.get("users") or {}
                for legacy_key, legacy_data in legacy_users.items():
                    key = str(legacy_key)
                    target = global_users.setdefault(
                        key,
                        {
                            "xp": 0,
                            "last_message_ts": 0,
                        },
                    )
                    target["xp"] += int(legacy_data.get("xp", 0))
                    target["last_message_ts"] = max(
                        int(target.get("last_message_ts", 0)),
                        int(legacy_data.get("last_message_ts", 0)),
                    )
            self.data["global_users"] = global_users
            changed = True
        if "release_cache" not in self.data or not isinstance(
            self.data.get("release_cache"), dict
        ):
            self.data["release_cache"] = {}
            changed = True
        if changed:
            self._save()

    def _get_global_guides(self) -> Dict[str, str]:
        guides = self.data.get("guides")
        if guides is None:
            guides = dict(getattr(config, "DEFAULT_GUIDES", {}))
            self.data["guides"] = guides
            self._save()
        return guides

    def _get_keywords(self) -> List[str]:
        keywords = self.data.get("keywords")
        if keywords is None or not isinstance(keywords, list):
            keywords = list(getattr(config, "HELP_KEYWORDS", []))
            self.data["keywords"] = keywords
            self._save()
        return keywords

    def _resolve_user_key(self, user_id: int, username: str | None) -> str:
        if username:
            return username.lower()
        return str(user_id)

    def _get_global_user(self, user_id: int, username: str | None) -> Dict[str, Any]:
        users = self.data.setdefault("global_users", {})
        key = self._resolve_user_key(user_id, username)
        if key not in users:
            users[key] = {
                "xp": 0,
                "last_message_ts": 0,
            }
        return users[key]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.path)

    def _get_chat(self, chat_id: int) -> Dict[str, Any]:
        key = str(chat_id)
        chats = self.data["chats"]
        if key not in chats:
            chats[key] = {
                "settings": {
                    "xp_per_message": config.XP_PER_MESSAGE,
                    "xp_cooldown_seconds": config.XP_COOLDOWN_SECONDS,
                    "ranks": list(config.DEFAULT_RANKS),
                },
                "users": {},
            }
        return chats[key]

    def get_chat_settings(self, chat_id: int) -> Dict[str, Any]:
        return self._get_chat(chat_id)["settings"]

    def list_chat_ids(self) -> List[int]:
        return [int(chat_id) for chat_id in self.data.get("chats", {}).keys()]

    def get_user(
        self, chat_id: int, user_id: int, username: str | None = None
    ) -> Dict[str, Any]:
        # chat_id kept for compatibility/logical separation of ranks
        self._get_chat(chat_id)
        return self._get_global_user(user_id, username)

    def _get_ranks(self, chat_id: int) -> List[Dict[str, Any]]:
        settings = self.get_chat_settings(chat_id)
        ranks = settings.get("ranks") or []
        ranks.sort(key=lambda r: int(r.get("xp_min", 0)))
        return ranks

    def get_rank_for_xp(self, chat_id: int, xp: int) -> str:
        ranks = self._get_ranks(chat_id)
        current = None
        for r in ranks:
            if xp >= int(r.get("xp_min", 0)):
                current = r
            else:
                break
        return current["name"] if current else "Без ранга"

    def add_message_xp(
        self,
        chat_id: int,
        user_id: int,
        username: str | None,
        now_ts: int | None = None,
    ) -> Tuple[int, str, str, bool]:
        if now_ts is None:
            now_ts = int(time.time())
        chat = self._get_chat(chat_id)
        settings = chat["settings"]
        user = self.get_user(chat_id, user_id, username)
        cooldown = int(settings.get("xp_cooldown_seconds", config.XP_COOLDOWN_SECONDS))
        xp_per_message = int(settings.get("xp_per_message", config.XP_PER_MESSAGE))

        old_xp = int(user.get("xp", 0))
        old_rank = self.get_rank_for_xp(chat_id, old_xp)
        last_ts = int(user.get("last_message_ts", 0))
        if last_ts and now_ts - last_ts < cooldown:
            return old_xp, old_rank, old_rank, False

        new_xp = old_xp + xp_per_message
        user["xp"] = new_xp
        user["last_message_ts"] = now_ts

        new_rank = self.get_rank_for_xp(chat_id, new_xp)
        leveled_up = new_rank != old_rank
        self._save()
        return new_xp, old_rank, new_rank, leveled_up

    def get_release_cache(self) -> Dict[str, Any]:
        return self.data.setdefault("release_cache", {})

    def get_last_release_info(
        self,
    ) -> Tuple[str | None, str | None, str | None, str | None]:
        cache = self.get_release_cache()
        return (
            cache.get("tag"),
            cache.get("published_at"),
            cache.get("summary"),
            cache.get("body"),
        )

    def set_last_release_info(
        self, tag: str, published_at: str | None, summary: str | None, body: str | None
    ) -> None:
        cache = self.get_release_cache()
        cache["tag"] = tag
        cache["published_at"] = published_at
        cache["summary"] = summary
        cache["body"] = body
        self._save()

    def get_release_list(self) -> Tuple[List[Dict[str, Any]], float]:
        cache = self.get_release_cache()
        items = cache.get("list")
        if not isinstance(items, list):
            items = []
        fetched_at = float(cache.get("list_fetched_at") or 0)
        return items, fetched_at

    def set_release_list(self, items: List[Dict[str, Any]]) -> None:
        cache = self.get_release_cache()
        cache["list"] = items
        cache["list_fetched_at"] = time.time()
        self._save()

    def add_rank(self, chat_id: int, xp_min: int, name: str) -> None:
        settings = self.get_chat_settings(chat_id)
        ranks = settings.get("ranks") or []
        ranks.append({"xp_min": int(xp_min), "name": name})
        ranks.sort(key=lambda r: int(r.get("xp_min", 0)))
        settings["ranks"] = ranks
        self._save()

    def list_ranks(self, chat_id: int) -> List[Dict[str, Any]]:
        return list(self._get_ranks(chat_id))

    def reset_ranks(self, chat_id: int) -> None:
        settings = self.get_chat_settings(chat_id)
        settings["ranks"] = list(config.DEFAULT_RANKS)
        self._save()

    def set_guide(self, chat_id: int, key: str, text: str) -> None:
        guides = self._get_global_guides()
        guides[key.lower()] = text
        self._save()

    def delete_guide(self, chat_id: int, key: str) -> bool:
        guides = self._get_global_guides()
        key = key.lower()
        if key in guides:
            del guides[key]
            self._save()
            return True
        return False

    def get_guide(self, chat_id: int, key: str) -> str | None:
        guides = self._get_global_guides()
        return guides.get(key.lower())

    def list_guides(self, chat_id: int) -> Dict[str, str]:
        return dict(self._get_global_guides())

    def list_keywords(self) -> List[str]:
        return list(self._get_keywords())

    def add_keyword(self, keyword: str) -> bool:
        cleaned = keyword.strip().lower()
        if not cleaned:
            return False
        keywords = self._get_keywords()
        if cleaned in keywords:
            return False
        keywords.append(cleaned)
        self._save()
        return True

    def delete_keyword(self, keyword: str) -> bool:
        cleaned = keyword.strip().lower()
        if not cleaned:
            return False
        keywords = self._get_keywords()
        if cleaned in keywords:
            keywords.remove(cleaned)
            self._save()
            return True
        return False

    def add_manual_xp(
        self, chat_id: int, user_id: int, username: str | None, amount: int
    ) -> Tuple[int, str, str, bool]:
        if amount == 0:
            user = self.get_user(chat_id, user_id, username)
            xp = int(user.get("xp", 0))
            rank = self.get_rank_for_xp(chat_id, xp)
            return xp, rank, rank, False
        chat = self._get_chat(chat_id)
        user = self.get_user(chat_id, user_id, username)
        old_xp = int(user.get("xp", 0))
        old_rank = self.get_rank_for_xp(chat_id, old_xp)
        new_xp = max(0, old_xp + int(amount))
        user["xp"] = new_xp
        new_rank = self.get_rank_for_xp(chat_id, new_xp)
        leveled_up = new_rank != old_rank
        self._save()
        return new_xp, old_rank, new_rank, leveled_up
