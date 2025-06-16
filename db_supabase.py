# --- START OF FILE db_supabase.py (Versi Perbaikan Error Final) ---

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
import requests
import toml

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error("Gagal terhubung ke Supabase. Pastikan secrets sudah benar.")
        st.stop()
        return None

# --- Fungsi Autentikasi ---
def sign_in(email, password):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, error_message

def create_user_as_admin(email, password, full_name, role, manager_id=None):
    supabase = init_connection()
    try:
        response = supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
        user = response.user
        if user:
            profile_data = {"id": user.id, "full_name": full_name, "role": role, "email": email, "manager_id": manager_id}
            supabase.from_("profiles").insert(profile_data).execute()
        return user, None
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, "Pengguna dengan email ini sudah terdaftar." if "User already exists" in error_message else error_message

def get_profile(user_id):
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*").eq("id", user_id).single().execute().data
    except Exception: return None

# --- Manajemen Pengguna ---
def get_all_profiles():
    supabase = init_connection()
    try:
        # PERBAIKAN: Menggunakan 'ascending=True' bukan 'asc=True'
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").order("full_name", ascending=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}"); return []

def get_team_profiles(manager_id):
    supabase = init_connection()
    try:
        # PERBAIKAN: Menggunakan 'ascending=True' bukan 'asc=True'
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").order("full_name", ascending=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data tim: {e}"); return []

def get_all_managers():
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("id, full_name").eq("role", "manager").execute().data
    except Exception: return []

# --- Marketing Activities ---
def get_all_marketing_activities():
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}"); return []

def get_marketing_activities_by_user_id(user_id):
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}"); return []

def get_team_marketing_activities(manager_id):
    supabase = init_connection()
    try:
        team_profiles = get_team_profiles(manager_id)
        if not team_profiles: return []
        team_ids = [p['id'] for p in team_profiles]
        return supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data aktivitas tim: {e}"); return []

def get_activity_by_id(activity_id):
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("id", activity_id).single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}"); return None
        
def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"marketer_id": marketer_id, "marketer_username": marketer_username, "prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": date_to_str(activity_date), "activity_type": activity_type, "description": description, "status": status}
        response = supabase.from_("marketing_activities").insert(data).execute()
        return True, "Aktivitas berhasil ditambahkan!", response.data[0]["id"]
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": date_to_str(activity_date), "activity_type": activity_type, "description": description, "status": status}
        supabase.from_("marketing_activities").update(data).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui aktivitas: {e}"

# --- Follow-up ---
def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        return supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}"); return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        data = {"activity_id": activity_id, "marketer_id": marketer_id, "marketer_username": marketer_username, "notes": notes, "next_action": next_action, "next_followup_date": date_to_str(next_followup_date), "interest_level": interest_level}
        supabase.from_("followups").insert(data).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

# --- Riset Prospek ---
def get_all_prospect_research():
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}"); return []

def get_prospect_research_by_marketer(marketer_id):
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").eq("marketer_id", marketer_id).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}"); return []
        
def get_team_prospect_research(manager_id):
    supabase = init_connection()
    try:
        team_profiles = get_team_profiles(manager_id)
        if not team_profiles: return []
        team_ids = [p['id'] for p in team_profiles]
        return supabase.from_("prospect_research").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data riset prospek tim: {e}"); return []

def get_prospect_by_id(prospect_id):
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").eq("id", prospect_id).single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}"); return None

def add_prospect_research(**kwargs):
    supabase = init_connection()
    try:
        supabase.from_("prospect_research").insert(kwargs).execute()
        return True, "Prospek berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"

def edit_prospect_research(prospect_id, **kwargs):
    supabase = init_connection()
    try:
        supabase.from_("prospect_research").update(kwargs).eq("id", prospect_id).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"

def search_prospect_research(keyword):
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").or_(f"company_name.ilike.%{keyword}%,contact_name.ilike.%{keyword}%,industry.ilike.%{keyword}%,location.ilike.%{keyword}%").execute().data
    except Exception as e:
        st.error(f"Error saat mencari prospek: {e}"); return []

# --- Sinkronisasi dari Apollo.io ---
def sync_prospect_from_apollo(query):
    url = "https://api.apollo.io/v1/mixed_people_search"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": st.secrets["apollo"]["api_key"]}
    payload = {"query": query, "page": 1, "page_size": 10}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            people, prospects = response.json().get("people", []), []
            for person in people:
                org, contact = person.get("organization", {}), person.get("contact", {})
                prospect_data = { "company_name": org.get("name"), "website": org.get("website_url"), "industry": org.get("industry_tag"), "contact_name": contact.get("full_name"), "contact_title": contact.get("title"), "contact_email": contact.get("email"), "marketer_id": st.session_state.user.id, "marketer_username": st.session_state.profile.get("full_name") }
                prospects.append(prospect_data)
            return prospects
        else:
            st.error(f"Gagal mengambil data dari Apollo.io: {response.text}"); return []
    except Exception as e:
        st.error(f"Error saat sinkron dari Apollo.io: {e}"); return []

# --- Konfigurasi Aplikasi & Zoho ---
def get_app_config():
    supabase = init_connection()
    try:
        response = supabase.from_("config").select("*").execute()
        return {item['key']: item['value'] for item in response.data}
    except Exception: return {"app_name": "Default Tracker"}

def update_app_config(new_config):
    supabase = init_connection()
    try:
        for key, value in new_config.items():
            supabase.from_("config").update({"value": value}).eq("key", key).execute()
        return True, "Konfigurasi berhasil diperbarui."
    except Exception as e: return False, f"Error saat update konfigurasi: {e}"

def save_email_template_to_prospect(prospect_id, template_html):
    supabase = init_connection()
    try:
        supabase.from_("prospect_research").update({"last_email_template": template_html}).eq("id", prospect_id).execute()
        return True, "Template berhasil disimpan!"
    except Exception as e: return False, f"Gagal menyimpan template: {e}"

def refresh_zoho_token():
    url, payload = "https://accounts.zoho.com/oauth/v2/token", {"grant_type": "refresh_token", "client_id": st.secrets["zoho"]["client_id"], "client_secret": st.secrets["zoho"]["client_secret"], "refresh_token": st.secrets["zoho"].get("refresh_token", "")}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token", "")
            return True, "Token berhasil diperbarui!"
        else: return False, f"Gagal memperbarui token: {response.text}"
    except Exception as e: return False, f"Error saat refresh token: {e}"

def send_email_via_zoho(email_data):
    url = "https://mail.zoho.com/api/v1/messages"
    def attempt_send():
        headers = {"Authorization": f"Zoho-oauthtoken {st.secrets['zoho']['access_token']}", "Content-Type": "application/json"}
        payload = {"from": {"address": email_data["from"]}, "to": [{"address": email_data["to"]}], "subject": email_data["subject"], "content": [{"type": "text/html", "content": email_data["content"]}]}
        return requests.post(url, json=payload, headers=headers)
    try:
        response = attempt_send()
        if response.status_code == 401:
            st.info("Access token Zoho kedaluwarsa. Mencoba me-refresh...")
            refresh_success, refresh_msg = refresh_zoho_token()
            if refresh_success:
                st.info("Token berhasil diperbarui. Mencoba mengirim email lagi...")
                response = attempt_send()
            else:
                return False, f"Gagal me-refresh token: {refresh_msg}"
        if response.status_code in [200, 202]: return True, "Email berhasil dikirim!"
        else: return False, f"Gagal kirim email: {response.text}"
    except Exception as e: return False, f"Error saat kirim email: {e}"

def exchange_code_for_tokens(code):
    url, payload = "https://accounts.zoho.com/oauth/v2/token", {"code": code, "client_id": st.secrets["zoho"]["client_id"], "client_secret": st.secrets["zoho"]["client_secret"], "grant_type": "authorization_code", "redirect_uri": st.secrets["zoho"].get("redirect_uri", "https://emimtsupabase.streamlit.app/")}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token", "")
            if "refresh_token" in tokens: st.secrets["zoho"]["refresh_token"] = tokens.get("refresh_token", "")
            return True, "Token berhasil digenerate!"
        else: return False, f"Gagal mendapatkan token: {response.text}"
    except Exception as e: return False, f"Error: {e}"