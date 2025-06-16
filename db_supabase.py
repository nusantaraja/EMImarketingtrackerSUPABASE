import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import requests
import toml
import pandas as pd


# --- Koneksi ke Supabase ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error("Gagal terhubung ke Supabase. Pastikan secrets benar.")
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


def get_profile(user_id):
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("*").eq("id", str(user_id)).single().execute()
        return response.data
    except Exception:
        return None


# --- Manajemen Pengguna (Superadmin Only) ---
def page_user_management():
    st.title("Manajemen Pengguna")
    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        profiles = get_all_profiles()
        if profiles:
            df = pd.DataFrame(profiles).rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role', 'email': 'Email'})
            st.dataframe(df[['User ID', 'Nama Lengkap', 'Email', 'Role']], use_container_width=True)
        else:
            st.info("Belum ada pengguna terdaftar.")

    with tab2:
        full_name = st.text_input("Nama Lengkap")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["superadmin", "manager", "marketing", "sales", "cfo", "finance", "it", "tech", "engineer"])
        if st.button("Daftarkan Pengguna Baru"):
            if not all([full_name, email, password]):
                st.error("Semua field wajib diisi!")
            else:
                user, error = sign_up(email, password, full_name, role)
                if user:
                    st.success(f"Pengguna {full_name} berhasil didaftarkan.")
                    st.rerun()
                else:
                    st.error(f"Gagal mendaftarkan: {error}")


def get_all_profiles():
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data profil: {e}")
        return []


# --- Marketing Activities CRUD ---
def get_all_marketing_activities():
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error ambil aktivitas: {e}")
        return []


def get_marketing_activities_by_user_id(user_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("marketer_id", str(user_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error ambil aktivitas per marketing: {e}")
        return []


def get_activity_by_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("id", str(activity_id)).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error ambil detail aktivitas: {e}")
        return None


def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key):
    supabase = init_connection()
    try:
        data_to_insert = {
            "marketer_id": str(marketer_id),
            "marketer_username": marketer_username,
            "prospect_name": prospect_name,
            "prospect_location": prospect_location,
            "contact_person": contact_person,
            "contact_position": contact_position,
            "contact_email": contact_email,
            "activity_date": activity_date,
            "activity_type": activity_type,
            "description": description,
            "status": status_key
        }

        response = supabase.from_("marketing_activities").insert(data_to_insert).execute()
        return True, "Aktivitas berhasil ditambahkan!", response.data[0]["id"]
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None


def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key):
    supabase = init_connection()
    try:
        data_to_update = {
            "prospect_name": prospect_name,
            "prospect_location": prospect_location,
            "contact_person": contact_person,
            "contact_position": contact_position,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "activity_date": activity_date,
            "activity_type": activity_type,
            "description": description,
            "status": status_key
        }

        response = supabase.from_("marketing_activities").update(data_to_update).eq("id", str(activity_id)).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui aktivitas: {e}"

def delete_marketing_activity(activity_id):
    supabase = init_connection()
    try:
        supabase.from_("followups").delete().eq("activity_id", str(activity_id)).execute()
        supabase.from_("marketing_activities").delete().eq("id", str(activity_id)).execute()
        return True, "Aktivitas berhasil dihapus!"
    except Exception as e:
        return False, f"Gagal menghapus aktivitas: {e}"

def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error ambil follow-up: {e}")
        return []

def add_followup(activity_id, marketer_id, notes, next_action, next_followup_date, interest_level, new_status_key):
    supabase = init_connection()
    try:
        # Update status utama
        supabase.from_("marketing_activities").update({"status": new_status_key}).eq("id", str(activity_id)).execute()

        # Format tanggal follow-up
        next_followup_date_str = next_followup_date.strftime("%Y-%m-%d") if next_followup_date else None

        data_to_insert = {
            "activity_id": str(activity_id),
            "marketer_id": str(marketer_id),
            "notes": notes,
            "next_action": next_action,
            "next_followup_date": next_followup_date_str,
            "interest_level": interest_level
        }

        response = supabase.from_("followups").insert(data_to_insert).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

def get_all_prospect_research():
    supabase = init_connection()
    try:
        response = supabase.from_("prospects").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil riset prospek: {e}")
        return []

def get_prospect_research_by_marketer(marketer_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospects").select("*").eq("marketer_id", str(marketer_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil prospek per marketing: {e}")
        return []

def search_prospect_research(query):
    supabase = init_connection()
    try:
        response = supabase.from_("prospects").select("*").text_search("company_name,contact_name,industry,location", query).execute()
        return response.data
    except Exception as e:
        st.error(f"Error pencarian prospek: {e}")
        return []

def add_prospect_research(**kwargs):
    supabase = init_connection()
    try:
        data_to_insert = {
            "marketer_id": kwargs.get("marketer_id"),
            "marketer_username": kwargs.get("marketer_username"),
            "company_name": kwargs.get("company_name"),
            "website": kwargs.get("website"),
            "industry": kwargs.get("industry"),
            "founded_year": kwargs.get("founded_year"),
            "company_size": kwargs.get("company_size"),
            "revenue": kwargs.get("revenue"),
            "location": kwargs.get("location"),
            "contact_name": kwargs.get("contact_name"),
            "contact_title": kwargs.get("contact_title"),
            "contact_email": kwargs.get("contact_email"),
            "linkedin_url": kwargs.get("linkedin_url"),
            "phone": kwargs.get("phone"),
            "keywords": kwargs.get("keywords"),
            "technology_used": kwargs.get("technology_used"),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status"),
            "source": kwargs.get("source"),
            "decision_maker": kwargs.get("decision_maker", False),
            "email_status": kwargs.get("email_status", "valid")
        }

        response = supabase.from_("prospects").insert(data_to_insert).execute()
        return True, "Prospek berhasil disimpan."
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"

def edit_prospect_research(prospect_id, **kwargs):
    supabase = init_connection()
    try:
        data_to_update = {
            "company_name": kwargs.get("company_name"),
            "website": kwargs.get("website"),
            "industry": kwargs.get("industry"),
            "founded_year": kwargs.get("founded_year"),
            "company_size": kwargs.get("company_size"),
            "revenue": kwargs.get("revenue"),
            "location": kwargs.get("location"),
            "contact_name": kwargs.get("contact_name"),
            "contact_title": kwargs.get("contact_title"),
            "contact_email": kwargs.get("contact_email"),
            "linkedin_url": kwargs.get("linkedin_url"),
            "phone": kwargs.get("phone"),
            "keywords": kwargs.get("keywords"),
            "technology_used": kwargs.get("technology_used"),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status"),
            "source": kwargs.get("source")
        }

        response = supabase.from_("prospects").update(data_to_update).eq("id", str(prospect_id)).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"

def delete_prospect_by_id(prospect_id):
    supabase = init_connection()
    try:
        supabase.from_("prospects").delete().eq("id", str(prospect_id)).execute()
        return True, "Prospek berhasil dihapus!"
    except Exception as e:
        return False, f"Gagal menghapus prospek: {e}"

def exchange_code_for_tokens(code):
    zoho_secrets = st.secrets["zoho"]
    token_url = "https://accounts.zoho.com/oauth/v2/token" 
    payload = {
        "code": code,
        "client_id": zoho_secrets["client_id"],
        "client_secret": zoho_secrets["client_secret"],
        "grant_type": "authorization_code",
        "redirect_uri": zoho_secrets.get("redirect_uri", "https://emimtsupabase.streamlit.app/") 
    }

    try:
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token")
            st.secrets["zoho"]["refresh_token"] = tokens.get("refresh_token")
            return True, "Token berhasil diperbarui."
        else:
            st.error(f"Gagal mendapatkan access token: {response.text}")
            return False, f"Error: {response.text}"
    except Exception as e:
        st.error(f"Error saat exchange code: {e}")
        return False, f"Error: {e}"


def refresh_zoho_token():
    zoho_secrets = st.secrets["zoho"]
    token_url = "https://accounts.zoho.com/oauth/v2/token" 
    payload = {
        "refresh_token": zoho_secrets["refresh_token"],
        "client_id": zoho_secrets["client_id"],
        "client_secret": zoho_secrets["client_secret"],
        "grant_type": "refresh_token"
    }

    try:
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            tokens = response.json()
            st.secrets["zoho"]["access_token"] = tokens.get("access_token")
            return True, "Token berhasil diperbarui."
        else:
            return False, f"Error saat refresh token: {response.text}"
    except Exception as e:
        return False, f"Error saat refresh token: {e}"


def send_email_via_zoho(email_data):
    access_token = st.secrets["zoho"].get("access_token")
    from_email = st.secrets["zoho"].get("from_email")

    if not access_token or not from_email:
        return False, "Zoho token atau alamat email tidak tersedia."

    url = "https://mail.zoho.com/api/v1/messages" 
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": {"address": from_email},
        "to": [{"address": email_data.get("to")}],
        "subject": email_data.get("subject"),
        "content": [{"type": "text/html", "content": email_data.get("content")}]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 202]:
            return True, "Email berhasil dikirim!"
        else:
            return False, f"Error mengirim email: {response.text}"
    except Exception as e:
        return False, f"Gagal mengirim email: {e}"

