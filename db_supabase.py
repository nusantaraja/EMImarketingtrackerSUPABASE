# --- START OF FILE db_supabase.py (Versi FINAL, Lengkap, dan Aman) ---

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
        st.error(f"Gagal terhubung ke Supabase. Pastikan secrets sudah benar. Detail: {e}")
        st.stop()
        return None

def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (datetime, date)) else dt

# --- Fungsi Autentikasi ---
def sign_in(email, password):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        error_message = str(e.args[0].get('message', str(e)))
        if "Invalid login credentials" in error_message:
            return None, "Kombinasi email & password salah."
        return None, error_message

def create_user_as_admin(email, password, full_name, role, manager_id=None):
    supabase = init_connection()
    if not all([email, password, full_name, role]):
        return None, "Email, password, nama lengkap, dan role tidak boleh kosong."
    try:
        response = supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
        user = response.user
        if user and user.id:
            profile_data = {"id": user.id, "full_name": full_name, "role": role, "email": email, "manager_id": manager_id}
            supabase.from_("profiles").insert(profile_data).execute()
            return user, None
        else:
            return None, "Gagal membuat entri otentikasi pengguna."
    except Exception as e:
        error_message = str(e.args[0].get('message', str(e)))
        return None, "Pengguna dengan email ini sudah terdaftar." if "User already exists" in error_message else error_message

def get_profile(user_id):
    if not user_id: return None
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*").eq("id", user_id).maybe_single().execute().data
    except Exception: return None

# --- Manajemen Pengguna ---
def get_all_profiles():
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").execute().data
    except Exception as e: st.error(f"Gagal mengambil data pengguna: {e}"); return []

def get_team_profiles(manager_id):
    if not manager_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").execute().data
    except Exception as e: st.error(f"Gagal mengambil data tim: {e}"); return []

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
    except Exception as e: st.error(f"Error mengambil data aktivitas: {e}"); return []

def get_marketing_activities_by_user_id(user_id):
    if not user_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute().data
    except Exception as e: st.error(f"Error mengambil data aktivitas: {e}"); return []

def get_team_marketing_activities(manager_id):
    if not manager_id: return []
    supabase = init_connection()
    try:
        team_member_res = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute()
        team_ids = [m['id'] for m in team_member_res.data]
        team_ids.append(manager_id)
        return supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e: st.error(f"Gagal mengambil data aktivitas tim: {e}"); return []

def get_activity_by_id(activity_id):
    if not activity_id: return None
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("id", activity_id).maybe_single().execute().data
    except Exception as e: st.error(f"Error mengambil detail aktivitas: {e}"); return None

def add_marketing_activity(
    marketer_id, marketer_username, prospect_name, prospect_location, 
    contact_person, contact_position, contact_phone, contact_email, 
    activity_date, activity_type, description, status
):
    """
    Menambahkan satu catatan aktivitas pemasaran ke database.
    Menerima semua argumen secara eksplisit.
    """
    supabase = init_connection()

    # Validasi data penting sebelum mengirim
    if not all([marketer_id, marketer_username, prospect_name]):
        error_msg = "Data krusial (ID Marketing, Username, Nama Prospek) tidak boleh kosong."
        return False, error_msg, None

    try:
        # Siapkan data dictionary dari semua argumen
        data = {
            "marketer_id": marketer_id,
            "marketer_username": marketer_username,
            "prospect_name": prospect_name,
            "prospect_location": prospect_location,
            "contact_person": contact_person,
            "contact_position": contact_position,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "activity_date": activity_date,
            "activity_type": activity_type,
            "description": description,
            "status": status
        }
        
        # Eksekusi perintah insert
        response = supabase.from_("marketing_activities").insert(data).execute()
        
        # Cek apakah data berhasil ditambahkan dan kembalikan ID baru
        if response.data and len(response.data) > 0:
            return True, "Aktivitas berhasil ditambahkan!", response.data[0].get("id")
        else:
            # Error ini biasanya terjadi karena RLS yang memblokir INSERT
            return False, "Gagal menambahkan aktivitas ke database. Periksa kebijakan RLS (INSERT).", None

    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, **kwargs):
    if not activity_id: return False, "ID Aktivitas tidak valid."
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update(kwargs).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e: return False, f"Gagal memperbarui aktivitas: {e}"

# --- Follow-up ---
def get_followups_by_activity_id(activity_id):
    if not activity_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).execute().data
    except Exception as e: st.error(f"Error mengambil data follow-up: {e}"); return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    if not all([activity_id, marketer_id, notes]):
        return False, "ID Aktivitas, ID Marketing, dan Catatan tidak boleh kosong."
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        data = {"activity_id": activity_id, "marketer_id": marketer_id, "marketer_username": marketer_username, "notes": notes, "next_action": next_action, "next_followup_date": date_to_str(next_followup_date), "interest_level": interest_level}
        supabase.from_("followups").insert(data).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e: return False, f"Gagal menambahkan follow-up: {e}"

# --- FUNGSI YANG HILANG DITAMBAHKAN DI SINI ---
# --- Riset Prospek ---
def get_all_prospect_research():
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}"); return []

def get_prospect_research_by_marketer(marketer_id):
    if not marketer_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").eq("marketer_id", marketer_id).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}"); return []
        
def get_team_prospect_research(manager_id):
    if not manager_id: return []
    supabase = init_connection()
    try:
        team_member_res = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute()
        team_ids = [m['id'] for m in team_member_res.data]
        team_ids.append(manager_id)
        return supabase.from_("prospect_research").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data riset prospek tim: {e}"); return []

def get_prospect_by_id(prospect_id):
    if not prospect_id: return None
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").eq("id", prospect_id).maybe_single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}"); return None

def add_prospect_research(**kwargs):
    supabase = init_connection()
    if not kwargs.get("company_name"):
        return False, "Nama perusahaan wajib diisi."
    try:
        supabase.from_("prospect_research").insert(kwargs).execute()
        return True, "Prospek berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"

def edit_prospect_research(prospect_id, **kwargs):
    if not prospect_id: return False, "ID Prospek tidak valid."
    supabase = init_connection()
    try:
        supabase.from_("prospect_research").update(kwargs).eq("id", prospect_id).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"

def search_prospect_research(keyword: str):
    """
    Mencari prospek berdasarkan beberapa kata kunci.
    Setiap kata kunci akan diterapkan sebagai filter AND.
    """
    supabase = init_connection()
    try:
        # 1. Bersihkan dan pecah input menjadi kata kunci terpisah
        # Mengganti koma dengan spasi, lalu memecah berdasarkan spasi
        keywords = [k.strip() for k in keyword.replace(",", " ").split() if k.strip()]

        # Jika tidak ada kata kunci setelah dibersihkan, kembalikan daftar kosong
        if not keywords:
            return []

        # 2. Mulai query dasar
        query = supabase.from_("prospect_research").select("*")

        # 3. Terapkan filter untuk SETIAP kata kunci
        # Ini akan membuat rantai filter: .or_(filter_untuk_kata1).or_(filter_untuk_kata2)
        # yang berfungsi sebagai (Kondisi Kata 1) AND (Kondisi Kata 2)
        for k in keywords:
            or_filter_string = (
                f"company_name.ilike.%{k}%,"
                f"contact_name.ilike.%{k}%,"
                f"industry.ilike.%{k}%,"
                f"location.ilike.%{k}%"
            )
            query = query.or_(or_filter_string)

        # 4. Eksekusi query yang sudah lengkap
        response = query.execute()
        return response.data

    except Exception as e:
        # Memberikan detail error jika ada masalah
        st.error(f"Error saat mencari prospek: {e}")
        return []

# --- Sinkronisasi dari Apollo.io ---
def sync_prospect_from_apollo(query):
    # Asumsi `st.secrets` bisa diakses dari modul ini
    if "apollo" not in st.secrets or not st.secrets["apollo"].get("api_key"):
        st.error("Kunci API Apollo tidak ditemukan di secrets.")
        return []
    
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

# --- Konfigurasi Aplikasi & Zoho --- (Tanpa perubahan)
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