
# RVR&JC College Chatbot - Test Queries

Use these questions to verify if the chatbot is working correctly across all three bots.

## 🟢 Bot 1: General Info (Rule-Based)
*These questions should get instant, short pattern-matched answers.*

*   "Where is the college?"
*   "What is the contact number?"
*   "What is the address?"
*   "Who is the principal?"
*   "What are the working hours?"

## 🔵 Bot 2: Semantic QA (Similar Questions)
*These questions rely on finding a similar question in our database.*

*   "How do I apply for a bonafide certificate?"
*   "Is there a gym strictly for students?"
*   "What is the dress code?"
*   "Can I leave the campus during college hours?"
*   "What is the library fine for late return?"
*   "Tell me about the NCC unit."

## 🟣 Bot 3: RAG (Complex Documents)
*These questions require the bot to read the scraped documents and generate an answer.*

*   "What are the placement statistics for 2024?"
*   "Tell me about the CSE department and its intake."
*   "What is the eligibility for B.Tech admission?"
*   "Who are the top recruiters?"
*   "Tell me about the hostel facilities in detail."
*   "What is the breakdown of the EAPCET convener quota?"

## 🧪 Testing Scope & Greeting
*   "Hi" -> Should say "Hi! I am the RVR&JC College Chatbot..."
*   "Who won the cricket match?" -> Should say "I can only answer questions related to RVR&JC..."
*   "Write me a python script" -> Should say "I can only answer questions related to RVR&JC..."
