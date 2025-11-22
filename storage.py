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
        if changed:
            self._save()

    def _get_global_guides(self) -> Dict[str, str]:
        guides = self.data.get("guides")
        if guides is None:
            guides = dict(getattr(config, "DEFAULT_GUIDES", {}))
            self.data["guides"] = guides
            self._save()
        return guides

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

    def get_user(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        chat = self._get_chat(chat_id)
        users = chat["users"]
        key = str(user_id)
        if key not in users:
            users[key] = {
                "xp": 0,
                "last_message_ts": 0,
            }
        return users[key]

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
        now_ts: int | None = None,
    ) -> Tuple[int, str, str, bool]:
        if now_ts is None:
            now_ts = int(time.time())
        chat = self._get_chat(chat_id)
        settings = chat["settings"]
        user = self.get_user(chat_id, user_id)
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
