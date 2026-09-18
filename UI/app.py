import hashlib
from pathlib import Path

import streamlit as st

from src.account import login_user, register_user
from src.storage import ChatStorage
from src.recommendation import travel_chatbot


def _init_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def _chat_storage_for_user(username: str) -> ChatStorage:
    """Return the saved-chat location associated with one account."""
    user_key = hashlib.sha256(username.casefold().encode("utf-8")).hexdigest()
    # app.py lives at the project root (it imports the "src" package), so the
    # project root is this file's own directory, not its parent.
    project_root = Path(__file__).resolve().parent
    return ChatStorage(project_root / "data" / "chat_history" / f"{user_key}.json")


def _show_auth_controls():
    """Render optional account controls without blocking guest chat."""
    st.subheader("Tài khoản")
    st.caption("Bạn có thể hỏi ngay với tư cách khách. Đăng nhập để lưu lịch sử chat.")

    login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập", key="login_username")
            password = st.text_input(
                "Mật khẩu", type="password", key="login_password"
            )
            submitted = st.form_submit_button(
                "Đăng nhập", use_container_width=True
            )

        if submitted:
            if not username or not password:
                st.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            else:
                success, result = login_user(username, password)

                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = result
                    st.session_state.pop("conversation_log", None)
                    st.rerun()
                else:
                    st.error(result)

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Tên đăng nhập", key="register_username")
            password = st.text_input(
                "Mật khẩu", type="password", key="register_password"
            )
            confirm_password = st.text_input(
                "Xác nhận mật khẩu",
                type="password",
                key="register_confirm",
            )
            submitted = st.form_submit_button(
                "Đăng ký", use_container_width=True
            )

        if submitted:
            if not username or not password or not confirm_password:
                st.error("Vui lòng nhập đầy đủ thông tin.")
            elif password != confirm_password:
                st.error("Mật khẩu xác nhận không khớp.")
            else:
                success, message = register_user(username, password)

                if success:
                    st.success(
                        "Đăng ký thành công. Bạn có thể đăng nhập ngay."
                    )
                else:
                    st.error(message)


def main():
    st.set_page_config(
        page_title="Travel Chatbot",
        page_icon="✈️",
        layout="wide",
    )

    _init_auth_state()

    with st.sidebar:
        if st.session_state.authenticated:
            user = st.session_state.user or {}
            username = user.get("username", "User")
            st.write(f"👤 **{username}**")
            st.caption("Lịch sử chat của bạn đang được lưu.")

            if st.button("Đăng xuất", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                # Do not show one account's chat history in a guest session.
                st.session_state.pop("conversation_log", None)
                st.rerun()
        else:
            _show_auth_controls()

    # Guests can use the chatbot for the current browser session. Only an
    # authenticated account receives a ChatStorage instance, so only its
    # questions and answers are written to disk.
    storage = None
    if st.session_state.authenticated:
        username = (st.session_state.user or {}).get("username", "User")
        storage = _chat_storage_for_user(username)

    travel_chatbot(storage)


if __name__ == "__main__":
    main()
