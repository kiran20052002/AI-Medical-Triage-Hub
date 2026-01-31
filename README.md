# AI Medical Triage Hub

An intelligent healthcare support platform that streamlines patient-doctor interactions using AI-powered triage and real-time chat.

## Features

- **AI Triage & Analysis**: Automatically analyzes patient tickets to estimate urgency and suggest relevant specialists.
- **Clinical Triage Reports**: Generates professional summaries for doctors/admins after a conversation ends, replacing traditional SOAP notes with a chat-optimized format:
  - **Chief Complaint**: The primary issue.
  - **Symptoms & Observations**: Patient-reported symptoms.
  - **Assessment**: AI-generated analysis of the situation.
  - **Recommended Plan**: Suggested next steps (ER, GP, Home Care).
- **Real-time Chat**: Integrated messaging between patients and doctors using StreamChat.
- **Smart Routing**: Directs tickets to the appropriate personnel based on AI analysis.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB (Beanie ODM)
- **AI/LLM**: Groq (Llama 3), Google Gemini (Embeddings)
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
