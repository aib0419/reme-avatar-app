import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("🦊 Re:Me アバター表示テスト")

# 3Dアバターを表示
components.html("""
<model-viewer src="avatar.glb"
              alt="Re:Me Avatar"
              auto-rotate
              camera-controls
              style="width:100%; height:400px;">
</model-viewer>

<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
""", height=420)
