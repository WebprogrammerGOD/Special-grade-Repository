import os
from typing import TYPE_CHECKING

from google import genai
from prompt_toolkit import prompt
import streamlit as st
from dotenv import load_dotenv

from src.preprocessing import BASE_DIR, CONFIG_DIR, load_json
from src.utils import detect_request

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error(
        "Google API key is missing. Add GEMINI_API_KEY to config/.env "
        "(see config/.env.example) or set it as an environment variable."
    )
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# Load configuration
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

system_instruction = f"""
You are SmartInstruct, the travel assistant for Viejar Mucho.

Company:
- Name: Viejar Mucho
- Address: 420 Av. P. de la Reforma, Mexico City, Mexico

Supported functions:
1. Introduce the company.
2. Recommend travel destinations from accommodation preferences.
3. Recommend travel destinations from plane-ticket preferences.
4. Travel destination information.
5. Help explain the supported travel services.

Configured function: {functions}

Rules:
- Be polite, concise, and useful.
- For travel-planning, hotel-booking, and plane-ticket requests, recommend
  destinations from the user's stated preferences and constraints.
- Never use, search, or refer to local travel, hotel, or flight datasets.
- Do not claim live prices, booking availability, flight schedules, or hotel
  availability.
- For unsupported requests, say:
  "I do not support this function. Please contact our company's staff via hotline +5251 - 234 - 5678 for assistance."
"""


def generate_destination_recommendations(prompt: str, request_type: str) -> str:
    """Generate destination advice without querying local booking datasets."""
    request_context = {
        "hotel": "The user is asking about a hotel or accommodation booking.",
        "plane": "The user is asking about a plane ticket or flight booking.",
        "travel": "The user is planning a trip.",
    }[request_type]

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=(
                "Recommend 5 suitable travel destinations for this user. "
                "Treat booking details as travel preferences, "
                "not as a request to search hotels, flights, prices, or availability. "
                "For each destination, give a brief reason it fits and one practical "
                "consideration. Do not claim live prices or availability, and do not "
                "say the choices came from a dataset.\n\n"
            f"User's request: {prompt}"
            ),
            config={"system_instruction": system_instruction},
        )
        return (
            response.text.strip()
            if response.text
            else "I could not generate destination recommendations."
        )
    except Exception as exc:
        return (
            "Sorry, I couldn't generate destination recommendations right now. "
            f"Please try again later. Details: {exc}"
        )


def travel_chatbot(storage: "ChatStorage | None" = None):
    st.title("✈️ Viejar Mucho Travel Chatbot")
    st.caption(
        "Tell me your hotel, flight, or trip preferences and I will recommend "
        "travel destinations."
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

    with st.spinner("🤖 Creating destination recommendations..."):
        if request_type in {"hotel", "plane", "travel"}:
            bot_reply = generate_destination_recommendations(prompt, request_type)

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
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=(
                        f"Conversation context:\n{context}\n\n"
                        f"User request:\n{prompt}"
                    ),
                    config={"system_instruction": system_instruction},
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
