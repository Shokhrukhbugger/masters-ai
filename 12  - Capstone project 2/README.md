---
title: Developer AI Support Chatbot
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: streamlit
app_file: app.py
pinned: false
license: apache-2.0
---

# Developer AI Support Chatbot

A Generative AI-based customer support web application that answers user questions from PDF manuals using OpenAI and FAISS, and creates support tickets in Jira if the answer cannot be found.

---

## Demo

https://huggingface.co/spaces/Shokhrukh994/support-chatbot

---

## Features

- **Web chat interface:** Built with Streamlit for instant Q&A.
- **Contextual answers:** Finds answers from multiple large PDF documents and always cites file and page number.
- **Hybrid retrieval:** Combines semantic search (OpenAI embeddings + FAISS) with keyword search for best accuracy.
- **Jira integration:** Seamlessly creates support tickets in your Jira project if the question can't be answered.
- **Configurable company info:** Easily set company name, support email, phone, and Jira project details.
- **Secure:** No secrets in code. API keys and tokens are managed via environment variables or Hugging Face Spaces Secrets.
- **Dockerized:** Ready to deploy anywhere (local, server, or Hugging Face Spaces).

---

## Setup & Usage

### 1. **Clone the Repository**

```sh
git clone https://huggingface.co/spaces/Shokhrukh994/support-chatbot
cd support-chatbot
```

---

### 2. **Install Requirements**

**Locally (with Python 3.10+):**

```sh
pip install -r requirements.txt
```

**Or, use Docker:**

```sh
docker build -t support-chatbot .
docker run -p 8501:8501 support-chatbot
```

---

### 3. **Configure Secrets and Company Info**

- All **company info** (name, email, phone, Jira URL, Jira project, Jira email) is set in [`config.py`](config.py).
- All **secrets** (API tokens) must be set as environment variables or via `.streamlit/secrets.toml` (for local) or Hugging Face Spaces “Secrets” (for cloud):

Example `.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."
JIRA_API_TOKEN = "your-jira-api-token"
```

Or, add these secrets using the **Hugging Face Spaces "Secrets" UI**.

---

### 4. **Run the App**

**Locally:**
```sh
streamlit run app.py
```

**Or, using Docker:**
```sh
docker run -p 8501:8501 -v ${PWD}/.streamlit:/app/.streamlit support-chatbot
```

---

## Directory Structure

```
.
├── app.py                # Main Streamlit app
├── config.py             # Company & Jira config (non-secret)
├── requirements.txt      # Python dependencies
├── Dockerfile            # For containerized deployment
├── data/                 # Your PDFs and index files
├── faiss_index/          # Generated vector_storage
└── .streamlit/
    └── secrets.toml      # Local secrets (do not commit!)
```

---

## Adding Data

- Place at least 3 PDF manuals (at least 2 PDFs and one with >400 pages recommended) in the `data/` folder.
- The app will automatically process and embed your PDFs on first run.

---

## Jira Integration

- You need a [Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens).
- The app will create issues in your configured Jira project if the answer can’t be found in the provided documents.

---

## Hugging Face Spaces Deployment

- Add `openai_api_key` and `JIRA_api_token` as secrets in your Space’s “Settings” → “Secrets” tab.
- The app will run on Spaces using the default Streamlit template or your Dockerfile.

---

## Customization

- Update `config.py` for your company and Jira settings.
- Add or replace PDFs in the `data/` directory.

---

## License

MIT

---

## Credits

Developed by Shokhrukh Nazarov, based on OpenAI, Streamlit, and FAISS.

---

## Contact

For support, contact: [`shokhrukh7230@gmail.com`](mailto:shokhrukh7230@gmail.com)

---

**Enjoy your powerful customer support chatbot! 🚀**