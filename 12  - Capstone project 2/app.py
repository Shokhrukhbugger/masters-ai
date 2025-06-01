import os
import streamlit as st
import requests
import base64
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

import config

# ─── 1) COMPANY CONSTANTS ─────────────────────────────────────────────────
COMPANY_NAME  = "Shokhrukh Soft"
SUPPORT_EMAIL = "shokhrukh7230@gmail.com"
SUPPORT_PHONE = "+998-97-750-94-72"

# ─── 2) CSS DEFINITIONS ───────────────────────────────────────────────────
css = '''
<style>
.chat-message {
    padding: 1.5rem; 
    border-radius: 0.5rem; 
    margin-bottom: 1rem; 
    display: flex;
}
.chat-message.user {
    background-color: #2b313e;
}
.chat-message.bot {
    background-color: #475063;
}
.chat-message .avatar {
  flex-shrink: 0; 
}
.chat-message .avatar img {
  max-width: 50px;
  max-height: 50px;
  border-radius: 50%;
  object-fit: cover;
}
.chat-message .message {
  width: 80%; 
  padding: 0 1.5rem;
  color: #fff;
  overflow-wrap: break-word;
  word-wrap: break-word;
}

/* Sidebar “About” box styling */
.sidebar-about {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
    background-color: #454749;
}
.sidebar-about p {
    margin: 0.2rem 0;
    font-size: 0.95rem;
}
</style>
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://www.shutterstock.com/image-vector/chat-bot-icon-virtual-smart-600nw-2478937553.jpg" alt="Bot Avatar">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://t4.ftcdn.net/jpg/02/29/75/83/360_F_229758328_7x8jwCwjtBMmC6rgFzLFhZoEpLobB6L8.jpg" alt="User Avatar">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''

JIRA_URL = "https://knowledgeassist.atlassian.net"
JIRA_USERNAME = "navruzbek_safoboev@student.itpu.uz"
JIRA_PROJECT_KEY = "KAN"

# ─── 3) UPDATED PROMPT: company info is now hard-coded in the text ─────────
STRICT_PROMPT = """
You are a helpful assistant representing **Shokhrukh Soft**.

**Company Name:** Shokhrukh Soft  
**Support Email:** shokhrukh7230@gmail.com  
**Support Phone:** +998-97-750-94-72  

Below is the relevant context from the document(s). Answer the user's question using ONLY the provided PDF context _or_ the company information above.  
If the answer cannot be found in the context or the company information, say:
    "I don't know"  
Do not use any other outside knowledge.

Context:
{context}

Question: {question}
Helpful answer:
"""
# ────────────────────────────────────────────────────────────────────────────

NOT_FOUND_MESSAGES = [
    "I don't know",
    "I don't know.",
    "The answer is not in the provided document(s)",
    "The answer is not in the provided document(s)."
]


def create_jira_ticket(summary, description):
    jira_url = config.JIRA_URL
    jira_email = config.JIRA_EMAIL
    if "JIRA_API_TOKEN" not in st.secrets:
        st.error("JIRA_API_TOKEN not found in Streamlit secrets.")
        return False, "JIRA API Token not configured."
    jira_api_token = st.secrets["JIRA_API_TOKEN"]
    jira_project_key = config.JIRA_PROJECT_KEY
    url = f"{jira_url}/rest/api/2/issue/"
    auth = base64.b64encode(f"{jira_email}:{jira_api_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": {
            "project": {"key": jira_project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Task"},
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        if resp.status_code == 201:
            issue_key = resp.json()["key"]
            return True, issue_key
        else:
            return False, resp.text
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {e}"


def get_pdf_chunks(pdf_paths):
    """
    Given a list of file paths to PDFs, read each one, split into chunks,
    and return a list of dicts with keys "text" and "metadata".
    """
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", "."],
        chunk_size=500,
        chunk_overlap=100,
        length_function=len
    )
    all_chunks = []

    for pdf_path in pdf_paths:
        try:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    chunks = text_splitter.split_text(page_text)
                    for chunk_text in chunks:
                        all_chunks.append({
                            "text": chunk_text,
                            "metadata": {
                                "pdf_name": os.path.basename(pdf_path),
                                "page": i + 1
                            }
                        })
        except Exception as e:
            st.error(f"Error reading {pdf_path}: {e}")
    return all_chunks


def build_and_persist_vectorstore(chunks, api_key, persist_dir: str):
    """
    Given text chunks and an OpenAI API key, build a FAISS vectorstore and save it to disk.
    Returns the in-memory vectorstore object.
    """
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    try:
        embeddings = OpenAIEmbeddings(
            api_key=api_key,
            model="text-embedding-3-small",
            batch_size=8
        )
        vectorstore = FAISS.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas
        )
        os.makedirs(persist_dir, exist_ok=True)
        vectorstore.save_local(persist_dir)
        return vectorstore

    except Exception as e:
        st.error(f"Failed to create or save vector store: {e}")
        return None


def load_vectorstore_if_exists(api_key: str, persist_dir: str):
    """
    If a persisted FAISS index exists on disk, load and return it.
    If not, return None.
    """
    if os.path.isdir(persist_dir) and os.listdir(persist_dir):
        try:
            embeddings = OpenAIEmbeddings(
                api_key=api_key,
                model="text-embedding-3-small"
            )
            vectorstore = FAISS.load_local(
                persist_dir,
                embeddings,
                allow_dangerous_deserialization=True
            )
            return vectorstore
        except Exception as e:
            st.error(f"Failed to load existing vector store: {e}")
            return None
    else:
        return None


def get_conversation_chain(vectorstore, api_key):
    """
    Build the ConversationalRetrievalChain using the FAISS vectorstore and return it.
    """
    # ── Now the prompt only needs "context" + "question" ──
    strict_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=STRICT_PROMPT
    )
    try:
        llm = ChatOpenAI(api_key=api_key, model="gpt-4.1-mini")
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": strict_prompt}
        )
        return conversation_chain
    except Exception as e:
        st.error(f"Failed to create conversation chain: {e}")
        return None


def check_if_not_found(answer_text):
    """Helper to detect “not found” style replies."""
    stripped = answer_text.strip()
    if stripped.lower() in ["i don't know", "i don't know."]:
        return True
    if stripped.startswith("The answer is not in the provided document"):
        return True
    return False


def handle_userinput(user_question):
    """
    Called when the user submits a question. Pass to the RAG chain,
    update chat history & referenced pages, or allow Jira creation.
    """
    if st.session_state.conversation is None:
        st.warning("The conversation has not been initialized yet.")
        return

    try:
        # ── Now we only pass "question" ──
        response = st.session_state.conversation({"question": user_question})
    except Exception as e:
        st.error(f"Error during conversation: {e}")
        st.session_state.chat_history.append(HumanMessage(content=user_question))
        st.session_state.chat_history.append(AIMessage(content=f"Sorry, an error occurred: {e}"))
        if "referenced_pages" not in st.session_state:
            st.session_state.referenced_pages = []
        st.session_state.referenced_pages.append([])
        return

    history = response["chat_history"]
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "referenced_pages" not in st.session_state:
        st.session_state.referenced_pages = []

    # Append the latest user/bot messages to state
    st.session_state.chat_history.append(history[-2])  # HumanMessage
    st.session_state.chat_history.append(history[-1])  # AIMessage

    answer_text = history[-1].content
    is_not_found = check_if_not_found(answer_text)

    if is_not_found:
        st.session_state.referenced_pages.append([])
    elif "source_documents" in response and response["source_documents"]:
        seen = set()
        sources = []
        for doc in response["source_documents"]:
            meta = getattr(doc, "metadata", {})
            pdf_name = meta.get("pdf_name", "PDF")
            page = meta.get("page", "?")
            if (pdf_name, page) not in seen:
                seen.add((pdf_name, page))
                sources.append(f"{pdf_name}, page {page}")
        st.session_state.referenced_pages.append(sources)
    else:
        st.session_state.referenced_pages.append([])


def render_chat():
    """
    Loop over st.session_state.chat_history in pairs (user, bot)
    and render the HTML bubbles + any referenced pages or Jira button.
    """
    from collections import defaultdict

    history = st.session_state.get("chat_history", [])
    referenced_pages_list = st.session_state.get("referenced_pages", [])

    if "jira_feedback" not in st.session_state:
        st.session_state.jira_feedback = {}

    bot_idx = 0
    for i in range(0, len(history), 2):
        if i + 1 >= len(history):
            break

        user_message = history[i]
        bot_message = history[i + 1]

        st.write(user_template.replace("{{MSG}}", user_message.content), unsafe_allow_html=True)
        st.write(bot_template.replace("{{MSG}}", bot_message.content), unsafe_allow_html=True)

        current_bot_pages = referenced_pages_list[bot_idx] if bot_idx < len(referenced_pages_list) else []
        answer_text = bot_message.content
        is_not_found = check_if_not_found(answer_text)
        jira_key = f"jira_{bot_idx}_{i}"

        if current_bot_pages:
            grouped = defaultdict(list)
            for ref in current_bot_pages:
                try:
                    pdf_name, page_str = ref.rsplit(", page ", 1)
                    grouped[pdf_name].append(page_str)
                except ValueError:
                    grouped["?"].append(ref)
            refs_str = "; ".join(
                f"{pdf_name} - {', '.join(page_list)}"
                for pdf_name, page_list in grouped.items()
            )
            st.markdown(f'''
            <div class="chat-sub-item-wrapper">
                <div class="chat-sub-item-content" style="background-color:#22324c; padding:10px; margin-bottom:10px; border-radius:8px; color:#fff;">
                    <b>Referenced pages:</b> {refs_str}
                </div>
            </div>
            ''', unsafe_allow_html=True)

        elif is_not_found:
            if not st.session_state.jira_feedback.get(jira_key, False):
                st.markdown(f'''
                <div class="chat-sub-item-wrapper">
                    <div class="chat-sub-item-content">
                ''', unsafe_allow_html=True)
                if st.button("📝 Create Jira Ticket", key=f"jira_btn_{jira_key}"):
                    st.session_state.active_jira_request = {
                        'key': jira_key,
                        'question': user_message.content,
                    }
                    st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="background-color:#1e3a2e; padding:10px; '
                    'border-radius:4px; color:#4ade80; margin-bottom:1rem; margin-top:1rem;">'
                    '✅ Jira ticket has been created for this question'
                    '</div>',
                    unsafe_allow_html=True
                )

        bot_idx += 1


def render_jira_form():
    """
    If user clicked “Create Jira Ticket,” show the form for summary/description.
    Otherwise, do nothing.
    """
    if 'active_jira_request' not in st.session_state:
        return

    jira_req = st.session_state.active_jira_request
    jira_key = jira_req['key']
    question = jira_req['question']

    st.markdown("---")
    st.subheader("Create Jira Ticket")

    with st.form(key=f"jira_form_{jira_key}"):
        st.write(f"**Question:** {question}")
        email = st.text_input("Your email", key=f"email_for_{jira_key}")
        summary = st.text_input(
            "Ticket summary",
            value=f"Missing information: {question[:50]}...",
            key=f"summary_for_{jira_key}"
        )
        description = st.text_area(
            "Describe what information should be added:",
            key=f"desc_for_{jira_key}"
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit Ticket")
        with col2:
            cancelled = st.form_submit_button("Cancel")

        if submitted:
            if email and summary and description:
                description_full = (
                    f"User email: {email}\n\n"
                    f"Original question: {question}\n\n"
                    f"Description: {description}"
                )
                with st.spinner("Creating Jira ticket..."):
                    success, result = create_jira_ticket(summary, description_full)
                if success:
                    st.success(f"✅ Jira ticket created successfully! Issue: {result}")
                    st.session_state.jira_feedback[jira_key] = True
                    del st.session_state.active_jira_request
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create Jira ticket: {result}")
            else:
                st.error("Please fill in all fields")
        if cancelled:
            del st.session_state.active_jira_request
            st.rerun()


def main():
    # ─── 1) Verify API keys, page config, CSS injection ───────────────────
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("OPENAI_API_KEY not found in Streamlit secrets.")
        st.stop()
    openai_api_key = st.secrets["OPENAI_API_KEY"]

    st.set_page_config(page_title="Dev AI Chatbot", page_icon="🤖")
    st.write(css, unsafe_allow_html=True)

    # ─── 2) State initialization ───────────────────────────────────────────
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "referenced_pages" not in st.session_state:
        st.session_state.referenced_pages = []
    if "jira_feedback" not in st.session_state:
        st.session_state.jira_feedback = {}

    st.header("Developer AI Support Chatbot 🤖")

    # ─── 3) Hardcoded PDF paths & FAISS index dir ─────────────────────────
    PDF_PATHS = [
        "data/Topic1.pdf",
        "data/Topic2.pdf",
        # Add more PDFs here if you wish
    ]
    FAISS_INDEX_DIR = "faiss_index"

    # ─── 4) Load or build the FAISS index ─────────────────────────────────
    if st.session_state.conversation is None:
        vectorstore = load_vectorstore_if_exists(openai_api_key, FAISS_INDEX_DIR)
        if vectorstore is None:
            chunks = get_pdf_chunks(PDF_PATHS)
            if not chunks:
                st.error("Could not read text from any of the hardcoded PDFs.")
                st.stop()

            with st.spinner("Building vectorstore from PDFs (this happens only once)..."):
                vectorstore = build_and_persist_vectorstore(chunks, openai_api_key, FAISS_INDEX_DIR)
                if vectorstore is None:
                    st.stop()  # Something went wrong during index creation

        conversation_chain = get_conversation_chain(vectorstore, openai_api_key)
        if conversation_chain:
            st.session_state.conversation = conversation_chain
            st.success("Vectorstore ready! You can now ask questions.")
        else:
            st.error("Failed to set up the conversation chain.")
            st.stop()

    # ─── 5) Render question box and handle submissions ────────────────────
    if 'active_jira_request' not in st.session_state:
        with st.form(key="user_question_form"):
            user_question_text = st.text_input("Ask a question about your documents:", label_visibility="collapsed")
            submit_button = st.form_submit_button(label="Ask")

        if submit_button and user_question_text:
            handle_userinput(user_question_text)
            st.rerun()

    # ─── 6) Show chat history (if any) and Jira form (if triggered) ───────
    if st.session_state.get("chat_history"):
        render_chat()

    render_jira_form()

    # ─── 7) Sidebar: show improved company info + instructions ─────────────
    with st.sidebar:
        st.markdown("### 🏢 About Shokhrukh Soft", unsafe_allow_html=True)
        st.markdown(f'''
        <div class="sidebar-about">
          <p>🏷️ <b>Company:</b> {COMPANY_NAME}</p>
          <p>✉️ <b>Email:</b> <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
          <p>📞 <b>Phone:</b> {SUPPORT_PHONE}</p>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown("---", unsafe_allow_html=True)

        st.markdown("### ℹ️ How to use this App", unsafe_allow_html=True)
        st.markdown("""
        1. **Type any question** about your hard-coded PDFs into the input box above.  
        2. The bot will search the documents and reply with relevant excerpts.  
        3. If it cannot find an answer, it will say “I don’t know” and show a **📝 Create Jira Ticket** button.  
        4. Click that button to request missing information (your ticket will go to our Jira).  
        5. Scroll up/down to revisit the chat history or see referenced pages.  
        6. If you ever update the PDF files, delete the `faiss_index/` folder and restart to re-index.
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
