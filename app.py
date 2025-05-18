import streamlit as st
import openai
import pandas as pd
import csv
from datetime import datetime
import os
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("🧠 Re:Me – 自己内省AI with 3Dアバター & 感情記録")

# 🔒 OpenAIキー（Streamlit CloudならSecrets管理が推奨）
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else "YOUR_API_KEY"

# 🦊 3Dアバター表示（新モデル）
components.html("""
<model-viewer src="avatar.glb"
              alt="3D Avatar"
              auto-rotate
              camera-controls
              style="width:100%; height:400px;">
</model-viewer>
<script type="module"
  src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js">
</script>
""", height=420)

st.markdown("### 💬 AIとの内省チャット")

# セッション履歴管理
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "あなたは共感的な内省支援AIです。"}]
if "log" not in st.session_state:
    st.session_state.log = []

# 入力欄
user_input = st.text_input("今日感じたことや考えたことを話してみてください", key="chat_input")

if st.button("送信") and user_input:
    # ユーザー入力
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 応答取得
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages
    )
    ai_reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
    
    # 感情スコアを取得
    emo_prompt = f"以下の発言のポジティブ度を100点満点で評価してください。数値のみを出力：{user_input}"
    emo_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": emo_prompt}]
    )
    try:
        score = int(''.join(filter(str.isdigit, emo_response.choices[0].message.content)))
    except:
        score = -1
    
    # ログに記録
    timestamp = datetime.now().isoformat()
    st.session_state.log.append({"日時": timestamp, "入力": user_input, "AI応答": ai_reply, "感情スコア": score})
    
    # CSV保存（Cloudでは動作しない場合がある）
    try:
        with open("emotion_log.csv", "a", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["日時", "入力", "AI応答", "感情スコア"])
            if os.stat("emotion_log.csv").st_size == 0:
                writer.writeheader()
            writer.writerow(st.session_state.log[-1])
    except:
        pass

    st.experimental_rerun()

# チャット履歴表示
for msg in st.session_state.messages[1:]:
    speaker = "🧍‍♀️ あなた" if msg["role"] == "user" else "🤖 Re:Me"
    st.markdown(f"**{speaker}：** {msg['content']}")

# 📈 感情スコアのグラフ表示
st.markdown("### 📊 感情スコアの推移")

if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")
    st.line_chart(df.set_index("日時")["感情スコア"])
else:
    st.info("まだ感情スコアのデータがありません。まずはチャットしてください。")
