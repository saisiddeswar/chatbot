# import io
# import os
# import sys

# import streamlit as st

# # Set UTF-8 encoding for all output streams
# if sys.stdout.encoding != 'utf-8':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# if sys.stderr.encoding != 'utf-8':
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# # Add current directory to path for imports
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from main import handle_query

# st.set_page_config(page_title="College Chatbot", layout="centered")
# st.title("College Administrative Chatbot")

# try:
#     # ================== INIT CHAT HISTORY ==================
#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []

#     # ================== USER INPUT ==================
#     query = st.text_input("Ask your question")

#     if query:
#         with st.spinner("Processing your question..."):
#             try:
#                 response = handle_query(query, st.session_state.chat_history)
                
#                 # Save conversation
#                 st.session_state.chat_history.append((query, response))
#             except Exception as e:
#                 st.error(f"Error processing query: {str(e)}")
#                 import traceback
#                 st.error(traceback.format_exc())

#     # ================== DISPLAY CHAT ==================
#     if st.session_state.chat_history:
#         st.markdown("---")
#         for q, a in st.session_state.chat_history:
#             st.markdown(f"**You:** {q}")
#             st.markdown(f"**Bot:** {a}")
#             st.markdown("---")
    
# except Exception as e:
#     st.error(f"[ERROR] Application failed to initialize: {str(e)}")
#     import traceback
#     st.error(traceback.format_exc())

import os
import sys
import chainlit as cl

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import handle_query


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])
    
    # Get Top FAQs
    from core.stats_manager import StatsManager
    top_questions = StatsManager.get_top_queries(n=4)
    
    actions = [
        cl.Action(name="faq", value=q, label=q)
        for q in top_questions
    ]
    
    await cl.Message(
        content="👋 *Hi! I'm the College Administrative Chatbot.*\n\nAsk me anything, or choose a popular question below:",
        actions=actions
    ).send()

@cl.action_callback("faq")
async def on_action(action: cl.Action):
    # Retrieve chat history
    chat_history = cl.user_session.get("chat_history")
    
    # Send the user's "message" to the UI
    await cl.Message(
        content=action.value,
        author="User"
    ).send()
    
    # Process
    try:
        response = handle_query(action.value, chat_history)
        chat_history.append((action.value, response))
        
        await cl.Message(content=response).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ Error: {str(e)}"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    chat_history = cl.user_session.get("chat_history")

    try:
        response = handle_query(message.content, chat_history)
        chat_history.append((message.content, response))

        await cl.Message(content=response).send()

    except Exception as e:
        await cl.Message(
            content=f"❌ Error processing your query:\n```\n{str(e)}\n```"
        ).send()

