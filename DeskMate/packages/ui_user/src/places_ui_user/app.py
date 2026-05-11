import uuid

import streamlit as st

st.set_page_config(page_title="Places — Book a Space", page_icon="🏢", layout="wide")

st.title("Places Booking")
st.markdown("Use the **sidebar** to browse pages, or chat with the booking assistant below.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask me to book a desk or room..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    from places_ui_user.api_client import agent_chat

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = agent_chat(
                prompt,
                session_id=st.session_state.session_id,
                user_id=st.session_state.get("user_id", 1),
            )
        st.write(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
