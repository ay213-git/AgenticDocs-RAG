"""עיצוב משותף לממשק הצ'אט (Gradio 6): ערכת נושא, CSS, כותרת ובניית הממשק.

שימוש:
    demo = build_demo(fn=answer, title=..., subtitle=..., badges=[...], examples=[...])
    demo.launch(theme=THEME, css=CSS)
"""
import gradio as gr

THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="violet",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Heebo"), "Arial", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "Consolas", "monospace"],
    radius_size=gr.themes.sizes.radius_lg,
).set(
    button_primary_background_fill="linear-gradient(135deg, #6366f1, #8b5cf6)",
    button_primary_background_fill_hover="linear-gradient(135deg, #4f46e5, #7c3aed)",
    button_primary_text_color="white",
    block_shadow="0 4px 24px rgba(15, 23, 42, 0.06)",
    block_border_width="1px",
)

CSS = """
/* ---------- משתני צבע (בהיר / כהה) ---------- */
:root {
    --app-accent: #6366f1;
    --app-accent-2: #8b5cf6;
    --app-pink: #db2777;
    --app-card: #ffffff;
    --app-card-border: #e2e8f0;
    --app-muted: #64748b;
    --app-bot-bg: #f8fafc;
    --app-tile-bg: #ffffff;
}
.dark {
    --app-card: #0f172a;
    --app-card-border: #1e293b;
    --app-muted: #94a3b8;
    --app-bot-bg: #1e293b;
    --app-tile-bg: #111827;
}

/* ---------- מסגרת כללית ---------- */
.gradio-container {
    max-width: 920px !important;
    margin: 0 auto !important;
    direction: rtl;
    padding-top: 18px !important;
}
footer { display: none !important; }
* { scrollbar-width: thin; scrollbar-color: #a5b4fc transparent; }

/* ---------- כותרת ---------- */
.app-header {
    position: relative;
    overflow: hidden;
    background: linear-gradient(120deg, #4f46e5, #7c3aed, #db2777, #7c3aed, #4f46e5);
    background-size: 300% 300%;
    animation: app-flow 14s ease infinite;
    color: #fff;
    border-radius: 24px;
    padding: 30px 32px 26px;
    margin-bottom: 16px;
    box-shadow: 0 14px 40px rgba(99, 102, 241, .38);
    text-align: right;
}
.app-header::after {
    content: "";
    position: absolute;
    inset-inline-start: -60px;
    top: -60px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,.28), transparent 70%);
    pointer-events: none;
}
@keyframes app-flow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.app-header h1 {
    margin: 0 0 8px;
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -.3px;
    color: #fff;
}
.app-header p {
    margin: 0;
    max-width: 640px;
    font-size: 1.04rem;
    line-height: 1.65;
    color: rgba(255,255,255,.93);
}
.app-badges { margin-top: 18px; display: flex; gap: 8px; flex-wrap: wrap; }
.app-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,.17);
    border: 1px solid rgba(255,255,255,.34);
    padding: 5px 14px;
    border-radius: 999px;
    font-size: .84rem;
    font-weight: 500;
    backdrop-filter: blur(6px);
    color: #fff;
}
.app-status::before {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 0 0 rgba(74, 222, 128, .7);
    animation: app-pulse 2s infinite;
}
@keyframes app-pulse {
    70%  { box-shadow: 0 0 0 8px rgba(74, 222, 128, 0); }
    100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
}

/* ---------- אריחי "איך זה עובד" ---------- */
.app-tiles {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}
.app-tile {
    background: var(--app-tile-bg);
    border: 1px solid var(--app-card-border);
    border-radius: 16px;
    padding: 14px 16px;
    text-align: right;
    transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.app-tile:hover {
    transform: translateY(-3px);
    border-color: var(--app-accent);
    box-shadow: 0 10px 24px rgba(99, 102, 241, .16);
}
.app-tile .ico { font-size: 1.5rem; }
.app-tile b { display: block; margin: 4px 0 2px; font-size: .98rem; }
.app-tile span { color: var(--app-muted); font-size: .84rem; line-height: 1.5; }
@media (max-width: 680px) {
    .app-tiles { grid-template-columns: 1fr; }
    .app-header { padding: 22px 20px; }
    .app-header h1 { font-size: 1.55rem; }
}

/* ---------- הצ'אט ---------- */
#chat-card {
    border: 1px solid var(--app-card-border);
    border-radius: 22px;
    padding: 6px;
    background: var(--app-card);
    box-shadow: 0 8px 30px rgba(15, 23, 42, .07);
}
#chatbot { border: none !important; background: transparent !important; }
#chatbot .message {
    line-height: 1.75 !important;
    border-radius: 18px !important;
    animation: app-pop .28s ease both;
}
@keyframes app-pop {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: none; }
}
#chatbot .bot .message,
#chatbot .message.bot {
    background: var(--app-bot-bg) !important;
    border: 1px solid var(--app-card-border) !important;
}
#chatbot .user .message,
#chatbot .message.user {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 6px 16px rgba(99, 102, 241, .3);
}
#chatbot .message.user *,
#chatbot .user .message * { color: #fff !important; }

/* מקורות ומסלול בתוך תשובות */
#chatbot .message.bot strong,
#chatbot .bot .message strong { color: var(--app-accent); }
#chatbot .message.bot em,
#chatbot .bot .message em {
    display: inline-block;
    margin-top: 6px;
    padding: 2px 10px;
    border-radius: 999px;
    background: rgba(99, 102, 241, .10);
    color: var(--app-accent);
    font-size: .8rem;
    font-style: normal;
}
#chatbot code {
    background: rgba(99, 102, 241, .10);
    padding: 1px 6px;
    border-radius: 6px;
}

/* ---------- קלט ודוגמאות ---------- */
textarea, input[type="text"] { direction: rtl; text-align: right; }
textarea:focus, input[type="text"]:focus {
    border-color: var(--app-accent) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, .22) !important;
}
.gradio-container button.example,
.gradio-container .examples button {
    border-radius: 999px !important;
    transition: transform .15s ease, background .15s ease;
}
.gradio-container button.example:hover,
.gradio-container .examples button:hover {
    transform: translateY(-2px);
    background: rgba(99, 102, 241, .10) !important;
}

.app-footer {
    text-align: center;
    color: var(--app-muted);
    font-size: .8rem;
    margin: 14px 0 4px;
}
.app-footer b { color: var(--app-accent); font-weight: 600; }
"""

DEFAULT_TILES = [
    ("🔎", "חיפוש סמנטי", "לשאלות הסבר והבנה על הפרויקט"),
    ("🗂️", "שליפה מובנית", "רשימות מלאות, הכלל העדכני ושאלות לפי זמן"),
    ("📚", "מקורות בכל תשובה", "כלי, קובץ וציון דמיון, לבדיקה מהירה"),
]


def _header(title: str, subtitle: str, badges: list[str]) -> str:
    chips = '<span class="app-badge app-status">פעיל</span>' + "".join(
        f'<span class="app-badge">{b}</span>' for b in badges
    )
    return (
        f'<div class="app-header"><h1>{title}</h1><p>{subtitle}</p>'
        f'<div class="app-badges">{chips}</div></div>'
    )


def _tiles(tiles) -> str:
    items = "".join(
        f'<div class="app-tile"><div class="ico">{i}</div><b>{t}</b><span>{d}</span></div>'
        for i, t, d in tiles
    )
    return f'<div class="app-tiles">{items}</div>'


def build_demo(fn, examples, title, subtitle, badges=None, tiles=None) -> gr.Blocks:
    """בונה את ממשק הצ'אט המעוצב סביב פונקציית התשובה fn(message, history)."""
    badges = badges or []
    tiles = DEFAULT_TILES if tiles is None else tiles
    with gr.Blocks(title=title) as demo:
        gr.HTML(_header(title, subtitle, badges))
        if tiles:
            gr.HTML(_tiles(tiles))
        with gr.Column(elem_id="chat-card"):
            gr.ChatInterface(
                fn=fn,
                chatbot=gr.Chatbot(
                    elem_id="chatbot",
                    rtl=True,
                    height=540,
                    layout="bubble",
                    show_label=False,
                    placeholder=(
                        "<div style='text-align:center;opacity:.7;padding:46px 12px'>"
                        "<div style='font-size:2.6rem'>💬</div>"
                        "<b style='font-size:1.1rem'>במה אפשר לעזור?</b><br>"
                        "<span style='font-size:.9rem'>שאלי כל שאלה על קבצי התיעוד, "
                        "או בחרי אחת מהדוגמאות למטה</span></div>"
                    ),
                ),
                textbox=gr.Textbox(
                    placeholder="כתבי שאלה בעברית...",
                    rtl=True,
                    container=False,
                    scale=7,
                    submit_btn="שלחי ✈️",
                    stop_btn="עצרי ⏹",
                ),
                examples=examples,
            )
        gr.HTML(
            '<div class="app-footer">נבנה עם <b>LlamaIndex</b> · <b>Cohere</b> · '
            '<b>Pinecone</b> · <b>Gradio</b></div>'
        )
    return demo