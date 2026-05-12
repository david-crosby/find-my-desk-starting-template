"""
Accessibility and theme utilities for the DeskMate user UI.

Provides:
  - inject_accessibility(mode, high_contrast) — call once per page render
  - render_theme_controls()                   — sidebar selectors

Theme switching works by injecting <style> blocks that override Streamlit's
default CSS. Dark/system/high-contrast modes override backgrounds, text, inputs,
and buttons throughout the app.

The mic button is injected as a position:fixed element near the chat input. It
uses the browser's SpeechRecognition API (Chrome/Edge) and writes the transcript
into Streamlit's chat textarea via React's native value setter.
"""
from __future__ import annotations

import streamlit as st

# ── Mobile & tablet responsive ───────────────────────────────────────────────

_MOBILE_CSS = """
@media (max-width: 768px) {
    section[data-testid="stSidebar"] { min-width: 82vw !important; }
    [data-testid="stChatInput"] textarea { font-size: 16px !important; }
    .stChatMessage { padding: 6px 4px !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    .stButton > button { min-height: 44px !important; }
    [data-testid="stMetric"] { padding: 10px 8px !important; }
}
@media (min-width: 769px) and (max-width: 1024px) {
    [data-testid="stChatInput"] textarea { font-size: 15px !important; }
    .stChatMessage { padding: 8px 6px !important; }
}
"""

# ── Mic button ────────────────────────────────────────────────────────────────

_MIC_CSS = """
#dm-mic-btn {
    position: fixed;
    bottom: 22px;
    right: 62px;
    z-index: 9999;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 2px solid #cccccc;
    background: #ffffff;
    cursor: pointer;
    font-size: 19px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.18);
    transition: border-color 0.2s, background 0.2s;
    padding: 0;
}
#dm-mic-btn:hover  { border-color: #ff4b4b; background: #fff5f5; }
#dm-mic-btn:focus  { outline: 3px solid #0078d4; outline-offset: 2px; }
#dm-mic-btn.listening {
    background: #ff4b4b !important;
    border-color: #cc0000 !important;
    animation: dmPulse 1s ease-in-out infinite;
}
@keyframes dmPulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,75,75,0.5); }
    50%       { box-shadow: 0 0 0 10px rgba(255,75,75,0); }
}
@media (max-width: 768px) {
    #dm-mic-btn { width: 48px; height: 48px; font-size: 22px; bottom: 18px; right: 58px; }
}
"""

_MIC_HTML = """
<button
  id="dm-mic-btn"
  onclick="dmMicStart()"
  aria-label="Voice input — click to speak"
  title="Voice input (Chrome / Edge)">
  <span aria-hidden="true">🎤</span>
</button>
<script>
(function () {
  function dmMicStart() {
    var Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Rec) {
      alert('Voice input requires Chrome or Edge.');
      return;
    }
    var btn  = document.getElementById('dm-mic-btn');
    var icon = btn.querySelector('span');
    var rec  = new Rec();
    rec.lang = 'en-GB';
    rec.continuous = false;
    rec.interimResults = false;

    btn.classList.add('listening');
    icon.textContent = '⏹';
    btn.setAttribute('aria-label', 'Listening — click to cancel');
    rec.start();

    rec.onresult = function (e) {
      var text = e.results[0][0].transcript;
      var ta = document.querySelector('[data-testid="stChatInput"] textarea');
      if (ta) {
        var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        setter.call(ta, text);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        ta.focus();
      }
    };

    function reset() {
      btn.classList.remove('listening');
      icon.textContent = '🎤';
      btn.setAttribute('aria-label', 'Voice input — click to speak');
    }
    rec.onend  = reset;
    rec.onerror = reset;
  }
  window.dmMicStart = dmMicStart;
}());
</script>
"""

# ── Dark mode ─────────────────────────────────────────────────────────────────

_DARK_CSS = """
.stApp, [data-testid="stAppViewContainer"] { background-color: #0e1117 !important; }
[data-testid="stHeader"] { background-color: #0e1117 !important; border-bottom: 1px solid #333 !important; }
[data-testid="stToolbar"] { background-color: #0e1117 !important; }
[data-testid="stStatusWidget"] { color: #a8a8a8 !important; }
footer, [data-testid="stFooter"], [data-testid="stBottom"] {
    background-color: #0e1117 !important;
    border-top: 1px solid #333 !important;
    color: #a8a8a8 !important;
}
footer a, [data-testid="stFooter"] a { color: #a8a8a8 !important; }
[data-testid="stSidebar"], [data-testid="stSidebarContent"] { background-color: #1a1d2b !important; }
.stMarkdown p, .stMarkdown li, p, li { color: #e0e0e0 !important; }
.stCaption, label, small { color: #a8a8a8 !important; }
h1, h2, h3, h4, h5 { color: #ffffff !important; }
[data-testid="stBottomBlockContainer"],
div:has(> [data-testid="stChatInput"]) { background: #0e1117 !important; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { background: #1a1d2b !important; border-top: 1px solid #333 !important; }
[data-testid="stChatInput"] textarea {
    background: #2d3148 !important;
    color: #fafafa !important;
    -webkit-text-fill-color: #fafafa !important;
    caret-color: #fafafa !important;
    border-color: #555 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #888 !important; -webkit-text-fill-color: #888 !important; }
[data-testid="stChatMessage"] { background: #1a2035 !important; }
.stButton > button { background: #252836 !important; color: #e0e0e0 !important; border-color: #555 !important; }
.stButton > button:hover { background: #353848 !important; border-color: #888 !important; }
input, select { background: #252836 !important; color: #fafafa !important; border-color: #555 !important; }
[data-testid="stMetric"] { background: #1a2035 !important; }
[data-testid="stSelectbox"] > div > div { background: #252836 !important; color: #fafafa !important; }
[data-baseweb="select"] > div { background: #252836 !important; border-color: #555 !important; color: #fafafa !important; }
[data-baseweb="popover"], [data-baseweb="menu"] { background: #252836 !important; }
[role="option"] { background: #252836 !important; color: #fafafa !important; }
[role="option"]:hover, [aria-selected="true"][role="option"] { background: #353848 !important; }
[data-testid="stDecoration"] { display: none !important; }
#dm-mic-btn { background: #252836 !important; border-color: #555 !important; filter: invert(0.8); }
"""

# ── High contrast (WCAG AAA — black / white / yellow) ────────────────────────

_HC_CSS = """
html, body, .stApp { background-color: #000000 !important; font-size: 17px !important; }
[data-testid="stHeader"] { background-color: #000000 !important; border-bottom: 3px solid #ffffff !important; }
[data-testid="stToolbar"] { background-color: #000000 !important; }
footer, [data-testid="stFooter"], [data-testid="stBottom"] {
    background-color: #000000 !important;
    border-top: 3px solid #ffffff !important;
    color: #ffffff !important;
}
footer a, [data-testid="stFooter"] a { color: #ffff00 !important; }
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background-color: #080808 !important;
    border-right: 3px solid #ffffff !important;
}
.stMarkdown p, .stMarkdown li, p, li, span, label { color: #ffffff !important; font-size: 1.15em !important; }
h1, h2, h3, h4 { color: #ffffff !important; font-size: 1.25em !important; font-weight: 800 !important; }
.stCaption, small { color: #dddddd !important; font-size: 1.05em !important; }
[data-testid="stBottomBlockContainer"],
div:has(> [data-testid="stChatInput"]) { background: #000000 !important; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { background: #111 !important; border-top: 3px solid #ffff00 !important; }
[data-testid="stChatInput"] textarea {
    background: #1a1a00 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffff00 !important;
    border: 3px solid #ffff00 !important;
    font-size: 1.15em !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #aaaaaa !important; -webkit-text-fill-color: #aaaaaa !important; }
[data-testid="stChatMessage"] {
    background: #111 !important;
    border: 2px solid #cccccc !important;
    border-radius: 8px !important;
    margin: 6px 0 !important;
}
.stButton > button {
    background: #000 !important; color: #ffff00 !important;
    border: 3px solid #ffff00 !important;
    font-size: 1.15em !important; font-weight: 800 !important; min-height: 48px !important;
}
.stButton > button:hover, .stButton > button:focus {
    background: #ffff00 !important; color: #000 !important;
    outline: 3px solid #ffffff !important;
}
a { color: #ffff00 !important; text-decoration: underline !important; font-weight: 700 !important; }
input, select, textarea {
    background: #000 !important; color: #fff !important;
    border: 3px solid #ffff00 !important; font-size: 1.15em !important;
}
[data-testid="stSelectbox"] > div > div { background: #111 !important; color: #ffffff !important; border-color: #ffff00 !important; }
[data-baseweb="select"] > div { background: #111 !important; border-color: #ffff00 !important; color: #ffffff !important; }
[data-baseweb="popover"], [data-baseweb="menu"] { background: #111 !important; }
[role="option"] { background: #111 !important; color: #ffffff !important; }
[role="option"]:hover, [aria-selected="true"][role="option"] { background: #333300 !important; color: #ffff00 !important; }
[data-testid="stMetric"] { border: 3px solid #ffffff !important; padding: 14px !important; background: #111 !important; }
[data-testid="stMetricValue"] { color: #ffff00 !important; font-size: 1.3em !important; }
[data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 1.1em !important; }
hr, [data-testid="stDivider"] { border-color: #ffffff !important; border-width: 2px !important; }
#dm-mic-btn {
    background: #000 !important; border: 3px solid #ffff00 !important;
    width: 50px !important; height: 50px !important; font-size: 23px !important;
}
"""


def inject_accessibility(mode: str = "light", high_contrast: bool = False) -> None:
    """
    Inject theme CSS and the mic button into the current page.

    Call this once per render, before any sidebar or content blocks.

    Args:
        mode: 'light' | 'dark' | 'system'
        high_contrast: when True, high-contrast CSS takes precedence over mode.
    """
    if high_contrast:
        theme_block = _HC_CSS
    elif mode == "dark":
        theme_block = _DARK_CSS
    elif mode == "system":
        theme_block = f"@media (prefers-color-scheme: dark) {{{_DARK_CSS}}}"
    else:
        theme_block = ""  # Streamlit's default light theme

    st.markdown(
        f"<style>{_MOBILE_CSS}{_MIC_CSS}{theme_block}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(_MIC_HTML, unsafe_allow_html=True)


def render_theme_controls() -> None:
    """
    Render theme selector and high-contrast toggle.

    Must be called inside a `with st.sidebar:` block.
    """
    st.divider()
    st.caption("Display")

    mode = st.selectbox(
        "Theme",
        options=["Light", "Dark", "System"],
        index=["Light", "Dark", "System"].index(
            st.session_state.get("theme_mode", "light").capitalize()
        ),
        key="_dm_theme",
    )
    st.session_state["theme_mode"] = mode.lower()

    high_contrast = st.checkbox(
        "High contrast",
        value=st.session_state.get("high_contrast", False),
        key="_dm_hc",
        help="Larger text and maximum contrast for visual accessibility.",
    )
    st.session_state["high_contrast"] = high_contrast
