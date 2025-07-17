# --- START OF FILE db_supabase.py (Versi Final Absolut) ---

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
from gotrue.errors import AuthApiError

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase. Detail: {e}"); st.stop()

def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

# --- FUNGSI AUTENTIKASI ---
def sign_in(email, password):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except AuthApiError:
        return None, "Kombinasi email & password salah."
    except Exception as e:
        return None, f"Terjadi error: {e}"

def create_user_as_admin(email, password, full_name, role, manager_id=None):
    supabase = init_connection()
    try:
        user_response = supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
        user = user_response.user
        if user and user.id:
            profile_data = {"id": user.id, "full_name": full_name, "role": role, "email": email, "manager_id": manager_id}
            supabase.from_("profiles").insert(profile_data).execute()
            return user, None
        else:
            return None, "Gagal membuat entri otentikasi."
    except Exception as e:
        return None, f"Gagal mendaftarkan: {e}"

def get_profile(user_id):
    if not user_id: return None
    try:
        return init_connection().from_("profiles").select("*").eq("id", user_id).maybe_single().execute().data
    except: return None

# --- MANAJEMEN PENGGUNA ---
def get_all_profiles(): return init_connection().from_("profiles").select("*, manager:manager_id(full_name)").execute().data
def get_team_profiles(manager_id):
    if not manager_id: return []
    return init_connection().from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").execute().data
def get_all_managers(): return init_connection().from_("profiles").select("id, full_name").eq("role", "manager").execute().data

# --- AKTIVITAS PEMASARAN (BENTUK ASLI YANG SEDERHANA) ---
def get_all_marketing_activities(): return init_connection().from_("marketing_activities").select("*").order("created_at", desc=True).execute().data
def get_marketing_activities_by_user_id(user_id):
    if not user_id: return []
    return init_connection().from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute().data
def get_team_marketing_activities(manager_id):
    if not manager_id: return []
    supabase = init_connection(); team_ids_res = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute(); team_ids = [m['id'] for m in team_ids_res.data]; team_ids.append(manager_id)
    return supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
def get_activity_by_id(activity_id):
    if not activity_id: return None
    return init_connection().from_("marketing_activities").select("*").eq("id", activity_id).maybe_single().execute().data

def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"marketer_id": marketer_id, "marketer_username": marketer_username, "prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": activity_date, "activity_type": activity_type, "description": description, "status": status}
        response = supabase.from_("marketing_activities").insert(data).execute()
        return True, "Aktivitas berhasil ditambahkan!", response.data[0].get("id") if response.data else None
    except Exception as e: return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": activity_date, "activity_type": activity_type, "description": description, "status": status}
        supabase.from_("marketing_activities").update(data).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e: return False, f"Gagal memperbarui: {e}"

# --- FOLLOW-UP ---
def get_followups_by_activity_id(activity_id): return init_connection().from_("followups").select("*").eq("activity_id", str(activity_id)).execute().data
def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection(); supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
    data = {"activity_id": activity_id, "marketer_id": marketer_id, "marketer_username": marketer_username, "notes": notes, "next_action": next_action, "next_followup_date": date_to_str(next_followup_date), "interest_level": interest_level}
    supabase.from_("followups").insert(data).execute(); return True, "Follow-up berhasil ditambahkan."