      
# --- START OF FILE db_supabase.py ---

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import requests
import toml


@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"] # Pastikan ini adalah service_role key
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


def sign_up(email, password, full_name, role):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        user = response.user

        if user:
            profile_data = {
                "id": user.id,
                "full_name": full_name,
                "role": role,
                "email": email
            }
            supabase.from_("profiles").insert(profile_data).execute()

        return user, None
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, error_message


# --- FUNGSI ADMIN ---
# --- MODIFIKASI: Ditambahkan parameter manager_id ---
def create_user_as_admin(email, password, full_name, role, manager_id=None):
    """
    Membuat pengguna baru via admin. Pengguna langsung aktif.
    """
    supabase = init_connection()
    try:
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name}
        })
        user = response.user

        if user:
            profile_data = {
                "id": user.id,
                "full_name": full_name,
                "role": role,
                "email": email,
                "manager_id": manager_id # Menyimpan ID manajer
            }
            supabase.from_("profiles").insert(profile_data).execute()

        return user, None
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        if "User already exists" in error_message:
            error_message = "Pengguna dengan email ini sudah terdaftar."
        return None, error_message


def get_profile(user_id):
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception:
        return None


# --- Manajemen Pengguna ---
def get_all_profiles():
    supabase = init_connection()
    try:
        # Menambahkan data manajer untuk ditampilkan di tabel
        response = supabase.from_("profiles").select("*, manager:manager_id(full_name)").execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}")
        return []

# --- FUNGSI BARU UNTUK MANAGER ---
def get_team_profiles(manager_id):
    supabase = init_connection()
    try:
        # Ambil profil user itu sendiri dan anggota timnya
        response = supabase.from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data tim: {e}")
        return []

# --- FUNGSI BARU UNTUK MANAGER ---
def get_all_managers():
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("id, full_name").eq("role", "manager").execute()
        return response.data
    except Exception:
        return []


def delete_user_by_id(user_id):
    return False, "Fitur Hapus Pengguna sedang dalam pengembangan."


# --- Marketing Activities CRUD ---
def get_all_marketing_activities():
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}")
        return []

def get_marketing_activities_by_user_id(user_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk pengguna: {e}")
        return []
        
# --- FUNGSI BARU UNTUK MANAGER ---
def get_team_marketing_activities(manager_id):
    supabase = init_connection()
    try:
        # 1. Dapatkan ID semua anggota tim
        team_members = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute()
        team_ids = [member['id'] for member in team_members.data]
        # 2. Sertakan ID manajer itu sendiri
        team_ids.append(manager_id)
        # 3. Ambil aktivitas dari semua ID tersebut
        response = supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data aktivitas tim: {e}")
        return []

def get_activity_by_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("id", activity_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}")
        return None

def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data_to_insert = {
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
        response = supabase.from_("marketing_activities").insert(data_to_insert).execute()
        return True, "Aktivitas berhasil ditambahkan!", response.data[0]["id"]
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data_to_update = {
            "prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person,
            "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email,
            "activity_date": activity_date, "activity_type": activity_type, "description": description, "status": status
        }
        response = supabase.from_("marketing_activities").update(data_to_update).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui aktivitas: {e}"

def delete_marketing_activity(activity_id):
    supabase = init_connection()
    try:
        supabase.from_("followups").delete().eq("activity_id", activity_id).execute()
        supabase.from_("marketing_activities").delete().eq("id", activity_id).execute()
        return True, "Aktivitas berhasil dihapus!"
    except Exception as e:
        return False, f"Gagal menghapus aktivitas: {e}"

# --- Follow-up CRUD ---
def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}")
        return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        next_followup_date_str = next_followup_date.strftime("%Y-%m-%d") if next_followup_date else None
        data_to_insert = {
            "activity_id": activity_id, "marketer_id": marketer_id, "marketer_username": marketer_username,
            "notes": notes, "next_action": next_action, "next_followup_date": next_followup_date_str, "interest_level": interest_level
        }
        response = supabase.from_("followups").insert(data_to_insert).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

# --- Riset Prospek CRUD ---
def get_all_prospect_research():
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}")
        return []

def get_prospect_research_by_marketer(marketer_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").eq("marketer_id", marketer_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}")
        return []

# --- FUNGSI BARU UNTUK MANAGER ---
def get_team_prospect_research(manager_id):
    supabase = init_connection()
    try:
        team_members = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute()
        team_ids = [member['id'] for member in team_members.data]
        team_ids.append(manager_id)
        response = supabase.from_("prospect_research").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data riset prospek tim: {e}")
        return []

def get_prospect_by_id(prospect_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").eq("id", prospect_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}")
        return None

def add_prospect_research(**kwargs):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").insert(kwargs).execute()
        return True, "Prospek berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"

def edit_prospect_research(prospect_id, **kwargs):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").update(kwargs).eq("id", prospect_id).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"

def search_prospect_research(keyword, user_id=None, role=None):
    supabase = init_connection()
    try:
        query = supabase.from_("prospect_research").select("*").or_(
            f"company_name.ilike.%{keyword}%,"
            f"contact_name.ilike.%{keyword}%,"
            f"industry.ilike.%{keyword}%,"
            f"location.ilike.%{keyword}%"
        )
        if role == 'marketing':
            query = query.eq('marketer_id', user_id)
        elif role == 'manager':
            team_members = supabase.from_("profiles").select("id").eq("manager_id", user_id).execute()
            team_ids = [member['id'] for member in team_members.data]
            team_ids.append(user_id)
            query = query.in_('marketer_id', team_ids)

        response = query.execute()
        return response.data
    except Exception as e:
        st.error(f"Error saat mencari prospek: {e}")
        return []


# Sisa kode lainnya (sync_prospect_from_apollo, config, email, zoho) tetap sama
# dan tidak perlu diubah.
# (Saya potong di sini agar tidak terlalu panjang, sisa file Anda aman)

def sync_prospect_from_apollo(query):
    """
    Tarik data prospek dari Apollo.io berdasarkan query.
    """
    url = "https://api.apollo.io/v1/mixed_people_search" 
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": st.secrets["apollo"]["api_key"]  # Harus ada di secrets.toml
    }

    payload = {
        "query": query,
        "page": 1,
        "page_size": 10
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            people = response.json().get("people", [])
            prospects = []

            for person in people:
                org = person.get("organization", {})
                contact = person.get("contact", {})

                prospect_data = {
                    "company_name": org.get("name"),
                    "website": org.get("website_url"),
                    "industry": org.get("industry_tag"),
                    "founded_year": org.get("founded_year"),
                    "company_size": org.get("employee_count"),
                    "revenue": org.get("annual_revenue"),
                    "location": person.get("location"),
                    "contact_name": contact.get("full_name"),
                    "contact_title": contact.get("title"),
                    "contact_email": contact.get("email"),
                    "linkedin_url": contact.get("linkedin_url"),
                    "phone": contact.get("phone_number"),
                    "keywords": org.get("tags", []),
                    "technology_used": org.get("technologies", []),
                    "notes": "",
                    "next_step": "Cold Email",
                    "next_step_date": None,
                    "status": "baru",
                    "source": "Apollo.io",
                    "decision_maker": False,
                    "email_status": "valid",
                    "marketer_id": st.session_state.user.id,
                    "marketer_username": st.session_state.profile.get("full_name")
                }
                prospects.append(prospect_data)

            return prospects
        else:
            st.error(f"Gagal mengambil data dari Apollo.io: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error saat sinkron dari Apollo.io: {e}")
        return []


# --- Konfigurasi Aplikasi ---
def get_app_config():
    supabase = init_connection()
    try:
        response = supabase.from_("config").select("*").execute()
        config = {item['key']: item['value'] for item in response.data}
        return config
    except Exception:
        return {"app_name": "Default Tracker"}


def update_app_config(new_config):
    supabase = init_connection()
    try:
        for key, value in new_config.items():
            supabase.from_("config").update({"value": value}).eq("key", key).execute()
        return True, "Konfigurasi berhasil diperbarui."
    except Exception as e:
        return False, f"Error saat update konfigurasi: {e}"


# --- Template Email (Opsional - Bisa Ditambah Nanti) ---
def save_email_template_to_prospect(prospect_id, template_html):
    supabase = init_connection()
    try:
        data_to_update = {
            "last_email_template": template_html
        }
        supabase.from_("prospect_research").update(data_to_update).eq("id", prospect_id).execute()
        return True, "Template berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan template: {e}"


def send_email_via_zoho(email_data):
    """
    Mengirim email via Zoho Mail API
    """
    url = "https://mail.zoho.com/api/v1/messages" 
    headers = {
        "Authorization": f"Zoho-oauthtoken {st.secrets['zoho']['access_token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": {"address": email_data["from"]},
        "to": [{"address": email_data["to"]}],
        "subject": email_data["subject"],
        "content": [{"type": "text/html", "content": email_data["content"]}]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 202]:
            return True, "Email berhasil dikirim!"
        else:
            return False, f"Gagal kirim email: {response.text}"
    except Exception as e:
        return False, f"Error saat kirim email: {e}"


# --- Refresh Token Zoho ---
def exchange_code_for_tokens(code):
    url = "https://accounts.zoho.com/oauth/v2/token" 
    payload = {
        "code": code, "client_id": st.secrets["zoho"]["client_id"], "client_secret": st.secrets["zoho"]["client_secret"],
        "grant_type": "authorization_code", "redirect_uri": st.secrets["zoho"].get("redirect_uri", "https://emimtsupabase.streamlit.app/") 
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token", "")
            if "refresh_token" in tokens:
                st.secrets["zoho"]["refresh_token"] = tokens.get("refresh_token", "")
            with open(".streamlit/secrets.toml", "w") as f:
                toml.dump(st.secrets._file, f)
            return True, "Token berhasil digenerate!"
        else:
            return False, f"Gagal mendapatkan token: {response.text}"
    except Exception as e:
        return False, f"Error: {e}"


def refresh_zoho_token():
    url = "https://accounts.zoho.com/oauth/v2/token" 
    payload = {
        "grant_type": "refresh_token", "client_id": st.secrets["zoho"]["client_id"],
        "client_secret": st.secrets["zoho"]["client_secret"], "refresh_token": st.secrets["zoho"].get("refresh_token", "")
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token", "")
            if "refresh_token" in tokens:
                st.secrets["zoho"]["refresh_token"] = tokens.get("refresh_token", "")
            with open(".streamlit/secrets.toml", "w") as f:
                toml.dump(st.secrets._file, f)
            return True, "Token berhasil diperbarui!"
        else:
            return False, f"Gagal memperbarui token: {response.text}"
    except Exception as e:
        return False, f"Error saat refresh token: {e}"