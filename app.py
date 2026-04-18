import streamlit as st
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime
import requests

# ===================== 无头浏览器工具 =====================
def browser_get_content(url: str) -> str:
    try:
        resp = requests.post(
            "https://browser.xingoxu.com/api",
            json={"action": "content", "url": url},
            timeout=20
        )
        return resp.json().get("text", "获取内容失败")
    except:
        return "获取网页失败"

def browser_get_screenshot(url: str) -> str:
    try:
        resp = requests.post(
            "https://browser.xingoxu.com/api",
            json={"action": "screenshot", "url": url},
            timeout=20
        )
        return resp.json().get("image", "截图失败")
    except:
        return "截图失败"

# ===================== 页面设置 =====================
st.set_page_config(
    page_title="Kzz AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===================== 模型列表 =====================
MODEL_LIST = [
    "@cf/moonshotai/kimi-k2.5",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/google/gemma-3-12b-it",
    "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "自定义模型"
]

# ===================== 账号优先级 =====================
def get_final_credits():
    var_id = st.secrets.get("CF_ACCOUNT_ID", "")
    var_token = st.secrets.get("CF_API_TOKEN", "")
    user_id = st.session_state.get("input_id", "")
    user_token = st.session_state.get("input_token", "")
    final_id = user_id.strip() if user_id.strip() else var_id.strip()
    final_token = user_token.strip() if user_token.strip() else var_token.strip()
    return final_id, final_token

# ===================== 状态初始化 =====================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""
if "agent_thoughts" not in st.session_state:
    st.session_state.agent_thoughts = []

# ===================== 工具函数 =====================
def clean_html(html):
    html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-z0-9#]+;", " ", html, flags=re.I)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:8000]

def fetch(url):
    if not url: return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as f:
            return clean_html(f.read().decode("utf-8", "ignore"))
    except:
        return ""

@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return "\n".join([fetch(url1), fetch(url2)])

# ===================== 提取回答 =====================
def extract_answer(res):
    try:
        result = res.get("result", res)
        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0].get("text", "").strip()
        elif "response" in result:
            text = str(result["response"]).strip()
        else:
            text = str(result).strip()
        text = re.sub(r"^[？?\n\s]+", "", text)
        return text
    except:
        return str(res).strip()

# ===================== AI 调用 =====================
def cf_ai(prompt, account_id, api_token, model):
    if not account_id or not api_token:
        return "🔒 请填写 CF Account ID 和 API Token", {}
    model = model.strip()
    if not model.startswith(("@cf/", "@hf/")):
        model = f"@cf/{model}"
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        data = json.dumps({"prompt": prompt, "max_tokens": 1200, "temperature": 0.6}).encode()
        req = urllib.request.Request(url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)
        return extract_answer(res), res
    except Exception as e:
        return f"❌ 调用失败：{str(e)}", {}

# ===================== 【AGENT 核心】AI 自主思考 + 调用工具 =====================
def agent_run(user_input, account, token, model, kb_content, file_content):
    thoughts = []
    thoughts.append("🧠 开始分析用户问题...")
    st.session_state.agent_thoughts = thoughts

    # 1. 判断是否需要联网
    thoughts.append("🔍 判断：是否需要打开网页？")
    st.session_state.agent_thoughts = thoughts
    judge_prompt = f"""
请判断问题是否需要【联网/打开网页】。
需要 → 输出：需要
不需要 → 输出：不需要

问题：{user_input}
"""
    judge_ans, _ = cf_ai(judge_prompt, account, token, model)
    thoughts.append(f"✅ 判断结果：{judge_ans}")
    st.session_state.agent_thoughts = thoughts

    # 2. 需要 → 自动调用浏览器
    if "需要" in judge_ans:
        thoughts.append("🌍 准备提取目标网址...")
        st.session_state.agent_thoughts = thoughts

        url_prompt = f"从问题中提取网址，没有就生成必应搜索链接。只输出链接：{user_input}"
        url, _ = cf_ai(url_prompt, account, token, model)
        if not url.startswith("http"):
            url = f"https://www.bing.com/search?q={urllib.parse.quote(user_input)}"

        thoughts.append(f"🔗 目标网址：{url}")
        st.session_state.agent_thoughts = thoughts

        thoughts.append("🚀 调用无头浏览器读取内容...")
        st.session_state.agent_thoughts = thoughts
        web_content = browser_get_content(url)

        thoughts.append("📷 调用无头浏览器截图...")
        st.session_state.agent_thoughts = thoughts
        screenshot = browser_get_screenshot(url)

        thoughts.append("📝 总结网页内容...")
        st.session_state.agent_thoughts = thoughts

        final_prompt = f"""
根据网页内容回答问题，简洁准确。
网页内容：{web_content}
问题：{user_input}
"""
        ans, raw_json = cf_ai(final_prompt, account, token, model)
        ans += f"\n\n🖼️ 截图：{screenshot}\n🔗 来源：{url}"
        thoughts.append("✅ 完成！")
        st.session_state.agent_thoughts = thoughts
        return ans, raw_json

    # 3. 不需要 → 本地回答
    else:
        thoughts.append("💡 使用本地知识回答...")
        st.session_state.agent_thoughts = thoughts
        context = f"知识库：{kb_content}\n文件：{file_content}"
        final_prompt = f"{context}\n问题：{user_input}"
        ans, raw_json = cf_ai(final_prompt, account, token, model)
        thoughts.append("✅ 完成！")
        st.session_state.agent_thoughts = thoughts
        return ans, raw_json

# ===================== 界面 =====================
st.markdown("""
<link rel="stylesheet" href="https://cdn.mdui.org/css/mdui.min.css">
<div class="mdui-appbar mdui-color-blue-600">
  <div class="mdui-toolbar mdui-container">
    <span class="mdui-typo-headline">🤖 Kzz AI Agent（自主调用浏览器）</span>
  </div>
</div>
<style>
.stApp { background: #121212 !important; }
.main { max-width: 900px; margin: 20px auto; padding:0 20px; }
.chat-box { background:#1e1e1e; border-radius:16px; padding:20px; max-height:55vh; overflow-y:auto; margin-bottom:16px; }
.thought-box { background:#181818; border-radius:12px; padding:12px; margin-bottom:12px; border:1px solid #333; color:#aaa; }
.user-msg { background:#2196F3; color:white; padding:12px 16px; border-radius:16px 16px 4px 16px; margin:8px 0; margin-left:auto; max-width:75%; }
.bot-msg { background:#2d2d2d; color:#fff; padding:12px 16px; border-radius:16px 16px 16px 4px; margin:8px 0; max-width:75%; white-space:pre-wrap; }
</style>
""", unsafe_allow_html=True)

# ===================== 侧边栏 =====================
with st.sidebar:
    st.title("⚙️ 设置")
    st.text_input("Account ID", key="input_id", type="password")
    st.text_input("API Token", key="input_token", type="password")
    st.title("📚 知识库")
    kb1 = st.text_input("链接1")
    kb2 = st.text_input("链接2")

# ===================== 主界面 =====================
st.markdown('<div class="main">', unsafe_allow_html=True)

col1, col2 = st.columns([4, 2])
with col1:
    model_sel = st.selectbox("模型", MODEL_LIST, label_visibility="collapsed")
with col2:
    if st.button("🧹 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_thoughts = []
        st.rerun()

custom_model = st.text_input("自定义模型", placeholder="模型名", label_visibility="collapsed") if model_sel == "自定义模型" else model_sel

# --- 【Agent 思考面板】---
if st.session_state.agent_thoughts:
    with st.container():
        st.markdown('<div class="thought-box">', unsafe_allow_html=True)
        st.caption("🤖 Agent 思考过程：")
        for t in st.session_state.agent_thoughts:
            st.write(t)
        st.markdown('</div>', unsafe_allow_html=True)

# 聊天区域
st.markdown('<div class="chat-box">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg">{msg["content"]}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

prompt = st.text_input("消息", placeholder="输入问题，AI 会自主决策是否打开网页...", label_visibility="collapsed")

# ===================== 发送 =====================
if st.button("🚀 发送", use_container_width=True) and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    account, token = get_final_credits()
    used_model = custom_model

    with st.spinner(""):
        kb_content = load_kb(kb1, kb2)
        file_content = st.session_state.file_content
        ans, raw_json = agent_run(prompt, account, token, used_model, kb_content, file_content)

    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
