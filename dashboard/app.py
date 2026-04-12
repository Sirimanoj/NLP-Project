from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"
API_TIMEOUT = 3

st.set_page_config(page_title="AgentShield Dashboard", layout="wide")
st.title("AgentShield Security Dashboard")

with st.sidebar:
    st.header("Session Settings")
    session_id = st.text_input("Session ID", value="session-1")
    user_id = st.text_input("User ID", value="user-1")
    role = st.selectbox("Role", options=["user", "admin"], index=0)

api_online = False
try:
    health = requests.get(f"{API_BASE}/health", timeout=API_TIMEOUT)
    api_online = health.status_code == 200
except requests.RequestException:
    api_online = False

if api_online:
    st.success("API status: online")
else:
    st.error("API status: offline. Start FastAPI on http://127.0.0.1:8000")

query = st.text_area("Message", value="Check balance for CUST1001")
if st.button("Send Message", type="primary"):
    if not api_online:
        st.error("Cannot send message: backend API is offline.")
    else:
        payload = {"session_id": session_id, "user_id": user_id, "role": role, "message": query}
        try:
            response = requests.post(f"{API_BASE}/chat", json=payload, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            st.subheader("Agent Response")
            st.write(data.get("response"))

            risk = data.get("risk", {})
            if risk:
                cols = st.columns(4)
                cols[0].metric("Total Risk", f"{risk.get('total_score', 0):.1f}")
                cols[1].metric("Semantic", f"{risk.get('semantic_score', 0):.1f}")
                cols[2].metric("Structural", f"{risk.get('structural_score', 0):.1f}")
                cols[3].metric("Context Deviation", f"{risk.get('context_deviation_score', 0):.1f}")

            if data.get("approval_required"):
                st.warning(f"Approval required. ID: {data['approval_id']}")
                approve = st.button("Approve Pending Action")
                reject = st.button("Reject Pending Action")
                if approve or reject:
                    r = requests.post(
                        f"{API_BASE}/approve",
                        json={"approval_id": data["approval_id"], "approved": bool(approve)},
                        timeout=API_TIMEOUT,
                    )
                    st.json(r.json())
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")

st.subheader("Audit Chain")
if not api_online:
    st.info("Audit unavailable while API is offline.")
else:
    payload = {"session_id": session_id, "user_id": user_id, "role": role, "message": query}
    try:
        verify_resp = requests.get(f"{API_BASE}/audit/verify", timeout=API_TIMEOUT)
        verify_resp.raise_for_status()
        st.json(verify_resp.json())
    except requests.RequestException as exc:
        st.error(f"Could not verify audit chain: {exc}")

st.subheader("Recent Audit Events")
if not api_online:
    st.info("Recent events unavailable while API is offline.")
else:
    try:
        events_resp = requests.get(f"{API_BASE}/audit/recent?limit=20", timeout=API_TIMEOUT)
        events_resp.raise_for_status()
        events = events_resp.json()
        if events:
            df = pd.DataFrame(events)
            st.dataframe(df[["id", "timestamp", "event_type", "user_id", "session_id", "role"]], use_container_width=True)
            with st.expander("Raw Event Payloads"):
                st.code(json.dumps(events, indent=2), language="json")
        else:
            st.info("No audit events yet.")
    except requests.RequestException as exc:
        st.error(f"Could not load events: {exc}")
