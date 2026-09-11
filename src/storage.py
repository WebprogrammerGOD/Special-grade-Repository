"""Persistent storage for user questions and assistant answers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ChatStorage:
	"""Store chat messages in a JSON file."""

	def __init__(self, file_path: str | Path = "chat_history.json") -> None:
		self.file_path = Path(file_path)

	def _load(self) -> list[dict[str, Any]]:
		if not self.file_path.exists():
			return []

		try:
			data = json.loads(self.file_path.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError):
			return []

		return data if isinstance(data, list) else []

	def _save(self, messages: list[dict[str, Any]]) -> None:
		self.file_path.parent.mkdir(parents=True, exist_ok=True)
		temporary_path = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
		temporary_path.write_text(
			json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8"
		)
		temporary_path.replace(self.file_path)

	def add_message(self, role: str, content: str) -> dict[str, Any]:
		"""Add a message with role ``user`` or ``assistant`` and return it."""
		if role not in {"user", "assistant", "system"}:
			raise ValueError("role must be 'user', 'assistant', or 'system'")
		if not isinstance(content, str) or not content.strip():
			raise ValueError("content must be a non-empty string")

		message = {
			"role": role,
			"content": content,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		messages = self._load()
		messages.append(message)
		self._save(messages)
		return message

	def save_exchange(self, question: str, answer: str) -> list[dict[str, Any]]:
		"""Store one user question and its assistant answer."""
		self.add_message("user", question)
		self.add_message("assistant", answer)
		return self.get_history()

	def get_history(self) -> list[dict[str, Any]]:
		"""Return all stored messages in chronological order."""
		return self._load()

	def clear(self) -> None:
		"""Delete the stored chat history."""
		if self.file_path.exists():
			self.file_path.unlink()


if __name__ == "__main__":
	storage = ChatStorage()
	storage.save_exchange("What is Python?", "Python is a programming language.")
	print(json.dumps(storage.get_history(), ensure_ascii=False, indent=2))
