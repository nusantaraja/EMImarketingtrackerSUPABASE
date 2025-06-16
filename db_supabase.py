# --- START OF FILE db_supabase.py (Lengkap & Final) ---

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
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
    """
    Membuat pengguna di Supabase Auth dan menyisipkan profilnya di tabel 'profiles'.
    Memerlukan hak akses admin (service_role key).
    """
    supabase = init_connection()
    try:
        # Langkah 1: Buat pengguna di sistem otentikasi Supabase
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True  # Langsung konfirmasi email
        })
        user = response.user
        if user:
            # Langkah 2: Buat profil untuk pengguna baru di tabel 'profiles'
            profile_data = {
                "id": user.id,
                "full_name": full_name,
                "role": role,
                "email": email,
                "manager_id": manager_id
            }
            supabase.from_("profiles").insert(profile_data).execute()
        return user, None
    except Exception as e:
        # Memberikan pesan error yang lebih jelas
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        if "User already exists" in error_message:
            return None, "Pengguna dengan email ini sudah terdaftar."
        return None, error_message

def get_profile(user_id):
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*").eq("id", user_id).single().execute().data
    except Exception: return None

# --- Manajemen Pengguna ---
def get_all_profiles():
    """Mengambil semua profil dan data manajer mereka jika ada."""
    supabase = init_connection()
    try:
        # Menggunakan join untuk mengambil nama lengkap manajer
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}"); return []

def get_team_profiles(manager_id):
    """Mengambil profil manajer dan semua anggota tim di bawahnya."""
    supabase = init_connection()
    try:
        # Mengambil profil manajer itu sendiri DAN semua user yang manager_id-nya adalah dia
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data tim: {e}"); return []

def get_all_managers():
    """Mengambil daftar semua pengguna dengan role 'manager'."""
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
        team_ids = [m['id'] for m in supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute().data]
        team_ids.append(manager_id)
        return supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data aktivitas tim: {e}"); return []

def get_activity_by_id(activity_id):
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("id", activity_id).single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}"); return None

def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"marketer_id": marketer_id, "marketer_username": marketer_username, "prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": activity_date, "activity_type": activity_type, "description": description, "status": status}
        response = supabase.from_("marketing_activities").insert(data).execute()
        return True, "Aktivitas berhasil ditambahkan!", response.data[0]["id"]
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data = {"prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": activity_date, "activity_type": activity_type, "description": description, "status": status}
        supabase.from_("marketing_activities").update(data).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui aktivitas: {e}"

# --- Follow-up ---
def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        return supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).execute().data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}"); return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        # Helper function untuk mengubah date object ke string
        def date_to_str(dt):
            return dt.strftime("%Y-%m-%d") if isinstance(dt, datetime.date) else dt

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
        team_ids = [m['id'] for m in supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute().data]
        team_ids.append(manager_id)
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
    payload = {"query": query, "page": 1, "per_page": 10} # 'page_size' diganti 'per_page' untuk Apollo API
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            people, prospects = response.json().get("people", []), []
            for person in people:
                org = person.get("organization", {}) or {}
                contact = person.get("contact", {}) or {}
                prospect_data = {
                    "company_name": org.get("name"), 
                    "website": org.get("website_url"), 
                    "industry": org.get("industry"),
                    "location": person.get("city", "") + ", " + person.get("state", ""),
                    "contact_name": person.get("name"), 
                    "contact_title": person.get("title"), 
                    "contact_email": person.get("email"),
                    "linkedin_url": person.get("linkedin_url"),
                    "source": "apollo",
                    "status": "baru",
                    "marketer_id": st.session_state.user.id,
                    "marketer_username": st.session_state.profile.get("full_name")
                }
                prospects.append({k: v for k, v in prospect_data.items() if v is not None}) # Hapus nilai None
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
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": st.secrets["zoho"]["client_id"],
        "client_secret": st.secrets["zoho"]["client_secret"],
        "refresh_token": st.secrets["zoho"].get("refresh_token", "")
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # Raise HTTPError for bad responses
        tokens = response.json()
        if "access_token" in tokens:
            # Perhatian: Ini tidak akan mengubah secrets di Streamlit Cloud secara permanen.
            # Ini hanya akan bekerja selama sesi aplikasi berjalan.
            st.secrets["zoho"]["access_token"] = tokens["access_token"]
            return True, "Token berhasil diperbarui!"
        else:
            return False, f"Gagal memperbarui token: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Error saat refresh token: {e}"

def send_email_via_zoho(email_data):
    # Dapatkan akun pengirim dari secrets Zoho
    sender_account_id = st.secrets["zoho"].get("account_id")
    if not sender_account_id:
        return False, "account_id tidak ditemukan di konfigurasi Zoho secrets."
    
    url = f"https://mail.zoho.com/api/v1/accounts/{sender_account_id}/messages"

    def attempt_send():
        headers = {"Authorization": f"Zoho-oauthtoken {st.secrets['zoho']['access_token']}"}
        payload = {
            "fromAddress": email_data["from"],
            "to": [{"emailAddress": email_data["to"]}],
            "subject": email_data["subject"],
            "content": email_data["content"],
            "mailFormat": "html"
        }
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
                return False, f"Gagal me-refresh token. Silakan generate ulang di halaman Pengaturan. Detail: {refresh_msg}"

        if response.status_code == 200:
            return True, "Email berhasil dikirim!"
        else:
            return False, f"Gagal kirim email. Status: {response.status_code}, Pesan: {response.text}"
    except Exception as e:
        return False, f"Error saat kirim email: {e}"

def exchange_code_for_tokens(code):
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "code": code,
        "client_id": st.secrets["zoho"]["client_id"],
        "client_secret": st.secrets["zoho"]["client_secret"],
        "grant_type": "authorization_code",
        "redirect_uri": st.secrets["zoho"].get("redirect_uri", "https://emimtsupabase.streamlit.app/")
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        tokens = response.json()
        
        if "access_token" in tokens:
            # Sama seperti refresh, ini hanya untuk sesi ini.
            # Pengguna HARUS menyimpan refresh_token secara manual di secrets.
            st.secrets["zoho"]["access_token"] = tokens.get("access_token")
            if "refresh_token" in tokens:
                st.secrets["zoho"]["refresh_token"] = tokens.get("refresh_token")
                st.info(f"Refresh Token Baru: {tokens.get('refresh_token')}. HARAP SIMPAN INI di secrets Streamlit Anda.")
            return True, "Token berhasil digenerate! Pastikan untuk menyimpan refresh_token baru jika ada."
        else:
            return False, f"Gagal mendapatkan token: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Error: {e}"