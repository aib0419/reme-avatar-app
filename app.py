# 修正済みの app.py 全文（ユーザーごとにログ保存）
import streamlit as st
st.set_page_config(layout="wide")

# 🔄 モード選択（通常／メモリアル）
st.sidebar.title("モード選択")
mode = st.sidebar.radio("使用モードを選択してください", ["通常モード", "メモリアルモード"])


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

# ✅ このまま使ってください（json.loads は不要）
if not firebase_admin._apps:
    firebase_info = dict(st.secrets["firebase"])  # ← ここが重要！
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

if mode == "メモリアルモード":
    st.title("🕊️ メモリアルモード - 故人との対話")

    # 🔐 ユーザーIDを取得（例：故人の名前）
    avatar_user_id = st.text_input("故人の名前（ユーザーID）を入力してください", key="memorial_user")

    
    if avatar_user_id:
        # 🦊 3Dアバター表示
        components.html("""<model-viewer src="https://raw.githubusercontent.com/aib0419/reme-avatar-app/main/avatar.glb"
                          alt="3D Avatar" auto-rotate camera-controls
                          style="width: 100%; height: 400px;">
        </model-viewer>
        <script type="module"
        src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js">
        </script>""", height=420)

        st.markdown("### 💬 故人アバターと対話する")
        visitor_input = st.text_input("メッセージを入力", key="memorial_chat")

        if visitor_input:
            # Firestoreからログ取得
            logs_ref = db.collection("reme_logs").document(avatar_user_id).collection("logs")
            logs = logs_ref.order_by("date", direction=firestore.Query.DESCENDING).limit(50).stream()
            user_texts = [doc.to_dict().get("user_input", "") for doc in logs]
            user_texts.reverse()

            summary = "\n".join(user_texts)
            memorial_prompt = f"""
あなたは以下の文章から再構築された人格AIです。
以下はあなたが生前に書いた内省的な発言ログです。

[人格データ]:
{summary}

訪問者の問いかけに対して、あなたらしい文体・価値観で応答してください。

[問いかけ]:
{visitor_input}
"""

            reply = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": memorial_prompt}]
            ).choices[0].message.content

            st.markdown(f"👤 **{avatar_user_id}：** {reply}")
    
    st.stop()  # ⚠️ 通常モードの処理を停止


st.title("🧠 Re:Me – 自己内省AI")

# 🔐 ユーザーID入力
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
st.session_state.user_id = st.text_input("🧑 あなたの名前またはニックネームを入力してください", value=st.session_state.user_id)
user_id = st.session_state.user_id.strip()

# Firestore からログを復元（セッションに）
if "log_loaded" not in st.session_state:
    st.session_state.log_loaded = True
    st.session_state.log = []

    try:
        docs = db.collection("reme_logs").document(user_id).collection("logs").order_by("date").stream()
        for doc in docs:
            st.session_state.log.append(doc.to_dict())
    except Exception as e:
        st.warning(f"ログの取得に失敗しました: {e}")


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
    
# 🔍 Firestoreからユーザー別ログを取得してDataFrame化
df_log = pd.DataFrame()

if user_id:
    try:
        docs = db.collection("reme_logs").document(user_id).collection("logs").stream()
        records = [doc.to_dict() for doc in docs]

        if records:
            df_log = pd.DataFrame(records)

            if "date" in df_log.columns:
                df_log["日時"] = pd.to_datetime(df_log["date"])
            elif "日時" in df_log.columns:
                df_log["日時"] = pd.to_datetime(df_log["日時"])
            else:
                st.warning("ログに 'date' や '日時' がありません。")
                df_log = pd.DataFrame()
                
            df_log = df_log.sort_values("日時")
        else:
            st.info("Firestoreに保存されたログがまだありません。")

    except Exception as e:
        st.error(f"Firestore読み込みエラー: {e}")
else:
    st.warning("ユーザー名を入力してください。")



# 📊 感情スコアグラフ（カラー強調バージョン）
st.markdown("### 📊 感情スコアの推移")

df = pd.DataFrame()

if user_id:
    try:
        docs = db.collection("reme_logs").document(user_id).collection("logs").stream()
        all_logs = [doc.to_dict() for doc in docs]

        if all_logs:
            df = pd.DataFrame(all_logs)
            df = df.loc[:, ~df.columns.duplicated()]
            if "日時" in df.columns:
                df["日時"] = pd.to_datetime(df["日時"])
            elif "date" in df.columns:
                df["日時"] = pd.to_datetime(df["date"])
            else:
                st.warning("ログに '日時' または 'date' の列がありません。")
                df = pd.DataFrame()
        else:
            st.info("まだFirestoreにデータがありません。")
    except Exception as e:
        st.error(f"データ取得時にエラーが発生しました: {e}")
else:
    st.info("ユーザー名を入力すると、あなた専用の感情スコアグラフが表示されます。")

# ▼▼ 表示処理 ▼▼
if not df.empty and "emotion_score" in df.columns:
    df = df.sort_values("日時")
    df = df[df["emotion_score"].between(0, 100)]

    # 🎨 カラー強調グラフ
    st.markdown("#### 🎨 感情スコア")
    color_chart = alt.Chart(df).mark_circle(size=100).encode(
        x=alt.X("日時:T", title="日時"),
        y=alt.Y("emotion_score:Q", title="感情スコア", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("emotion_score:Q", scale=alt.Scale(scheme="redyellowgreen"), legend=None),
        tooltip=["日時:T", "emotion_score:Q"]
    ) + alt.Chart(df).mark_line().encode(
        x="日時:T", y="emotion_score:Q"
    )
    st.altair_chart(color_chart.properties(width=700, height=300), use_container_width=True)

    # 🔽 折りたたみで分析表示
    with st.expander("📅 曜日・週・月ごとの感情スコア平均"):
        # 曜日処理
        df["曜日英語"] = df["日時"].dt.day_name()
        day_map = {
            "Monday": "月", "Tuesday": "火", "Wednesday": "水",
            "Thursday": "木", "Friday": "金", "Saturday": "土", "Sunday": "日"
        }
        df["曜日"] = df["曜日英語"].map(day_map)
        order = ["月", "火", "水", "木", "金", "土", "日"]
        df["曜日"] = pd.Categorical(df["曜日"], categories=order, ordered=True)

        # 🔹 曜日別
        st.markdown("#### 🔹 曜日別 平均")
        weekly_avg = df.groupby("曜日", observed=True)["emotion_score"].mean().reset_index()
        st.altair_chart(alt.Chart(weekly_avg).mark_bar().encode(
            x="曜日:N", y="emotion_score:Q", tooltip=["曜日", "emotion_score"]
        ).properties(width=300, height=200))

        # 🔹 週ごと
        st.markdown("#### 🔹 週ごと平均")
        df["週"] = df["日時"].dt.to_period("W").astype(str)
        weekly = df.groupby("週", observed=True)["emotion_score"].mean().reset_index()
        st.altair_chart(alt.Chart(weekly).mark_bar().encode(
            x="週:N", y="emotion_score:Q", tooltip=["週", "emotion_score"]
        ).properties(width=300, height=200))

        # 🔹 月ごと
        st.markdown("#### 🔹 月ごと平均")
        df["月"] = df["日時"].dt.to_period("M").astype(str)
        monthly = df.groupby("月", observed=True)["emotion_score"].mean().reset_index()
        st.altair_chart(alt.Chart(monthly).mark_line(point=True).encode(
            x="月:N", y="emotion_score:Q", tooltip=["月", "emotion_score"]
        ).properties(width=300, height=200))

else:
    st.info("表示できる感情スコアのデータがありません。")







import re, json
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

st.markdown("### 🕸️ 能力レーダーチャート")

categories = ["共感力", "論理力", "創造性", "行動力", "継続力", "自己認識"]

# Firestoreからログ取得
if user_id:
    try:
        docs = db.collection("reme_logs").document(user_id).collection("logs").stream()
        all_logs = [doc.to_dict() for doc in docs]

        if all_logs:
            df_log = pd.DataFrame(all_logs)

            # 🔧 重複列削除
            df_log = df_log.loc[:, ~df_log.columns.duplicated()]

            # 🔍 日時変換
            if "日時" in df_log.columns:
                df_log["日時"] = pd.to_datetime(df_log["日時"])
            elif "date" in df_log.columns:
                df_log["日時"] = pd.to_datetime(df_log["date"])
            else:
                st.warning("ログに '日時' または 'date' の列がありません。")
                df_log = pd.DataFrame()

            df_log["日付"] = df_log["日時"].dt.date

            # 日付指定
            today = datetime.today().date()
            yesterday = today - pd.Timedelta(days=1)

            def extract_scores_by_date(target_date):
                if df_log.empty or "日付" not in df_log.columns or "user_input" not in df_log.columns:
                    return None
                    
                logs = df_log[df_log["日付"] == target_date]
                if logs.empty:
                    return None

                # 🔧 NaN除外 & 文字列化
                text = "\n".join([str(x) for x in logs["user_input"].tolist() if pd.notna(x)])
            
                prompt = f"""
            以下のテキストから、次の6つの能力を100点満点で評価してください。
            - 共感力・論理力・創造性・行動力・継続力・自己認識
            
            JSON形式で：
            {{"共感力":70,"論理力":60,...}}
            
            テキスト：
            {text}
            """
                try:
                    res = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    json_text = re.search(r"\{[\s\S]*\}", res.choices[0].message.content).group()
                    scores = json.loads(json_text)
                    return [scores.get(c, 0) for c in categories]
                except Exception as e:
                    st.error(f"AI解析エラー: {e}")
                    return None




            today_scores = extract_scores_by_date(today)
            yesterday_scores = extract_scores_by_date(yesterday)

            if today_scores or yesterday_scores:
                fig = go.Figure()
                if today_scores:
                    fig.add_trace(go.Scatterpolar(
                        r=today_scores + [today_scores[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        name="今日"
                    ))
                if yesterday_scores:
                    fig.add_trace(go.Scatterpolar(
                        r=yesterday_scores + [yesterday_scores[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        name="昨日"
                    ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True
                )
                st.plotly_chart(fig)
            else:
                st.info("レーダーチャートを表示するには、今日または昨日の記録が必要です。")

        else:
            st.info("Firestoreに記録がありません。")

    except Exception as e:
        st.error(f"データ取得時にエラーが発生しました: {e}")
else:
    st.info("ユーザー名を入力すると、あなた専用の分析が表示されます。")











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




