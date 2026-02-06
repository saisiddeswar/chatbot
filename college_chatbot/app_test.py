import io
import os
import sys

import streamlit as st

# Set UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="College Chatbot", layout="centered")
st.title("College Administrative Chatbot")

st.write("Loading application...")

try:
    st.write("Importing handler...")
    from main import handle_query
    st.write("[OK] Handler imported successfully!")
    
    # ================== INIT CHAT HISTORY ==================
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ================== USER INPUT ==================
    query = st.text_input("Ask your question")

    if query:
        with st.spinner("Processing your question..."):
            try:
                response = handle_query(query, st.session_state.chat_history)
                st.session_state.chat_history.append((query, response))
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                import traceback
                st.error(traceback.format_exc())

    # ================== DISPLAY CHAT ==================
    if st.session_state.chat_history:
        st.markdown("---")
        for q, a in st.session_state.chat_history:
            st.markdown(f"**You:** {q}")
            st.markdown(f"**Bot:** {a}")
            st.markdown("---")
    
except Exception as e:
    st.error(f"[ERROR] Application failed to initialize: {str(e)}")
    import traceback
    st.error(traceback.format_exc())
    
    st.warning("Try reloading the page or contact support if the problem persists.")
