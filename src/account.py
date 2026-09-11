"""Account registration and login helpers for the travel chatbot.

The public functions are intentionally small so they can be called directly
from ``app.py`` without requiring a database or third-party package.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any


_DATA_FILE = Path(__file__).with_name("users.json")
_ITERATIONS = 310_000


def _load_users() -> dict[str, dict[str, Any]]:
	try:
		with _DATA_FILE.open("r", encoding="utf-8") as file:
			data = json.load(file)
		return data if isinstance(data, dict) else {}
	except (FileNotFoundError, json.JSONDecodeError, OSError):
		return {}


def _save_users(users: dict[str, dict[str, Any]]) -> None:
	_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
	temporary = _DATA_FILE.with_suffix(".tmp")
	with temporary.open("w", encoding="utf-8") as file:
		json.dump(users, file, indent=2, ensure_ascii=False)
	os.replace(temporary, _DATA_FILE)


def _normalise_username(username: str) -> str:
	return username.strip().casefold()


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
	salt = salt or secrets.token_bytes(16)
	password_hash = hashlib.pbkdf2_hmac(
		"sha256", password.encode("utf-8"), salt, _ITERATIONS
	)
	return salt.hex(), password_hash.hex()


def register_user(username: str, password: str, **profile: Any) -> tuple[bool, str]:
	"""Create and persist an account, returning ``(success, message)``."""
	username = _normalise_username(username)
	if len(username) < 3:
		return False, "Username must contain at least 3 characters."
	if len(password) < 8:
		return False, "Password must contain at least 8 characters."

	users = _load_users()
	if username in users:
		return False, "That username is already registered."

	salt, password_hash = _hash_password(password)
	users[username] = {
		"username": username,
		"salt": salt,
		"password_hash": password_hash,
		**profile,
	}
	_save_users(users)
	return True, "Registration successful."


def login_user(username: str, password: str) -> tuple[bool, dict[str, Any] | str]:
	"""Validate credentials, returning ``(success, user-or-error-message)``."""
	username = _normalise_username(username)
	user = _load_users().get(username)
	if not user:
		return False, "Invalid username or password."

	try:
		_, password_hash = _hash_password(password, bytes.fromhex(user["salt"]))
		valid = hmac.compare_digest(password_hash, user["password_hash"])
	except (KeyError, TypeError, ValueError):
		valid = False
	if not valid:
		return False, "Invalid username or password."

	return True, {key: value for key, value in user.items() if key not in {"salt", "password_hash"}}


def user_exists(username: str) -> bool:
	"""Return whether a username has been registered."""
	return _normalise_username(username) in _load_users()
