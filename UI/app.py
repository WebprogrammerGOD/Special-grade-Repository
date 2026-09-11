import streamlit as st

from account import login_user, register_user
from src.recommendation import travel_chatbot


def _init_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def _show_auth_page():
    st.title("✈️ Travel Chatbot")
    st.subheader("Tài khoản")

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

    # Chưa đăng nhập -> chỉ hiển thị trang đăng nhập/đăng ký.
    if not st.session_state.authenticated:
        _show_auth_page()
        return

    # Đã đăng nhập -> hiển thị tài khoản và chatbot.
    user = st.session_state.user or {}
    username = user.get("username", "User")

    with st.sidebar:
        st.write(f"👤 **{username}**")

        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    travel_chatbot()


if __name__ == "__main__":
    main()