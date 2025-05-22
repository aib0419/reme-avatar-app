# 修正済みの app.py 全文（ユーザーごとにログ保存）
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

# Firebase関連
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase Admin SDKの初期化
if not firebase_admin._apps:
    firebase_info = json.loads(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.title("🧠 Re:Me – 自己内省AI")

# 🔐 ユーザーID入力
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
st.session_state.user_id = st.text_input("🧑 あなたの名前またはニックネームを入力してください", value=st.session_state.user_id)
user_id = st.session_state.user_id.strip()

# 🔍 Firestore 接続確認のためテスト保存
if user_id and st.button("🔧 Firestoreにテスト保存"):
    test_data = {
        "text": "テスト保存",
        "date": datetime.now().isoformat()
    }
    try:
        db.collection("reme_logs").document(user_id).collection("logs").add(test_data)
        st.success("✅ Firestore に正常に保存できました！Firebase Console を確認してみてください。")
    except Exception as e:
        st.error(f"❌ Firestore保存に失敗しました: {e}")

# OpenAIキー
openai.api_key = st.secrets["OPENAI_API_KEY"]

# 3Dアバター表示
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

# セッション初期化
for key in ["messages", "log", "ability_self", "ability_ai"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "log" in key or "messages" in key else None
if not st.session_state.messages:
    st.session_state.messages = [{"role": "system", "content": "あなたは共感的な内省支援AIです。"}]

# ユーザー入力
st.markdown("### 💬 今日考えたこと・感じたことを話してみてください")
user_input = st.text_input("入力してください", key="chat_input")

if st.button("送信"):
    if not user_id:
        st.warning("⚠️ ユーザー名を入力してください。")
    elif user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.messages
        )
        reply = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": reply})

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

        # 🔽 Firestoreにユーザー別で保存
        if user_id:
            log_data = {
                "date": now,
                "user_input": user_input,
                "ai_reply": reply,
                "emotion_score": score
            }
            db.collection("reme_logs").document(user_id).collection("logs").add(log_data)

        st.rerun()

# チャット履歴表示
for msg in st.session_state.messages[1:]:
    role = "🧍‍♀️ あなた" if msg["role"] == "user" else "🤖 Re:Me"
    st.markdown(f"**{role}：** {msg['content']}")

# 📊 感情スコアグラフ
st.markdown("### 📊 感情スコアの推移")
if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")
    st.line_chart(df.set_index("日時")["感情スコア"])

    df["曜日英語"] = df["日時"].dt.day_name()
    day_map = {"Monday": "月", "Tuesday": "火", "Wednesday": "水", "Thursday": "木", "Friday": "金", "Saturday": "土", "Sunday": "日"}
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
'''


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

from datetime import datetime, date
import pandas as pd
import openai

# ✅ 週間ふりかえりレポート用セクション
st.markdown("## 🗓️ 週間ふりかえりレポート")

# 表示制御フラグ（セッション内で1日1回）
if "report_shown_today" not in st.session_state:
    st.session_state.report_shown_today = False

# ログデータの整形
if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    df["日時"] = pd.to_datetime(df["日時"])
    df = df.sort_values("日時")

    # 🔎 今週のログ抽出（日曜〜土曜のログ）
    today = datetime.today()
    last_monday = today - pd.Timedelta(days=6)
    df_lastweek = df[df["日時"] >= last_monday]

    def generate_weekly_report(df_input):
        logs = "\n".join(df_input["入力"].tolist())
        prompt = f"""
以下の1週間のユーザー発言から、以下の3つを出力してください。

1. 📅 今週の要約（200文字以内）：感情・思考傾向の全体まとめ
2. 💡 コメント（150文字以内）：変化や特徴に言及
3. 🎯 一言アドバイス（50文字以内）：翌週に向けた提案

【発言ログ】：
{logs}
        """
        res = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content

    # ✅ 毎週日曜に自動表示（1日1回）
    if datetime.today().weekday() == 6 and not st.session_state.report_shown_today:
        if not df_lastweek.empty:
            st.markdown("### 📋 今週のふりかえりレポート（自動表示）")
            summary = generate_weekly_report(df_lastweek)
            st.success(summary)
            st.session_state.report_shown_today = True

    # ✅ 手動生成ボタン（いつでも使える）
    if st.button("📝 手動でふりかえりレポートを生成"):
        if not df_lastweek.empty:
            st.markdown("### 📋 今週のふりかえりレポート")
            summary = generate_weekly_report(df_lastweek)
            st.success(summary)
        else:
            st.info("今週のログがまだありません。まずは内省を記録しましょう。")
else:
    st.info("ふりかえりレポートを生成するには、チャット履歴が必要です。")




