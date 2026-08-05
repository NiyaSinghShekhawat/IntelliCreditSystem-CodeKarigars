# src/database.py
import streamlit as st
from supabase import create_client, Client
from typing import Optional
import uuid

import os
from dotenv import load_dotenv

load_dotenv()  # reads your .env file


@st.cache_resource
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase credentials missing. Check your .env file.")
        st.stop()
    return create_client(url, key)

# @st.cache_resource
# def get_supabase() -> Client:
#     url = st.secrets["SUPABASE_URL"]
#     key = st.secrets["SUPABASE_KEY"]
#     return create_client(url, key)


# ── Entities ──────────────────────────────────────────────

def save_entity(data: dict) -> str:
    """Insert a new entity, return its UUID."""
    sb = get_supabase()
    res = sb.table("entities").insert(data).execute()
    return res.data[0]["id"]


def get_all_entities() -> list:
    sb = get_supabase()
    res = sb.table("entities").select(
        "*").order("created_at", desc=True).execute()
    return res.data


def get_entity(entity_id: str) -> Optional[dict]:
    sb = get_supabase()
    res = sb.table("entities").select(
        "*").eq("id", entity_id).single().execute()
    return res.data


# ── Cases ─────────────────────────────────────────────────

def create_case(entity_id: str) -> str:
    """Create a blank IN_PROGRESS case for an entity, return case UUID."""
    sb = get_supabase()
    res = sb.table("cases").insert({
        "entity_id": entity_id,
        "status": "IN_PROGRESS"
    }).execute()
    return res.data[0]["id"]


def update_case(case_id: str, data: dict):
    """Partial update — pass only the fields you want to change."""
    sb = get_supabase()
    sb.table("cases").update(data).eq("id", case_id).execute()


def get_case(case_id: str) -> Optional[dict]:
    sb = get_supabase()
    res = sb.table("cases").select(
        "*, entities(*)").eq("id", case_id).single().execute()
    return res.data


def get_all_cases() -> list:
    """All cases joined with entity name, for the dashboard."""
    sb = get_supabase()
    res = (
        sb.table("cases")
        .select("*, entities(company_name, sector, loan_amount_cr, loan_type)")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def get_cases_for_entity(entity_id: str) -> list:
    sb = get_supabase()
    res = (
        sb.table("cases")
        .select("*")
        .eq("entity_id", entity_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data
