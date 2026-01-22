# AI-Medical-Traige-Hub

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
