# Graph IR Web App

This app turns your Colab assignment flow into a deployable web interface:

- TREC-COVID loading (small subset for speed)
- Dependency graph feature extraction (spaCy)
- Semantic node similarity (SentenceTransformer, with fallback)
- Improved edge similarity (dependency-relation overlap)
- Top-K document retrieval
- Precision/Recall@K for selected TREC topic IDs

## Local Run

From project root:

```bash
pip install -r graph_ir_app/requirements.txt
streamlit run graph_ir_app/app.py
```

If you want full semantic embeddings (recommended), install advanced deps:

```bash
pip install -r graph_ir_app/requirements-advanced.txt
```

## Deploy: Streamlit Community Cloud

1. Push this repo to GitHub.
2. Open [https://share.streamlit.io](https://share.streamlit.io).
3. Click **New app**.
4. Select your repo and branch.
5. Set **Main file path** to:
   `graph_ir_app/app.py`
6. Deploy.

Notes:
- Streamlit Cloud will auto-install from `graph_ir_app/requirements.txt` when app path is in `graph_ir_app/`.
- If you want sentence-transformers there too, replace `graph_ir_app/requirements.txt` content with `requirements-advanced.txt` (or copy advanced entries into `requirements.txt`) before deploying.

## Deploy: Render

### Option A: Blueprint (recommended)
1. Push this repo to GitHub.
2. In Render dashboard, click **New +** -> **Blueprint**.
3. Select this repository.
4. Render reads `render.yaml` and creates service `graph-ir-streamlit`.
5. Deploy.

### Option B: Manual Web Service
1. New -> **Web Service** -> connect repo.
2. Environment: `Python`.
3. Build Command:
   `pip install -r graph_ir_app/requirements.txt`
4. Start Command:
   `streamlit run graph_ir_app/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
5. Deploy.

## Important Notes

- First run in TREC mode can take time due dataset download.
- If spaCy model is unavailable in hosting, app falls back to a blank English pipeline (lower relation quality but app still runs).
- If sentence-transformers is unavailable, app falls back to lightweight deterministic embeddings (app remains usable).
