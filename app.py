import streamlit as st

st.set_page_config(page_title="Student Grade System", layout="wide")

st.title(" Student Grade Analysis System")

col1, col2 = st.columns(2)

with col1:
    if st.button("Student Login", use_container_width=True):
        st.switch_page("student.py")

with col2:
    if st.button("Teacher Login", use_container_width=True):
        st.switch_page("teacher.py")