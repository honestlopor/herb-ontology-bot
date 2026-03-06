import streamlit as st
import requests

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# Sets the browser tab title, icon, and layout style.
# "centered" keeps the chat in a readable column in the middle.
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Thai Chatbot",
    page_icon="🌿",
    layout="centered",
)

# ══════════════════════════════════════════════════════════════════
# CUSTOM CSS
# All visual styling is injected here as a single HTML block.
# Sections:
#   - .stApp          → page background color
#   - .chat-header    → green gradient title banner at the top
#   - .bubble-user    → dark green bubble for user messages (right side)
#   - .bubble-bot     → white bubble for bot messages (left side)
#   - .main-chat-container → wraps all bubbles; padding-bottom reserves
#                            space so the fixed input bar doesn't overlap messages
#   - .msg-row-user   → right-aligns the user bubble row
#   - .bot-row        → flex row containing avatar + bot bubble
#   - .bot-avatar     → circular icon shown to the left of each bot bubble
#   - .bot-bubble-wrap → column flex container for bot-name label + bubble
#   - .bot-name       → small grey label "ผู้ช่วยสมุนไพร" above bot bubble
#   - .spinner        → pure CSS rotating circle used as loading indicator
#   - .hint-box       → light green suggestion bar below the header
#   - [data-testid="stForm"] → overrides Streamlit's form to be fixed
#                              at the bottom of the viewport (like a chat input bar)
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* Page background */
    .stApp { background-color: #f0f7f0; }

    /* Top banner */
    .chat-header {
        background: linear-gradient(135deg, #2d6a4f, #52b788);
        color: white;
        padding: 20px 24px;
        border-radius: 16px;
        margin-bottom: 12px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(45,106,79,0.3);
    }
    .chat-header h1 { margin: 0; font-size: 1.8rem; }
    .chat-header p  { margin: 6px 0 0; opacity: 0.85; font-size: 0.95rem; }

    /* User message bubble — right aligned, dark green */
    .bubble-user {
        background: #2d6a4f;
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 6px 0 6px 20%;
        display: inline-block;
        max-width: 80%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    /* Bot message bubble — left aligned, white */
    .bubble-bot {
        background: white;
        color: #1b4332;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 6px 20% 6px 0;
        display: inline-block;
        max-width: 80%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #d8f3dc;
    }

    /* Scrollable chat area — padding-bottom must be tall enough
       so the last bubble is not hidden behind the fixed input bar */
    .main-chat-container { padding-bottom: 220px; }

    /* Right-aligns the user message row */
    .msg-row-user { text-align: right; margin: 4px 0; }
    .label { font-size: 0.72rem; color: #888; margin: 2px 4px; }

    /* Bot message row: avatar on the left, bubble on the right */
    .bot-row {
        display: flex;
        flex-direction: row;
        align-items: flex-end;
        gap: 8px;
        margin: 6px 0;
        max-width: 80%;
    }

    /* Circular avatar icon next to each bot bubble */
    .bot-avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        min-width: 32px;
        border-radius: 50%;
        background: white;
        color: white;
        font-size: 16px;
        box-shadow: 0 2px 6px rgba(45,106,79,0.3);
        align-self: flex-end; /* sticks avatar to bottom of bubble */
    }

    /* Wraps the bot name label + bubble in a column */
    .bot-bubble-wrap {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        flex: 1;
        min-width: 0; /* prevents flex overflow */
    }

    /* Small label above bot bubble e.g. "ผู้ช่วยสมุนไพร" */
    .bot-name {
        font-size: 0.72rem;
        color: #888;
        margin: 0 0 3px 4px;
    }

    /* Allow bot bubble to fill available width inside the flex row */
    .bot-row .bubble-bot {
        max-width: 100%;
        margin: 0;
        white-space: normal;
        word-break: break-word;
    }

    /* CSS-only spinning circle used as loading indicator inside the bubble.
       To use: <span class="spinner"></span> before your text */
    .spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid #d8f3dc;
        border-top: 2px solid #2d6a4f;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        vertical-align: middle;
        margin-right: 8px;
    }
    @keyframes spin {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Example question hints below the header */
    .hint-box {
        background: #d8f3dc;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 0.88rem;
        color: #1b4332;
    }

    /* Fixes Streamlit's form to the bottom of the screen like a chat input bar.
       Adjust max-width / bottom to reposition if needed. */
    [data-testid="stForm"] {
        position: fixed !important;
        bottom: 20px !important;
        left: 0 !important;
        right: 0 !important;
        background: white !important;
        padding: 10px 24px !important;
        z-index: 1000 !important;
        top: auto !important;
        height: auto !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1) !important;
        max-width: 730px !important;
        width: 90% !important;
        margin: 0 auto !important;
    }

    /* Hide default Streamlit footer and hamburger menu */
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# HEADER BANNER
# Rendered as raw HTML so we can use the custom .chat-header styles.
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="chat-header">
    <h1>🌿 Thai herbal medicine Chatbot</h1>
    <p>Ask about Thai herbal medicine! · Thai Herb Medicine Knowledge Base</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# Streamlit reruns the entire script on every interaction.
# st.session_state persists data across reruns within the same session.
#
#   messages  → list of {"role": "user"|"bot", "text": "..."}
#   searching → bool flag; True while waiting for the API response
#
# The greeting message is added only once on the very first run.
# ══════════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "bot",
        "text": "สวัสดีครับ! ผมคือผู้ช่วยด้านยาสมุนไพรไทย\nถามผมได้เลยว่า 'ยาอะไรรักษาท้องอืด' หรือ 'ยาขมิ้นชันรักษาอะไร'"
    })

# ══════════════════════════════════════════════════════════════════
# HINT BOX
# Shows example questions to guide the user.
# Edit the text here to change the suggestions.
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hint-box">
💡 <strong>ตัวอย่างคำถาม:</strong>
ยาอะไรรักษาท้องอืด &nbsp;|&nbsp;
ยาอะไรรักษาท้องผูก &nbsp;|&nbsp;
ยาอะไรรักษาอาการวิงเวียน &nbsp;|&nbsp;
ยาขมิ้นชันรักษาอะไร
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SEARCHING STATE
# Read the flag before rendering so we know whether to show
# the loading bubble in the current render pass.
# ══════════════════════════════════════════════════════════════════
is_searching = st.session_state.get("searching", False)

# ══════════════════════════════════════════════════════════════════
# CHAT HISTORY RENDERER
# Builds the full chat as one HTML string and renders it in one call.
# This avoids Streamlit adding extra whitespace between elements.
#
# User messages → right-aligned dark green bubble
# Bot messages  → left-aligned white bubble with circular avatar
#
# If is_searching is True, a loading bubble with a CSS spinner is
# appended directly after the last message so it appears inline.
# ══════════════════════════════════════════════════════════════════
history_html = '<div class="main-chat-container">'

for msg in st.session_state.messages:
    if msg["role"] == "user":
        history_html += f"""
        <div class="msg-row-user">
            <span class="label">You</span><br>
            <span class="bubble-user">{msg['text']}</span>
        </div>"""
    else:
        text_html = msg['text'].replace('\n', '<br>')
        history_html += f"""
        <div class="bot-row">
            <div class="bot-avatar">🌱</div>
            <div class="bot-bubble-wrap">
                <span class="bot-name">ผู้ช่วยสมุนไพร</span>
                <span class="bubble-bot">{text_html}</span>
            </div>
        </div>"""

# Loading bubble — only shown while waiting for API response
if is_searching:
    history_html += """
    <div class="bot-row" style="margin-top: 10px;">
        <div class="bot-avatar">💬</div>
        <div class="bot-bubble-wrap">
            <span class="bot-name">ผู้ช่วยสมุนไพร</span>
            <span class="bubble-bot"><span class="spinner"></span>กำลังค้นหา...</span>
        </div>
    </div>"""

history_html += '</div>'
st.markdown(history_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# INPUT FORM
# Fixed at the bottom of the screen via CSS above.
# clear_on_submit=True clears the text field after the user sends.
# ══════════════════════════════════════════════════════════════════
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="message",
            placeholder="พิมพ์คำถามของคุณที่นี่ / Type your question...",
            label_visibility="collapsed"
        )
    with col2:
        submitted = st.form_submit_button("Submit", use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# SEND HANDLER — STEP 1: show user bubble immediately
# When the user submits, we add their message to history, set the
# searching flag to True, then rerun. This causes the page to
# re-render instantly showing the user's bubble + loading indicator
# BEFORE the API call happens — giving instant visual feedback.
# ══════════════════════════════════════════════════════════════════
if submitted and user_input.strip():
    st.session_state.messages.append({"role": "user", "text": user_input.strip()})
    st.session_state.searching = True
    st.rerun()

# ══════════════════════════════════════════════════════════════════
# SEND HANDLER — STEP 2: call the API and get bot reply
# This block only runs on the rerun triggered above (is_searching=True).
# It calls the FastAPI backend, appends the bot reply to history,
# clears the searching flag, then reruns again to show the reply.
#
# Backend endpoint: POST http://127.0.0.1:8000/api/chat
# Request body:  { "user_id": str, "question": str }
# Response body: { "reply": str }
#
# To change the backend URL, update the requests.post() call below.
# ══════════════════════════════════════════════════════════════════
if is_searching and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    question = st.session_state.messages[-1]["text"]
    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/chat",
            json={"user_id": "streamlit_user", "question": question},
            timeout=30
        )
        if response.status_code == 200:
            bot_reply = response.json().get("reply", "ไม่พบคำตอบ")
        else:
            bot_reply = f"❌ เกิดข้อผิดพลาด (HTTP {response.status_code})"
    except requests.exceptions.ConnectionError:
        bot_reply = "❌ ไม่สามารถเชื่อมต่อ API ได้ กรุณาตรวจสอบว่า FastAPI server กำลังทำงานอยู่ที่ port 8000"
    except requests.exceptions.Timeout:
        bot_reply = "⏱️ API ตอบสนองช้าเกินไป กรุณาลองใหม่อีกครั้ง"

    st.session_state.messages.append({"role": "bot", "text": bot_reply})
    st.session_state.searching = False
    st.rerun()