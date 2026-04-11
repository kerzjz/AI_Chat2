import streamlit as st
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime

# ===================== 页面设置 =====================
st.set_page_config(
    page_title="AI 助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===================== 模型列表 =====================
MODEL_LIST = [
    "@cf/moonshotai/kimi-k2.5",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/meta/llama-3-8b-instruct",
    "@cf/google/gemma-2-9b-it",
    "@cf/qwen/qwen3-30b-a3b-fp8",
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

# ===================== 【终极修复】回答提取 =====================
def extract_answer(res):
    try:
        result = res.get("result", res)
        if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
            return result["choices"][0].get("text", "").strip()
        if "response" in result:
            return str(result["response"]).strip()
        return str(result).strip()
    except:
        return str(res).strip()

# ===================== 【核心修复】请求格式（加了 max_tokens ！！！） =====================
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

        # ✅ ✅ ✅ 就是这里！！！加了 max_tokens=1024 永不截断！！
        data = json.dumps({
            "prompt": prompt,
            "max_tokens": 1024,  # 标准值，不浪费token，不截断！
            "temperature": 0.7
        }).encode()

        req = urllib.request.Request(url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            res = json.load(f)

        return extract_answer(res), res

    except Exception as e:
        return f"❌ 调用失败：{str(e)}", {}

# ===================== MDUI 界面 =====================
st.markdown("""
<link rel="stylesheet" href="https://cdn.mdui.org/css/mdui.min.css">
<script src="https://cdn.mdui.org/js/mdui.min.js"></script>
<div class="mdui-appbar mdui-color-blue-600">
  <div class="mdui-toolbar mdui-container">
    <span class="mdui-typo-headline">🤖 AI 对话助手</span>
  </div>
</div>
<br>
<style>
.main { max-width: 820px; margin: 0 auto; padding: 20px; }
.mdui-card { padding: 24px; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); background: #fff; }
#chat-box { height: 550px; overflow-y: auto; }
.user-msg { background: #2196F3; color: white; padding: 12px 16px; border-radius: 16px 16px 4px 16px; margin: 8px 0; margin-left: auto; max-width: 75%; }
.bot-msg { background: #f1f3f4; padding: 12px 16px; border-radius: 16px 16px 16px 4px; margin: 8px 0; max-width: 75%; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

# ===================== 侧边栏 =====================
with st.sidebar:
    st.markdown('<div class="mdui-card">', unsafe_allow_html=True)
    st.title("⚙️ 设置")
    st.text_input("Account ID", key="input_id", type="password")
    st.text_input("API Token", key="input_token", type="password")
    st.divider()
    st.title("📚 知识库")
    kb1 = st.text_input("链接 1", value="https://jxsy.bearblog.dev/")
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

col1, col2, col3 = st.columns([3,1,1])
with col1:
    model_sel = st.selectbox("模型", MODEL_LIST)
with col2:
    if st.button("🧹 清空对话"):
        st.session_state.messages = []
        st.session_state.json_logs = {}
        st.rerun()
with col3:
    if st.session_state.messages:
        txt = "\n\n".join([f"{'用户' if m['role']=='user' else '助手'}：{m['content']}" for m in st.session_state.messages])
        st.download_button("💾 导出对话", txt, f"对话_{datetime.now().strftime('%Y%m%d%H%M')}.txt")

custom_model = st.text_input("自定义模型") if model_sel == "自定义模型" else ""

# 聊天区域
st.markdown('<div class="mdui-card" id="chat-box">', unsafe_allow_html=True)
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        if str(i) in st.session_state.json_logs:
            with st.expander("📄 查看完整JSON", expanded=False):
                st.code(st.session_state.json_logs[str(i)], language="json")
st.markdown('</div>', unsafe_allow_html=True)

# 输入框
prompt = st.text_input("输入问题", label_visibility="collapsed", placeholder="输入消息...", key="user_prompt")

# 回车发送
st.markdown("""
<script>
const ipt = document.querySelector('input[aria-label="输入问题"]');
ipt?.addEventListener('keydown', e => { if(e.key === 'Enter') document.querySelector('button[kind="primary"]')?.click(); });
</script>
""", unsafe_allow_html=True)

# 发送逻辑
if st.button("🚀 发送", use_container_width=True) and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    used_model = custom_model if model_sel == "自定义模型" else model_sel
    account, token = get_final_credits()

    with st.spinner("处理中..."):
        kb_content = load_kb(kb1, kb2)
        file_content = st.session_state.file_content
        context = f"【知识库】\n{kb_content}\n\n【上传文件】\n{file_content}"

        check_ans, _ = cf_ai(f"只用中文。能回答输出有答案，否则无答案。\n{context}\n问题：{prompt}", account, token, used_model)
        
        if "无答案" in check_ans:
            web = search(prompt)
            ans, raw_json = cf_ai(f"只用中文如实完整回答。\n{context}\n搜索：{web}\n问题：{prompt}", account, token, used_model)
            ans += "\n(来源：联网搜索)"
        else:
            ans, raw_json = cf_ai(f"只用中文完整回答。\n{context}\n问题：{prompt}", account, token, used_model)
            ans += "\n(来源：知识库)"

    idx = len(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.session_state.json_logs[str(idx)] = json.dumps(raw_json, ensure_ascii=False, indent=2)
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
