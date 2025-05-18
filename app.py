import streamlit as st
import openai
import pandas as pd
import csv
from datetime import datetime
import os
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("Re:Me – 自己内省AI")

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

import altair as alt

st.markdown("### 📊 感情スコアの推移")

if st.session_state.log:
    # DataFrame化と整形
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")

    # 📈 感情スコア 時系列折れ線グラフ
    st.markdown("#### 🔹 時系列の感情スコア推移")
    st.line_chart(df.set_index("日時")["感情スコア"])

    # 📊 曜日ごとの感情スコア（平均）
    st.markdown("#### 🔹 曜日別の感情スコア（平均）")
    df["曜日英語"] = df["日時"].dt.day_name()
    day_map = {
        "Monday": "月", "Tuesday": "火", "Wednesday": "水",
        "Thursday": "木", "Friday": "金", "Saturday": "土", "Sunday": "日"
    }
    df["曜日"] = df["曜日英語"].map(day_map)
    order = ["月", "火", "水", "木", "金", "土", "日"]
    df["曜日"] = pd.Categorical(df["曜日"], categories=order, ordered=True)
    weekly_avg = df.groupby("曜日", observed=True)["感情スコア"].mean().reset_index()

    chart = alt.Chart(weekly_avg).mark_bar().encode(
        x=alt.X("曜日:N", title="曜日"),
        y=alt.Y("感情スコア:Q", title="平均感情スコア"),
        tooltip=["曜日", "感情スコア"]
    ).properties(width=700, height=300)
    st.altair_chart(chart)

    # 📊 週ごとの感情スコア（平均）
    st.markdown("#### 🔹 週ごとの感情スコア（平均）")
    df["週"] = df["日時"].dt.to_period("W").astype(str)
    weekly = df.groupby("週", observed=True)["感情スコア"].mean().reset_index()
    chart_week = alt.Chart(weekly).mark_bar().encode(
        x=alt.X("週:N", title="週"),
        y=alt.Y("感情スコア:Q", title="平均感情スコア"),
        tooltip=["週", "感情スコア"]
    ).properties(width=700, height=300)
    st.altair_chart(chart_week)

    # 📈 月ごとの感情スコア（平均）
    st.markdown("#### 🔹 月ごとの感情スコア（平均）")
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

import streamlit as st
st.set_page_config(layout="wide")  # ← 最初に配置する必要がある！

import openai
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime
import os
import csv

st.title("🧠 Re:Me - 自己内省AI with 3Dアバター & 能力レーダー")

# 🔒 OpenAI APIキー
openai.api_key = st.secrets["OPENAI_API_KEY"]

# 3Dアバター表示
components.html("""
<model-viewer src="avatar.glb"
              alt="3D Avatar"
              auto-rotate camera-controls
              style="width:100%; height:400px;">
</model-viewer>
<script type="module"
  src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js">
</script>
""", height=420)

# セッション初期化
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

    # 感情スコア取得
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

# チャット履歴表示
for msg in st.session_state.messages[1:]:
    role = "🧍‍♀️ あなた" if msg["role"] == "user" else "🤖 Re:Me"
    st.markdown(f"**{role}：** {msg['content']}")

# 感情スコアグラフ
st.markdown("### 📊 感情スコアの推移")
if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")
    st.line_chart(df.set_index("日時")["感情スコア"])
else:
    st.info("まだ感情スコアのデータがありません。まずはチャットしてください。")

# ✅ 混合型レーダーチャート
st.markdown("### 🕸️ 能力レーダーチャート")

# 能力カテゴリ
categories = ["共感力", "論理力", "創造性", "行動力", "継続力", "自己認識"]

# 自己評価スライダー
if st.button("自己評価する"):
    scores = []
    for cat in categories:
        score = st.slider(f"{cat}", 0, 100, 50)
        scores.append(score)
    st.session_state.ability_self = scores

# AI評価（チャットログがある場合のみ）
if st.session_state.log:
    summary_text = "\n".join([log["入力"] for log in st.session_state.log[-5:]])
    ai_prompt = f"""
あなたは自己内省支援AIです。
以下のテキストを分析し、次の6項目の能力を100点満点で数値で評価してください。

- 共感力
- 論理力
- 創造性
- 行動力
- 継続力
- 自己認識

フォーマットは例のようにJSONで出力してください：
{{
  "共感力": 70,
  "論理力": 60,
  ...
}}

入力文：
{summary_text}
"""
    ai_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": ai_prompt}]
    )
    import json, re
    try:
        json_text = re.search(r"\{[\s\S]*\}", ai_response.choices[0].message.content).group()
        ai_scores = json.loads(json_text)
        st.session_state.ability_ai = [ai_scores[cat] for cat in categories]
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



