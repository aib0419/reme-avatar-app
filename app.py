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
import openai
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(layout="wide")
st.title("🧠 Re:Me 能力レーダーチャート（混合型）")

# OpenAI APIキーの読み込み
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else "YOUR_API_KEY"

# 能力カテゴリ
categories = ["共感力", "論理力", "創造性", "行動力", "継続力", "自己認識"]

# ユーザー入力：自己評価
st.markdown("### 🌟 自己評価")
user_scores = {}
with st.form("self_eval"):
    for cat in categories:
        user_scores[cat] = st.slider(f"{cat}：", 0, 100, 50)
    submitted = st.form_submit_button("評価を送信")

# チャット履歴（仮にここでは固定文を使う）
chat_history = st.text_area("📝 チャット履歴からAIに能力を推論させる（例：最近のやりとりを貼る）", "今日は友達の相談に乗っていて、共感しながら話を聞いた。...", height=150)

# AIによる能力評価
ai_scores = {cat: 50 for cat in categories}  # 初期値
if st.button("🔍 AIに分析させる") and chat_history:
    prompt = f"以下の文章から、次の6つの能力を100点満点で評価してください：{', '.join(categories)}。出力形式はCSVで：能力名,スコア\n文章：{chat_history}"
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    csv_result = response.choices[0].message.content.strip().splitlines()
    try:
        for line in csv_result:
            name, score = line.split(',')
            ai_scores[name.strip()] = int(score.strip())
    except:
        st.warning("⚠️ AIの出力形式に問題がある可能性があります。")

# レーダーチャート描画
if submitted or any(v != 50 for v in ai_scores.values()):
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[user_scores[cat] for cat in categories] + [user_scores[categories[0]]],
        theta=categories + [categories[0]],
        fill='toself',
        name='自己評価',
        line_color='blue'
    ))

    fig.add_trace(go.Scatterpolar(
        r=[ai_scores[cat] for cat in categories] + [ai_scores[categories[0]]],
        theta=categories + [categories[0]],
        fill='toself',
        name='AI評価',
        line_color='orange'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title="🕸️ 能力プロファイル比較"
    )
    st.plotly_chart(fig)
else:
    st.info("自己評価かAI評価のどちらかを実行するとレーダーチャートが表示されます。")



