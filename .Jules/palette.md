## 2024-03-16 - Prevent empty submissions in Streamlit
**Learning:** In Streamlit applications, form buttons do not have native required-field validation like HTML forms. If text inputs are cleared, users might still click run buttons causing backend errors or unhelpful empty states.
**Action:** Always compute `is_disabled = not input_val.strip()` and pass it to `st.button` with a helpful `help` text.
