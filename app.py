import streamlit as st
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime

# ===================== 页面设置 =====================
st.set_page_config(
    page_title="Kzz AI 2",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===================== 模型列表 =====================
MODEL_LIST = [
    "@cf/moonshotai/kimi-k2.5",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/openai/gpt-oss-20b",
    "@cf/openai/gpt-oss-120b",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/google/gemma-3-12b-it",
    "@cf/qwen/qwq-32b",
    "@cf/qwen/qwen2.5-coder-32b-instruct",
    "@cf/meta/llama-guard-3-8b",
    "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-3.2-1b-instruct",
    "@cf/meta/llama-3.2-3b-instruct",
    "@cf/meta/llama-3.2-11b-vision-instruct",
    "@cf/meta/llama-3.1-8b-instruct-awq",
    "@cf/meta/llama-3.1-8b-instruct-fp8",
    "@cf/meta/llama-3-8b-instruct-awq",
    "@cf/meta/llama-3-8b-instruct",
    "@cf/google/gemma-7b-it-lora",
    "@cf/google/gemma-2b-it-lora",
    "@cf/meta-llama/llama-2-7b-chat-hf-lora",
    "@hf/google/gemma-7b-it",
    "@cf/microsoft/phi-2",
    "@cf/meta/llama-2-7b-chat-fp16",
    "@cf/meta/llama-2-7b-chat-int8",
    "自定义模型"
]

# ===================== 账号优先级（你原版 100% 不动）=====================
def get_final_credits():
    var_id = st.secrets.get("CF_ACCOUNT_ID", "")
    var_token = st.secrets.get("CF_API_TOKEN", "")
    user_id = st.session_state.get("input_id", "")
    user_token = st.session_state.get("input_token", "")
    final_id = user_id.strip() if user_id.strip() else var_id.strip()
    final_token = user_token.strip() if user_token.strip() else var_token.strip()
    return final_id, final_token

# ===================== 【仅新增：CF 浏览器独立获取】=====================
def get_browser_credits():
    # 浏览器也走同样逻辑：用户输入优先 → 否则 secrets
    browser_id = st.secrets.get("CF_BROWSER_ACCOUNT_ID", "")
    browser_token = st.secrets.get("CF_BROWSER_API_TOKEN", "")
    return browser_id, browser_token

# ===================== 【仅新增：Cloudflare 官方无头浏览器】=====================
def cf_browser_fetch(url, account_id, api_token):
    if not account_id or not api_token:
        return ""
    try:
        api = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "url": url,
            "waitFor": 1000,
            "output": "markdown"
        }).encode()
        req = urllib.request.Request(api, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)
            return res.get("result", {}).get("markdown", "")
    except:
        return ""

# ===================== 状态初始化 =====================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""
if "json_logs" not in st.session_state:
    st.session_state.json_logs = {}

# ===================== 工具函数 =====================
def clean_html(html):
    html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-z0-9#]+;", " ", html, flags=re.I)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:8000]

def fetch(url):
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as f:
            return clean_html(f.read().decode("utf-8", "ignore"))
    except:
        return ""

@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return "\n".join([fetch(url1), fetch(url2)])

@st.cache_data(ttl=60)
def search(query):
    return fetch(f"https://www.bing.com/search?q={urllib.parse.quote(query)}")

# ===================== 提取回答 + 过滤问号 =====================
def extract_answer(res):
    try:
        result = res.get("result", res)
        if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
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
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0.7
        }).encode()

        req = urllib.request.Request(url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)

        return extract_answer(res), res

    except Exception as e:
        return f"❌ 调用失败：{str(e)}", {}

# ===================== 【核心修复】MDUI 布局 + 消除空白 =====================
st.markdown("""
<link rel="stylesheet" href="https://cdn.mdui.org/css/mdui.min.css">
<script src="https://cdn.mdui.org/js/mdui.min.js"></script>

<div class="mdui-appbar mdui-color-blue-600">
  <div class="mdui-toolbar mdui-container">
    <span class="mdui-typo-headline">🤖 AI 对话助手</span>
  </div>
</div>

<style>
.stApp { background: #121212 !important; }
.main { 
    max-width: 900px; 
    margin: 20px auto 0 auto;
    padding: 0 20px;
}
.model-bar { 
    display: flex; 
    gap: 16px; 
    align-items: center; 
    margin-bottom: 16px;
}
.chat-box {
    background: #1e1e1e;
    border-radius: 16px;
    padding: 20px;
    max-height: 60vh;
    overflow-y: auto;
    margin-bottom: 16px;
    border: 1px solid #333;
}
.user-msg {
    background: #2196F3;
    color: white;
    padding: 12px 16px;
    border-radius: 16px 16px 4px 16px;
    margin: 8px 0;
    margin-left: auto;
    max-width: 75%;
}
.bot-msg {
    background: #2d2d2d;
    color: #fff;
    padding: 12px 16px;
    border-radius: 16px 16px 16px 4px;
    margin: 8px 0;
    max-width: 75%;
    white-space: pre-wrap;
}
.stTextInput > div > input {
    border-radius: 12px;
    background: #1e1e1e;
    border: 1px solid #333;
    color: #fff;
}
.stButton > button {
    border-radius: 12px;
    background: #2196F3;
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ===================== 侧边栏 =====================
with st.sidebar:
    st.title("Kzz AI 2")
    st.markdown('<div class="mdui-card" style="background:#1e1e1e;border:1px solid #333;">', unsafe_allow_html=True)
    st.title("⚙️ 设置")
    st.text_input("Account ID", key="input_id", type="password")
    st.text_input("API Token", key="input_token", type="password")
    st.divider()
    st.title("📚 知识库")
    kb1 = st.text_input("链接 1", value="")
    kb2 = st.text_input("链接 2", value="")
    st.divider()
    st.title("📎 上传文件")
    uploaded = st.file_uploader("TXT/MD", type=["txt", "md"])
    if uploaded:
        st.session_state.file_content = uploaded.read().decode("utf-8", errors="ignore")
        st.success("✅ 已加载")
    st.markdown('</div>', unsafe_allow_html=True)

# ===================== 主界面 =====================
st.markdown('<div class="main">', unsafe_allow_html=True)

col1, col2, col3 = st.columns([3,1,1], gap="small")
with col1:
    model_sel = st.selectbox("模型", MODEL_LIST, label_visibility="collapsed")
with col2:
    if st.button("🧹 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.json_logs = {}
        st.rerun()
with col3:
    if st.session_state.messages:
        txt = "\n\n".join([f"{'用户' if m['role']=='user' else '助手'}：{m['content']}" for m in st.session_state.messages])
        st.download_button("💾 导出对话", txt, f"对话_{datetime.now().strftime('%Y%m%d%H%M')}.txt", use_container_width=True)

custom_model = st.text_input("自定义模型", label_visibility="collapsed", placeholder="输入自定义模型名") if model_sel == "自定义模型" else ""

st.markdown('<div class="chat-box">', unsafe_allow_html=True)
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        if str(i) in st.session_state.json_logs:
            with st.expander("📄 查看完整JSON", expanded=False):
                st.code(st.session_state.json_logs[str(i)], language="json")
st.markdown('</div>', unsafe_allow_html=True)

prompt = st.text_input("输入问题", label_visibility="collapsed", placeholder="输入消息...", key="user_prompt")

st.markdown("""
<script>
const ipt = document.querySelector('input[aria-label="输入问题"]');
ipt?.addEventListener('keydown', e => { if(e.key === 'Enter') document.querySelector('button[kind="primary"]')?.click(); });
</script>
""", unsafe_allow_html=True)

# ===================== 发送逻辑（你原版 100% 不动 + 仅加浏览器）=====================
if st.button("🚀 发送", use_container_width=True) and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    used_model = custom_model if model_sel == "自定义模型" else model_sel
    account, token = get_final_credits()
    browser_account, browser_token = get_browser_credits()

    with st.spinner("处理中..."):
        kb_content = load_kb(kb1, kb2)
        file_content = st.session_state.file_content
        context = f"【知识库】\n{kb_content}\n\n【上传文件】\n{file_content}"

        check_prompt = f"""你是中文助手，只根据知识库回答。
能回答就输出：有答案
不能回答就输出：无答案
不要输出任何其他内容，不要加问号。

知识库：{context}
问题：{prompt}"""
        check_ans, _ = cf_ai(check_prompt, account, token, used_model)
        
        if "无答案" in check_ans:
            # 👇 这里：优先用 CF 官方无头浏览器，没有就降级普通搜索
            web = cf_browser_fetch(f"https://www.bing.com/search?q={urllib.parse.quote(prompt)}", browser_account, browser_token)
            if not web:
                web = search(prompt)
            
            final_prompt = f"""你是中文助手，只根据搜索结果如实回答，不要加任何前缀、问号。
知识库：{context}
搜索结果：{web}
问题：{prompt}"""
            ans, raw_json = cf_ai(final_prompt, account, token, used_model)
            ans += "\n(来源：Cloudflare 浏览器)"
        else:
            final_prompt = f"""你是中文助手，只根据知识库完整回答，不要加任何前缀、问号。
知识库：{context}
问题：{prompt}"""
            ans, raw_json = cf_ai(final_prompt, account, token, used_model)
            ans += "\n(来源：知识库)"

    idx = len(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.session_state.json_logs[str(idx)] = json.dumps(raw_json, ensure_ascii=False, indent=2)
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
