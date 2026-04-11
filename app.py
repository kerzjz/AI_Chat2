import streamlit as st
import urllib.request
import urllib.parse
import json
import re
import datetime

# ===================== 页面设置 =====================
st.set_page_config(
    page_title="AI 对话助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认隐藏侧边栏
)

# ===================== 模型列表（剔除向量，全部保留） =====================
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

# ===================== 优先级逻辑（你要的三情况） =====================
def get_effective_account_token():
    # 1. 从 secrets 读取变量
    var_account = st.secrets.get("CF_ACCOUNT_ID", "")
    var_token = st.secrets.get("CF_API_TOKEN", "")

    # 2. 用户在界面填写的
    user_account = st.session_state.get("input_account", "")
    user_token = st.session_state.get("input_token", "")

    # 3. 优先级：用户填写 > 变量
    final_account = user_account.strip() if user_account.strip() else var_account.strip()
    final_token = user_token.strip() if user_token.strip() else var_token.strip()

    return final_account, final_token

# ===================== 状态初始化 =====================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""

# ===================== 工具函数 =====================
def clean_html(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-zA-Z0-9#]+;", " ", html, flags=re.I)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:8000]

def fetch_url(url):
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as f:
            return clean_html(f.read().decode("utf-8", "ignore"))
    except:
        return ""

@st.cache_data(ttl=3600)
def load_kb(url1, url2):
    return "\n---\n".join([fetch_url(url1), fetch_url(url2)])

@st.cache_data(ttl=60)
def bing_search(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    return fetch_url(url)

def cf_ai(prompt, account_id, api_token, model):
    if not account_id or not api_token:
        return "🔒 请先配置 Account ID 和 API Token"

    model = model.strip()
    if not model.startswith(("@cf/", "@hf/")):
        model = f"@cf/{model}"

    try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        data = json.dumps({"prompt": prompt}).encode()
        req = urllib.request.Request(api_url, headers=headers, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as f:
            return json.load(f)["result"]["response"].strip()
    except Exception as e:
        return f"❌ 调用失败：{str(e)}"

# ===================== MDUI 样式 =====================
st.markdown("""
<style>
* { font-family: 'Roboto', 'Segoe UI', sans-serif; }
.chat-wrapper { max-width: 820px; margin: 0 auto; padding: 20px; }
.chat-box {
    background: #fff; border-radius: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    padding: 24px; height: 540px; overflow-y: auto; margin-bottom: 16px;
}
.msg-user {
    background: #1976D2; color: #fff;
    padding: 12px 16px; border-radius: 18px 18px 4px 18px;
    max-width: 75%; margin-left: auto; margin-bottom: 12px;
}
.msg-bot {
    background: #f1f3f4; color: #202124;
    padding: 12px 16px; border-radius: 18px 18px 18px 4px;
    max-width: 75%; margin-bottom: 12px; white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# ===================== 侧边栏配置 =====================
with st.sidebar:
    st.title("⚙️ 设置")
    st.text_input("Account ID", key="input_account", type="password")
    st.text_input("API Token", key="input_token", type="password")

    st.divider()
    st.title("📚 知识库")
    kb1 = st.text_input("知识库地址 1", value="https://jxsy.bearblog.dev/")
    kb2 = st.text_input("知识库地址 2", value="")

    st.divider()
    st.title("📎 上传文件")
    file = st.file_uploader("上传 txt/md", type=["txt", "md", "json"])
    if file:
        st.session_state.file_content = file.read().decode("utf-8", errors="ignore")
        st.success("✅ 已加载")

# ===================== 主界面 =====================
st.markdown("<h2 style='text-align:center; margin-bottom:24px'>🤖 AI 对话助手</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([3,1,1])
with col1:
    model_sel = st.selectbox("选择模型", MODEL_LIST)
with col2:
    if st.button("🧹 清空对话"):
        st.session_state.messages = []
        st.rerun()
with col3:
    if st.session_state.messages:
        chat_text = "\n\n".join([
            f"{'用户' if m['role']=='user' else '助手'}：{m['content']}"
            for m in st.session_state.messages
        ])
        st.download_button(
            "💾 导出对话",
            chat_text,
            f"对话_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.txt",
            use_container_width=True
        )

custom_model = ""
if model_sel == "自定义模型":
    custom_model = st.text_input("输入模型名称")

# 渲染聊天
with st.container():
    st.markdown('<div class="chat-wrapper"><div class="chat-box">', unsafe_allow_html=True)
    for m in st.session_state.messages:
        if m["role"] == "user":
            st.markdown(f'<div class="msg-user">{m["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="msg-bot">{m["content"]}</div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

# 输入
question = st.text_input("输入问题", placeholder="发送消息...", label_visibility="collapsed")

if st.button("🚀 发送", use_container_width=True) and question:
    st.session_state.messages.append({"role": "user", "content": question})
    used_model = custom_model if model_sel == "自定义模型" else model_sel
    account, token = get_effective_account_token()

    with st.spinner("思考中..."):
        kb_text = load_kb(kb1, kb2)
        file_text = st.session_state.file_content
        context = f"【知识库】\n{kb_text}\n\n【上传文件】\n{file_text}"

        # 判断是否需要联网
        check_prompt = f"""只用中文回答。
上下文：
{context}

问题：{question}

如果能回答，只输出：有答案
否则只输出：无答案
"""
        check_result = cf_ai(check_prompt, account, token, used_model)

        if "无答案" in check_result:
            web = bing_search(question)
            final_prompt = f"""你是中文助手，简洁如实回答，不编造。
上下文：
{context}

搜索结果：
{web}

问题：{question}
"""
            ans = cf_ai(final_prompt, account, token, used_model) + "\n(来源：联网搜索)"
        else:
            final_prompt = f"""你是中文助手，简洁回答。
上下文：
{context}

问题：{question}
"""
            ans = cf_ai(final_prompt, account, token, used_model) + "\n(来源：知识库/文件)"

    st.session_state.messages.append({"role": "assistant", "content": ans})
    st.rerun()
