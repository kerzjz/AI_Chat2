import streamlit as st
import urllib.request
import urllib.parse
import json
import re

# ==================== 你的配置 ====================
CF_ACCOUNT_ID = "你的account_id"
CF_API_TOKEN = "你的API Token"
MODEL = "@cf/meta/llama-3-8b-instruct"

KNOWLEDGE_URLS = [
    "https://a.com/1",
    "https://a.com/2"
]
# ===================================================

# 网页清洗（去标签、去元数据、去转义）
def clean(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-zA-Z0-9#]+;", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:7000]

# 抓取网页
def fetch(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as f:
            return clean(f.read().decode("utf-8", "ignore"))
    except:
        return ""

# 加载知识库（缓存）
@st.cache_data(ttl=3600)
def load_kb():
    return "\n---\n".join([fetch(u) for u in KNOWLEDGE_URLS])

# 联网搜索
@st.cache_data(ttl=60)
def search(q):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
    return fetch(url)

# 调用CF AI
def ai(prompt):
    try:
        r = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{MODEL}",
            headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"},
            data=json.dumps({"prompt": prompt}).encode(),
            method="POST"
        )
        with urllib.request.urlopen(r, timeout=20) as f:
            return json.load(f)["result"]["response"].strip()
    except:
        return "AI 出错"

# ==================== 主逻辑 ====================
def answer(q, kb):
    p1 = f"""只用中文回答。
知识库：{kb}
问题：{q}
能回答直接答，不能只输出：需要联网"""
    a = ai(p1)
    if "需要联网" not in a:
        return "✅ 知识库", a

    web = search(q)
    p2 = f"""只用中文回答，不编造。
搜索内容：{web}
问题：{q}"""
    return "🌍 联网搜索", ai(p2)

# ==================== 界面：纯HTML ====================
st.set_page_config(page_title="AI 助手", page_icon="🤖")

# 👇 这里全是你要的 HTML 界面
st.markdown("""
<style>
.main { max-width: 700px; margin: 0 auto; }
.chat-box {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 20px;
    height: 500px;
    overflow-y: auto;
    margin-bottom: 16px;
    line-height: 1.5;
}
.user {
    background: #007bff;
    color: white;
    padding: 10px 14px;
    border-radius: 8px;
    margin: 8px 0;
    max-width: 80%;
    margin-left: auto;
}
.bot {
    background: #e9ecef;
    padding: 10px 14px;
    border-radius: 8px;
    margin: 8px 0;
    max-width: 80%;
}
.label { font-size: 12px; color: #666; margin-bottom: 4px; }
</style>

<h2 style="text-align:center;">🤖 知识库 + 联网 AI</h2>
""", unsafe_allow_html=True)

chat = st.empty()
user_input = st.text_input("💬 输入问题：", label_visibility="collapsed")
btn = st.button("🚀 发送", use_container_width=True)

if btn and user_input:
    kb = load_kb()
    src, ans = answer(user_input, kb)

    # 渲染聊天界面
    chat.markdown(f"""
    <div class="chat-box">
        <div class="user">{user_input}</div>
        <div class="label">{src}</div>
        <div class="bot">{ans}</div>
    </div>
    """, unsafe_allow_html=True)
