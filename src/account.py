"""Registration and login helpers for app.py."""

import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path


DATABASE = Path(__file__).with_name("accounts.db")


def _connect():
	connection = sqlite3.connect(DATABASE)
	connection.row_factory = sqlite3.Row
	connection.execute(
		"""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			username TEXT NOT NULL UNIQUE COLLATE NOCASE,
			password_hash TEXT NOT NULL,
			salt TEXT NOT NULL
		)
		"""
	)
	connection.commit()
	return connection


def _hash_password(password, salt=None):
	salt = salt or secrets.token_hex(16)
	password_hash = hashlib.pbkdf2_hmac(
		"sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
	).hex()
	return password_hash, salt


def register(username, password):
	"""Create an account and return (success, message)."""
	username = username.strip()
	if len(username) < 3:
		return False, "Username must contain at least 3 characters."
	if len(password) < 8:
		return False, "Password must contain at least 8 characters."

	password_hash, salt = _hash_password(password)
	try:
		with _connect() as connection:
			connection.execute(
				"INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
				(username, password_hash, salt),
			)
		return True, "Account created successfully."
	except sqlite3.IntegrityError:
		return False, "Username is already registered."


def login(username, password):
	"""Return the authenticated user, or None when credentials are invalid."""
	with _connect() as connection:
		user = connection.execute(
			"SELECT id, username, password_hash, salt FROM users WHERE username = ?",
			(username.strip(),),
		).fetchone()

	if user is None:
		return None
	password_hash, _ = _hash_password(password, user["salt"])
	if hmac.compare_digest(password_hash, user["password_hash"]):
		return {"id": user["id"], "username": user["username"]}
	return None
