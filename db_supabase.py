# db_supabase.py

import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- Inisialisasi Koneksi ---
@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error("Gagal terhubung ke Supabase. Periksa file secrets.toml atau Secrets di Streamlit Cloud.")
        raise e

# --- Fungsi Autentikasi Profesional ---
def sign_in(email, password):
    """Melakukan sign-in menggunakan Supabase Auth."""
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_up(email, password, full_name, role):
    """Mendaftarkan pengguna baru menggunakan Supabase Auth."""
    supabase = init_connection()
    try:
        # Mendaftarkan user ke auth.users, sambil menyisipkan data tambahan
        response = supabase.auth.sign_up(
            {
                "email": email, 
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": role
                    }
                }
            }
        )
        return response.user, None
    except Exception as e:
        return None, str(e)

def get_profile(user_id):
    """Mengambil profil (termasuk role) dari pengguna."""
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception:
        return None

# --- Fungsi Manajemen Pengguna (Untuk Superadmin) ---
def get_all_profiles():
    """Mengambil semua profil pengguna dari tabel profiles."""
    supabase = init_connection()
    try:
        response = supabase.from_("profiles").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}")
        return []

def delete_user_by_id(user_id):
    """Menghapus pengguna oleh Admin."""
    # Ini memerlukan kunci service_role yang harus disimpan dengan aman
    # Untuk sementara, fitur ini kita tandai untuk pengembangan selanjutnya.
    # supabase_admin = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_key"])
    # supabase_admin.auth.admin.delete_user(user_id)
    return False, "Fitur Hapus Pengguna sedang dalam pengembangan."


# --- Fungsi CRUD Aktivitas & Follow-up (Tetap Sama) ---
# ... (Semua fungsi CRUD yang sudah ada sebelumnya bisa ditaruh di sini) ...
# ... Mari kita salin ulang dengan sedikit penyesuaian ...

def get_all_marketing_activities():
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}")
        return []

def get_marketing_activities_by_user_id(user_id):
    """Mengambil aktivitas pemasaran berdasarkan ID pengguna."""
    supabase = init_connection()
    try:
        # Mencari berdasarkan kolom BARU yaitu 'marketer_id'
        response = supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk pengguna: {e}")
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
        activity_date_str = activity_date.strftime("%Y-%m-%d") if isinstance(activity_date, datetime) else str(activity_date)
        response = supabase.from_("marketing_activities").insert({
            "marketer_id": marketer_id,
            "marketer_username": marketer_username,
            "prospect_name": prospect_name, "prospect_location": prospect_location,
            "contact_person": contact_person, "contact_position": contact_position,
            "contact_phone": contact_phone, "contact_email": contact_email,
            "activity_date": activity_date_str, "activity_type": activity_type,
            "description": description, "status": status
        }).execute()
        if not response.data: raise Exception(response.error.message if hasattr(response, 'error') else "Unknown error")
        return True, "Aktivitas berhasil ditambahkan.", response.data[0]['id']
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None


def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        activity_date_str = activity_date.strftime("%Y-%m-%d") if isinstance(activity_date, datetime) else str(activity_date)
        response = supabase.from_("marketing_activities").update({
            "prospect_name": prospect_name, "prospect_location": prospect_location,
            "contact_person": contact_person, "contact_position": contact_position,
            "contact_phone": contact_phone, "contact_email": contact_email,
            "activity_date": activity_date_str, "activity_type": activity_type,
            "description": description, "status": status
        }).eq("id", activity_id).execute()
        if not response.data: raise Exception(response.error.message if hasattr(response, 'error') else "Unknown error")
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui: {e}"

def delete_marketing_activity(activity_id):
    supabase = init_connection()
    try:
        supabase.from_("followups").delete().eq("activity_id", activity_id).execute()
        response = supabase.from_("marketing_activities").delete().eq("id", activity_id).execute()
        if not response.data: raise Exception(response.error.message if hasattr(response, 'error') else "Unknown error")
        return True, "Aktivitas berhasil dihapus."
    except Exception as e:
        return False, f"Gagal menghapus: {e}"


def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", activity_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}")
        return []

def add_followup(activity_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        next_followup_date_str = next_followup_date.strftime("%Y-%m-%d") if isinstance(next_followup_date, datetime) else (str(next_followup_date) if next_followup_date else None)
        response = supabase.from_("followups").insert({
            "activity_id": activity_id, "marketer_username": marketer_username,
            "notes": notes, "next_action": next_action,
            "next_followup_date": next_followup_date_str, "interest_level": interest_level
        }).execute()
        if not response.data: raise Exception(response.error.message if hasattr(response, 'error') else "Unknown error")
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

# ... Fungsi config tetap sama ...
def get_app_config():
    supabase = init_connection()
    try:
        response = supabase.from_("config").select("*").execute()
        config = {item['key']: item['value'] for item in response.data}
        return config
    except Exception: return {"app_name": "Default Tracker"}

def update_app_config(new_config):
    supabase = init_connection()
    try:
        for key, value in new_config.items():
            supabase.from_("config").update({"value": value}).eq("key", key).execute()
        return True, "Konfigurasi berhasil diperbarui."
    except Exception as e: return False, f"Error: {e}"