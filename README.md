# AI Medical Triage Hub

An intelligent healthcare support platform that streamlines patient-doctor interactions using AI-powered triage and real-time chat.

## Features

- **AI Triage & Analysis**: Automatically analyzes patient tickets to estimate urgency and suggest relevant specialists.

- **Clinical Triage (SOAP) Reports**: Generates professional medical summaries for admins and doctors using the SOAP format:
  - **Subjective (S)**: Patient's complaints, history, and reported symptoms.
  - **Objective (O)**: Direct observations, including photos or exam findings.
  - **Assessment (A)**: Professional AI analysis and likely diagnosis.
  - **Plan (P)**: Recommended treatment, tests ordered, and follow-up advice.

- **Real-time Chat**: Integrated messaging between patients and doctors using StreamChat.

- **Smart Routing**: Directs tickets to the appropriate personnel based on AI analysis.

- **Agentic RAG Chatbot**: A state-of-the-art medical assistant powered by **LangGraph**.
  - **3-Stage Guard Pipeline**: Existing local ML models validate queries for gibberish/non-medical content before reaching the agent.
  - **Smart Routing**: Detects medical emergencies and vague symptoms for immediate prioritized responses.
  - **Corrective RAG (CRAG)**: An automated grading loop that evaluates the relevance of retrieved documents.
  - **Iterative Query Transformation**: If a database search fails, the agent re-optimizes and re-phrases the query for a more accurate search.
  - **Concise & Grounded Answers**: Strictly answers based on past cases without unnecessary conversational fluff.

## User Roles & Capabilities

### 🏥 Patient

- Create support tickets describing their symptoms.
- Chat with assigned doctors in real-time.
- View status of their active cases.

### 👨‍⚕️ Doctor

- Receive assigned tickets based on specialization.
- Live chat with patients to diagnose issues.
- **One-Click Report Generation**: Generate an AI summary at the end of a consultation.
- Mark tickets as resolved.

### 🛡️ Admin

- **Dashboard Overview**: View platform stats (Total Patients, Doctors, Tickets).
- **Manage Doctors**: View list of registered specialists.
- **Medical Reports**: Browse all AI-generated triage reports.
- _Note: Admin accounts are virtual and configured via environment variables._

- **Backend**: FastAPI (Python)
- **Database**: MongoDB (Beanie ODM)
- **AI/LLM**: Groq (Llama 3), Google Gemini (Embeddings), **LangGraph (Agentic Orchestration)**
- **Local ML/NLP**: Scikit-Learn (MultinomialNB, RandomForest), NLTK (PorterStemmer, Stopwords)
- **Real-time**: StreamChat
- **Auth**: JWT (Stateless)

## Authentication

This project uses a **Stateless Authentication** mechanism secured by **JSON Web Tokens (JWT)**.

### How it works:

1.  **Login**: Users (Patients, Doctors, Admins) authenticate via `/auth/login`.
2.  **Token Generation**: Upon successful validation, the server generates a JWT containing:
    - `sub`: User email
    - `role`: User role (patient, doctor, admin)
    - `id`: User ID
3.  **Storage**: The JWT is sent to the client and stored in an **HTTPOnly Cookie** named `access_token`. This prevents client-side access.
4.  **Verification**: Protected routes use the `get_current_user` dependency to read the cookie, decode the token, and verify the user session.

### Key Libraries:

- `python-jose`: For JWT encoding/decoding.
- `passlib`: For password hashing (bcrypt).
