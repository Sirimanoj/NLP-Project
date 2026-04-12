# AgentShield

AgentShield is a zero-cost, end-to-end project for **Security in Agentic AI**.  
It implements a customer-support agent protected by 5 layers:

1. Input Guard (prompt-injection and PII masking)
2. Threat Scorer (semantic + structural + context risk score)
3. Behavioral Monitor (tool-call anomaly detection)
4. Integrity Layer (human-in-the-loop approval for risky actions)
5. Audit Layer (tamper-evident hash-chained logs)

## Project Structure

```
agent/       # core orchestration + tools
security/    # input guard, pii masking, output filter, access control
scorer/      # threat scoring + behavior profiling
audit/       # hash-chained audit logger
dashboard/   # streamlit dashboard
attacks/     # attack simulation scripts
data/        # mock DB + RAG documents
main.py      # FastAPI entrypoint
```

## Quick Start

1. Create and activate venv
2. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Optional: copy env defaults

```bash
copy .env.example .env
```

4. Run API

```bash
uvicorn main:app --reload
```

5. Run dashboard (new terminal)

```bash
streamlit run dashboard/app.py
```

6. Run attack simulation (new terminal)

```bash
python attacks/demo_attacks.py
```

Notes:
- `AGENTSHIELD_ENABLE_EMBEDDINGS=0` keeps startup fast in early development.
- Set `AGENTSHIELD_ENABLE_EMBEDDINGS=1` when you are ready to run semantic embedding scoring.

## API Endpoints

- `GET /health`
- `POST /chat`
- `POST /approve`
- `GET /audit/verify`
- `GET /audit/recent?limit=50`

## Suggested Team Ownership

- Member 1: `agent/`
- Member 2: `security/` + `audit/`
- Member 3: `scorer/`
- Member 4: `dashboard/` + `attacks/`

## Sample Chat Payload

```json
{
  "session_id": "team-demo",
  "user_id": "user-1",
  "role": "user",
  "message": "Check balance for CUST1001"
}
```

## Graph IR Assignment Web App

A separate Graph IR implementation was added for your NLP course project based on:
**Information Retrieval Using Dependency Graphs (Graph IR) with TREC-COVID**.

### Local Streamlit Prototype

```bash
streamlit run graph_ir_app/app.py
```

See: `graph_ir_app/README.md`

### Production Deployment (Recommended)

- **Frontend on Vercel**: `graph_ir_frontend/`
- **Backend on Render**: `graph_ir_backend/`

Docs:
- `graph_ir_frontend/README.md`
- `graph_ir_backend/README.md`

Quick deploy flow:
1. Deploy backend first on Render using `render.yaml`.
2. Copy Render backend URL (for example `https://graph-ir-api.onrender.com`).
3. Deploy frontend on Vercel with root directory `graph_ir_frontend`.
4. Open Vercel app and paste Render URL into `Render API Base URL`.

Deployment configs included:
- `render.yaml` (Render Blueprint for Graph IR backend API)
- `graph_ir_frontend/vercel.json` (Vercel static routing)
