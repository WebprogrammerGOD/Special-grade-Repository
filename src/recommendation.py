import os
from typing import TYPE_CHECKING

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

from src.preprocessing import BASE_DIR, CONFIG_DIR, load_excel, load_csv, load_json
from src.utils import detect_request, format_table, search_dataframe

if TYPE_CHECKING:
    from src.storage import ChatStorage

# Credentials are local configuration and must not be committed in source code.
# Process environment variables take precedence over values in config/.env.
load_dotenv(CONFIG_DIR / ".env")

st.set_page_config(
    page_title="Viejar Mucho Travel Chatbot",
    page_icon="✈️",
    layout="wide",
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error(
        "Google API key is missing. Add GOOGLE_API_KEY to config/.env "
        "(see config/.env.example) or set it as an environment variable."
    )
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)


# Load configuration and datasets
try:
    config = load_json("config.json")
except (FileNotFoundError, ValueError, OSError) as exc:
    st.error(f"Cannot load config.json: {exc}")
    st.stop()

initial_bot_message = config.get(
    "initial_bot_message",
    "Hello! How can I help you with your travel plans?",
)

functions = config.get("function", "travel assistance")

try:
    # The travel-history CSV is deliberately not loaded here. Destination
    # requests are recommendations based on the user's prompt, not searches
    # through historical trips in "Travel details dataset.csv".
    hotel_df = load_csv(
        "Yerevan-Hotels.csv",
        encoding="utf-8",
        index_col=0,
    )
    plane_df = load_excel(
        "Data_Train.xlsx",
        index_col=0,
    )
except (FileNotFoundError, ValueError, KeyError, OSError) as exc:
    st.error(f"Cannot load one of the service datasets: {exc}")
    st.stop()


# Prepare database examples for Gemini's system instruction
hotel_names = (
    ", ".join(
        hotel_df["Hotel Names"]
        .dropna()
        .astype(str)
        .head(50)
        .tolist()
    )
    if "Hotel Names" in hotel_df.columns
    else "Available hotel data"
)

routes = (
    ", ".join(
        plane_df["Route"]
        .dropna()
        .astype(str)
        .head(50)
        .tolist()
    )
    if "Route" in plane_df.columns
    else "Available flight route data"
)

system_instruction = f"""
You are SmartInstruct, the travel assistant for Viejar Mucho.

Company:
- Name: Viejar Mucho
- Address: 420 Av. P. de la Reforma, Mexico City, Mexico

Supported functions:
1. Introduce the company.
2. Accommodation information.
3. Plane ticket / flight route information.
4. Travel destination information.
5. Help explain the supported travel services.

Configured function: {functions}

Examples of known hotels:
{hotel_names}

Examples of known flight routes:
{routes}

Rules:
- Be polite, concise, and useful.
- Do not invent prices, routes, or hotels.
- When the application provides database results, use those results instead of guessing.
- For travel-planning requests, recommend destinations from the user's stated
  preferences. Never use or refer to the Travel details dataset.csv file.
- For unsupported requests, say:
  "I do not support this function. Please contact our company's staff via hotline +5251 - 234 - 5678 for assistance."
"""


try:
    model = genai.GenerativeModel(
        "gemini-3-flash-preview",
        system_instruction=system_instruction,
    )
except Exception as exc:
    st.error(f"Cannot initialize Gemini model: {exc}")
    st.stop()


def travel_chatbot(storage: "ChatStorage | None" = None):
    st.title("✈️ Viejar Mucho Travel Chatbot")
    st.caption(
        "Ask about hotels, plane tickets, travel destinations, "
        "or Viejar Mucho company information."
    )

    if "conversation_log" not in st.session_state:
        saved_history = storage.get_history() if storage else []
        st.session_state.conversation_log = saved_history or [
            {
                "role": "assistant",
                "content": initial_bot_message,
            }
        ]

    with st.sidebar:
        st.header("Chat controls")

        if st.button(
            "🗑️ Clear conversation",
            use_container_width=True,
        ):
            if storage:
                storage.clear()
            st.session_state.conversation_log = [
                {
                    "role": "assistant",
                    "content": initial_bot_message,
                }
            ]
            st.rerun()

        st.divider()
        st.write("Supported services")
        st.write("🏨 Accommodation")
        st.write("✈️ Plane tickets")
        st.write("🌎 Travel destinations")
        st.write("🏢 Company information")

    for message in st.session_state.conversation_log:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Type your request...")

    if not prompt:
        return

    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.conversation_log.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    request_type = detect_request(prompt)

    with st.spinner("🤖 Searching for valid data..."):
        if request_type == "hotel":
            result = search_dataframe(
                hotel_df,
                prompt,
                ["Hotel Names", "City", "Country"],
                limit=8,
            )

            if not result.empty:
                bot_reply = format_table(
                    result,
                    [
                        ("Hotel Names", "Hotel"),
                        ("Price", "Price"),
                        ("City", "City"),
                        ("Country", "Country"),
                    ],
                    "Available accommodations",
                )
            else:
                bot_reply = model.generate_content(prompt)

        elif request_type == "plane":
            result = search_dataframe(
                plane_df,
                prompt,
                ["Route", "Airline"],
                limit=8,
            )

            if not result.empty:
                bot_reply = format_table(
                    result,
                    [
                        ("Route", "Route"),
                        ("Price", "Price"),
                        ("Airline", "Airline"),
                    ],
                    "Available plane tickets",
                )
            else:
                bot_reply = model.generate_content(prompt)

        elif request_type == "travel":
            # Destination advice is intentionally generated from the user's
            # request rather than matched against Travel details dataset.csv.
            try:
                response = model.generate_content(
                    "Recommend 3 suitable travel destinations for this user. "
                    "Use only the preferences and constraints in their message. "
                    "For each destination, give a brief reason it fits and one "
                    "practical consideration. Do not claim live prices, current "
                    "availability, or that the choices came from a dataset.\n\n"
                    f"User's trip request: {prompt}"
                )
                bot_reply = (
                    response.text.strip()
                    if response.text
                    else "I could not generate destination recommendations."
                )
            except Exception as exc:
                bot_reply = (
                    "Sorry, I couldn't generate destination recommendations right now. "
                    f"Please try again later. Details: {exc}"
                )

        elif request_type == "company":
            bot_reply = (
                "### About the company Viejar Mucho\n"
                "Provides the \"out of the world\" travel services including accommodation, plane tickets, "
                "Viejar Mucho is a travel company located at "
                "420 Av. P. de la Reforma, Mexico City, Mexico.\n"
                "For more information, please contact our staff via hotline +5251 - 234 - 5678."
            )

        elif request_type == "help":
            bot_reply = (
                "### Can I help you with these services?\n"
                "You can type the questions that related to these topics:\n"
                "- 🏢 Company information\n"
                "- 🏨 Accommodation\n"
                "- ✈️ Plane tickets\n"
                "- 🌎 Travel destinations"
            )
            with st.chat_message("assistant"): st.markdown(bot_reply)

        else:
            recent_history = st.session_state.conversation_log[-6:]

            context = "\n".join(
                f"{msg['role']}: {msg['content']}"
                for msg in recent_history
            )

            try:
                response = model.generate_content(
                    f"Conversation context:\n{context}\n\n"
                    f"User request:\n{prompt}"
                )

                bot_reply = (
                    response.text.strip()
                    if response.text
                    else "I could not generate a response."
                )

            except Exception as exc:
                bot_reply = (
                    "Sorry, I couldn't process your request right now. "
                    f"Please try again later. Details: {exc}"
                )

    with st.chat_message("assistant"):
        st.markdown(bot_reply)

    st.session_state.conversation_log.append(
        {
            "role": "assistant",
            "content": bot_reply,
        }
    )

    if storage:
        storage.save_exchange(prompt, str(bot_reply))
