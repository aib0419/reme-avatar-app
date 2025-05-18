import streamlit as st
st.set_page_config(layout="wide")

import openai
import pandas as pd
import plotly.graph_objects as go
import altair as alt
import streamlit.components.v1 as components
from datetime import datetime
import os
import csv
import json, re

st.title("🧠 Re:Me – 自己内省AI")

# OpenAIキー
openai.api_key = st.secrets["OPENAI_API_KEY"]

# 🦊 3Dアバター表示
components.html("""
<model-viewer src="https://raw.githubusercontent.com/aib0419/reme-avatar-app/main/avatar.glb"
              alt="3D Avatar"
              auto-rotate camera-controls
              style="width: 100%; height: 400px;">
</model-viewer>
<script type="module"
  src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js">
</script>
""", height=420)

# 初期化
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "あなたは共感的な内省支援AIです。"}]
if "log" not in st.session_state:
    st.session_state.log = []
if "ability_self" not in st.session_state:
    st.session_state.ability_self = None
if "ability_ai" not in st.session_state:
    st.session_state.ability_ai = None

# ユーザー入力
st.markdown("### 💬 今日考えたこと・感じたことを話してみてください")
user_input = st.text_input("入力してください", key="chat_input")

if st.button("送信") and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages
    )
    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})

    # 感情スコア
    emo_prompt = f"この文章のポジティブ度を100点満点で数値のみで答えてください：{user_input}"
    emo_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": emo_prompt}]
    )
    try:
        score = int(''.join(filter(str.isdigit, emo_response.choices[0].message.content)))
    except:
        score = -1

    now = datetime.now().isoformat()
    st.session_state.log.append({"日時": now, "入力": user_input, "AI応答": reply, "感情スコア": score})
    st.rerun()

# チャット履歴
for msg in st.session_state.messages[1:]:
    role = "🧍‍♀️ あなた" if msg["role"] == "user" else "🤖 Re:Me"
    st.markdown(f"**{role}：** {msg['content']}")

# 📊 感情スコア可視化
st.markdown("### 📊 感情スコアの推移")

if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")
    st.line_chart(df.set_index("日時")["感情スコア"])

    df["曜日英語"] = df["日時"].dt.day_name()
    day_map = {
        "Monday": "月", "Tuesday": "火", "Wednesday": "水",
        "Thursday": "木", "Friday": "金", "Saturday": "土", "Sunday": "日"
    }
    df["曜日"] = df["曜日英語"].map(day_map)
    order = ["月", "火", "水", "木", "金", "土", "日"]
    df["曜日"] = pd.Categorical(df["曜日"], categories=order, ordered=True)

    st.markdown("#### 🔹 曜日別 平均")
    weekly_avg = df.groupby("曜日", observed=True)["感情スコア"].mean().reset_index()
    st.altair_chart(alt.Chart(weekly_avg).mark_bar().encode(
        x="曜日:N", y="感情スコア:Q", tooltip=["曜日", "感情スコア"]
    ).properties(width=700, height=300))

    st.markdown("#### 🔹 週ごと平均")
    df["週"] = df["日時"].dt.to_period("W").astype(str)
    weekly = df.groupby("週", observed=True)["感情スコア"].mean().reset_index()
    st.altair_chart(alt.Chart(weekly).mark_bar().encode(
        x="週:N", y="感情スコア:Q", tooltip=["週", "感情スコア"]
    ).properties(width=700, height=300))

    st.markdown("#### 🔹 月ごと平均")
    df["月"] = df["日時"].dt.to_period("M").astype(str)
    monthly = df.groupby("月", observed=True)["感情スコア"].mean().reset_index()
    st.altair_chart(alt.Chart(monthly).mark_line(point=True).encode(
        x="月:N", y="感情スコア:Q", tooltip=["月", "感情スコア"]
    ).properties(width=700, height=300))
else:
    st.info("まだ感情スコアのデータがありません。まずはチャットしてください。")

# 🕸️ 混合型レーダーチャート
st.markdown("### 🕸️ 能力レーダーチャート")

categories = ["共感力", "論理力", "創造性", "行動力", "継続力", "自己認識"]

if st.button("自己評価する"):
    st.session_state.ability_self = [st.slider(cat, 0, 100, 50) for cat in categories]

if st.session_state.log:
    text_summary = "\n".join([log["入力"] for log in st.session_state.log[-5:]])
    prompt = f"""
以下のテキストから、次の6つの能力を100点満点で評価してください。
- 共感力・論理力・創造性・行動力・継続力・自己認識

JSON形式で：
{{"共感力":70,"論理力":60,...}}

テキスト：
{text_summary}
"""
    try:
        res = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        json_text = re.search(r"\{[\s\S]*\}", res.choices[0].message.content).group()
        ai_scores = json.loads(json_text)
        st.session_state.ability_ai = [ai_scores[c] for c in categories]
    except:
        st.warning("AIによる能力評価の解析に失敗しました。")

# レーダーチャート描画
if st.session_state.ability_self or st.session_state.ability_ai:
    fig = go.Figure()
    if st.session_state.ability_self:
        fig.add_trace(go.Scatterpolar(
            r=st.session_state.ability_self + [st.session_state.ability_self[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name="自己評価"
        ))
    if st.session_state.ability_ai:
        fig.add_trace(go.Scatterpolar(
            r=st.session_state.ability_ai + [st.session_state.ability_ai[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name="AI評価"
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True
    )
    st.plotly_chart(fig)
else:
    st.info("レーダーチャートを表示するには自己評価かチャットが必要です。")



