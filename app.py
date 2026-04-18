import streamlit as st
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime

# ===================== 页面设置 =====================
st.set_page_config(
    page_title="Kzz AI Agent + CF Browser",
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

@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return ""

# ===================== 【官方】Cloudflare 无头浏览器 =====================
# 这是 Cloudflare 官方 Browser Rendering API（真实无头浏览器）
def cf_browser_fetch(url, account_id, api_token):
    try:
        url_api = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "url": url,
            "waitFor": 1000,
            "output": "markdown"
        }).encode()

        req = urllib.request.Request(url_api, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)
            return res.get("result", {}).get("markdown", "获取失败")
    except Exception as e:
        return f"CF浏览器调用失败：{str(e)}"

def cf_browser_screenshot(url, account_id, api_token):
    try:
        url_api = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "url": url,
            "waitFor": 1000,
            "screenshot": True
        }).encode()

        req = urllib.request.Request(url_api, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)
            img_b64 = res.get("result", {}).get("screenshot", "")
            if img_b64:
                return f"data:image/png;base64,{img_b64}"
        return "截图失败"
    except:
        return "截图失败"

# ===================== AI 调用 =====================
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

# ===================== 【AGENT 核心】自主调用 CF 无头浏览器 =====================
def agent_run(user_input, account, token, model):
    thoughts = []
    thoughts.append("🧠 Agent 分析问题...")
    st.session_state.agent_thoughts = thoughts

    # 判断是否需要浏览器
    judge_prompt = f"""
判断问题是否需要【打开网页/联网】。
需要 → 输出：需要
不需要 → 输出：不需要

问题：{user_input}
"""
    judge_ans, _ = cf_ai(judge_prompt, account, token, model)
    thoughts.append(f"✅ 判断结果：{judge_ans}")
    st.session_state.agent_thoughts = thoughts

    if "需要" in judge_ans:
        thoughts.append("🔗 提取目标网址...")
        st.session_state.agent_thoughts = thoughts

        url_prompt = f"提取问题中的网址，没有就生成必应搜索链接。只输出链接：{user_input}"
        url, _ = cf_ai(url_prompt, account, token, model)
        if not url.startswith("http"):
            url = f"https://www.bing.com/search?q={urllib.parse.quote(user_input)}"

        thoughts.append(f"🌍 访问：{url}")
        st.session_state.agent_thoughts = thoughts

        # 调用 Cloudflare 官方无头浏览器
        thoughts.append("🚀 调用 CF 无头浏览器读取内容...")
        st.session_state.agent_thoughts = thoughts
        content = cf_browser_fetch(url, account, token)

        thoughts.append("📷 调用 CF 无头浏览器截图...")
        st.session_state.agent_thoughts = thoughts
        img = cf_browser_screenshot(url, account, token)

        # 总结
        thoughts.append("📝 生成回答...")
        st.session_state.agent_thoughts = thoughts
        final_prompt = f"网页内容：{content}\n问题：{user_input}\n简洁回答："
        ans, raw_json = cf_ai(final_prompt, account, token, model)
        ans += f"\n\n🖼️ 截图：{img}\n🔗 来源：{url}"
        return ans, raw_json

    else:
        thoughts.append("💡 直接回答...")
        st.session_state.agent_thoughts = thoughts
        ans, raw_json = cf_ai(user_input, account, token, model)
        return ans, raw_json

# ===================== 界面 =====================
st.markdown("""
<link rel="stylesheet" href="https://cdn.mdui.org/css/mdui.min.css">
<div class="mdui-appbar mdui-color-blue-600">
  <div class="mdui-toolbar mdui-container">
    <span class="mdui-typo-headline">🤖 Kzz AI Agent（CF官方无头浏览器）</span>
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

# 思考面板
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

prompt = st.text_input("消息", placeholder="输入问题，AI 自动调用 Cloudflare 无头浏览器...", label_visibility="collapsed")

# ===================== 发送 =====================
if st.button("🚀 发送", use_container_width=True) and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    account, token = get_final_credits()
    used_model = custom_model

    with st.spinner(""):
        ans, raw_json = agent_run(prompt, account, token, used_model)

    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
