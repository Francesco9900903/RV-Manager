import streamlit as st

def render_insight(insight) -> None:
    text = f"**{insight.title}**\n\n{insight.message}"
    if insight.action:
        text += f"\n\n_Azione suggerita: {insight.action}_"

    if insight.level == "critical":
        st.error(text)
    elif insight.level == "warning":
        st.warning(text)
    elif insight.level == "success":
        st.success(text)
    else:
        st.info(text)
