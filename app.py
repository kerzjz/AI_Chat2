import streamlit as st
import urllib.request
import urllib.parse
import json
import re

# ===================== 全局配置（无密钥、全由用户输入） =====================
st.set_page_config(page_title="多轮AI助手", page_icon="🤖", layout="centered")

# 侧边栏：用户自己填写 API 信息
with st.sidebar:
    st.title("🔐 API 配置")
    CF_ACCOUNT_ID = st.text_input("Cloudflare Account ID", type="password")
    CF_API_TOKEN = st.text_input("API Token", type="password")
    MODEL = st.text_input("模型名称", value="@cf/meta/llama-3-8b-instruct")

    st.divider()
    st.title("📚 知识库")
    KB_URL1 = st.text_input("知识库链接 1", value="https://jxsy.bearblog.dev/")
    KB_URL2 = st.text_input("知识库链接 2", value="")

# 初始化对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------
# 网页清洗
# ------------------------------
def clean_html(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-z0-9#]+;", " ", html, flags=re.I)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:7000]

# ------------------------------
# 抓取页面
# ------------------------------
def fetch_page(url):
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as f:
            return clean_html(f.read().decode("utf-8", "ignore"))
    except:
        return ""

# ------------------------------
# 加载知识库
# ------------------------------
@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return "\n---\n".join([fetch_page(url1), fetch_page(url2)])

# ------------------------------
# 联网搜索
# ------------------------------
@st.cache_data(ttl=60)
def web_search(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    return fetch_page(url)

# ------------------------------
# 调用 CF AI
# ------------------------------
def call_cf(prompt, account_id, api_token, model):
    if not account_id or not api_token:
        return "请先在侧边栏填写 API 信息"

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    try:
        data = json.dumps({"prompt": prompt}).encode()
        req = urllib.request.Request(url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=20) as f:
            return json.load(f)["result"]["response"].strip()
    except Exception as e:
        return f"调用失败：{str(e)}"

# ------------------------------
# 判断是否需要联网
# ------------------------------
def is_search_needed(question, kb, account_id, api_token, model):
    prompt = f"""只用中文回答。
知识库：{kb}
问题：{question}

能回答则输出：不需要
否则输出：需要
"""
    return call_cf(prompt, account_id, api_token, model).strip() == "需要"

# ------------------------------
# 构建多轮 prompt
# ------------------------------
def build_prompt(question, kb, history, web_data=None):
    hist_text = ""
    for m in history:
        prefix = "用户" if m["role"] == "user" else "助手"
        hist_text += f"{prefix}：{m['content']}\n"

    base = f"""你是中文助手，只使用中文，自然简洁回答。
知识库内容：
{kb}

对话历史：
{hist_text}

用户：{question}
"""
    if web_data:
        return f"""{base}
以下是联网搜索结果：
{web_data}
请根据搜索内容如实回答，不编造。
"""
    else:
        return base

# ===================== 界面：HTML 聊天框 =====================
st.markdown("""
<style>
.chat-box {
    background:#f7f8fa;
    border-radius:12px;
    padding:20px;
    height:500px;
    overflow-y:auto;
    margin-bottom:16px;
}
.msg-user {
    background:#007bff;
    color:white;
    padding:10px 14px;
    border-radius:8px;
    margin-left:auto;
    max-width:80%;
    margin-bottom:8px;
}
.msg-bot {
    background:#e9ecef;
    padding:10px 14px;
    border-radius:8px;
    max-width:80%;
    margin-bottom:8px;
}
</style>
<h2 style="text-align:center;">🤖 多轮对话 · 知识库 + 搜索</h2>
""", unsafe_allow_html=True)

# 渲染历史
chat_box = '<div class="chat-box">'
for m in st.session_state.messages:
    if m["role"] == "user":
        chat_box += f'<div class="msg-user">{m["content"]}</div>'
    else:
        chat_box += f'<div class="msg-bot">{m["content"]}</div>'
chat_box += "</div>"
st.markdown(chat_box, unsafe_allow_html=True)

# 输入
user_q = st.text_input("输入问题：", label_visibility="collapsed", placeholder="输入问题...")

if st.button("🚀 发送", use_container_width=True) and user_q:
    st.session_state.messages.append({"role": "user", "content": user_q})

    with st.spinner("处理中..."):
        kb_text = load_kb(KB_URL1, KB_URL2)
        need_web = is_search_needed(user_q, kb_text, CF_ACCOUNT_ID, CF_API_TOKEN, MODEL)

        if need_web:
            web_data = web_search(user_q)
            final_prompt = build_prompt(user_q, kb_text, st.session_state.messages, web_data)
            ans = call_cf(final_prompt, CF_ACCOUNT_ID, CF_API_TOKEN, MODEL) + "\n(来源：联网搜索)"
        else:
            final_prompt = build_prompt(user_q, kb_text, st.session_state.messages)
            ans = call_cf(final_prompt, CF_ACCOUNT_ID, CF_API_TOKEN, MODEL) + "\n(来源：知识库)"

    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.rerun()
