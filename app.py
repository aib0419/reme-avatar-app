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
import streamlit.components.v1 as components

components.html("""
<model-viewer src="https://raw.githubusercontent.com/aib0419/reme-avatar-app/main/avatar.glb"
              alt="3D Avatar"
              auto-rotate
              camera-controls
              style="width: 100%; height: 400px;">
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

    st.rerun()

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

    # ▼ 日時から曜日を取り出して棒グラフにする（既存）
    df["曜日"] = df["日時"].dt.day_name(locale='Japanese')
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df["曜日"] = pd.Categorical(df["曜日"], categories=order, ordered=True)
    weekly_avg = df.groupby("曜日", observed=True)["感情スコア"].mean().reset_index()
    chart = alt.Chart(weekly_avg).mark_bar().encode(
        x=alt.X("曜日:N", title="曜日"),
        y=alt.Y("感情スコア:Q", title="平均感情スコア"),
        tooltip=["感情スコア"]
    ).properties(width=700, height=300)
    st.altair_chart(chart)

    # ▼ 週ごとの平均
    st.markdown("### 📊 週ごとの感情スコア（平均）")
    df["週"] = df["日時"].dt.to_period("W").astype(str)
    weekly = df.groupby("週", observed=True)["感情スコア"].mean().reset_index()
    chart_week = alt.Chart(weekly).mark_bar().encode(
        x=alt.X("週:N", title="週"),
        y=alt.Y("感情スコア:Q", title="平均感情スコア"),
        tooltip=["週", "感情スコア"]
    ).properties(width=700, height=300)
    st.altair_chart(chart_week)

    # ▼ 月ごとの平均
    st.markdown("### 📊 月ごとの感情スコア（平均）")
    df["月"] = df["日時"].dt.to_period("M").astype(str)
    monthly = df.groupby("月", observed=True)["感情スコア"].mean().reset_index()
    chart_month = alt.Chart(monthly).mark_line(point=True).encode(
        x=alt.X("月:N", title="月"),
        y=alt.Y("感情スコア:Q", title="平均感情スコア"),
        tooltip=["月", "感情スコア"]
    ).properties(width=700, height=300)
    st.altair_chart(chart_month)

else:
    st.info("まだ感情スコアのデータがありません。まずはチャットしてください。")

