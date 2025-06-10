# db_supabase.py

import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- Inisialisasi Client Supabase ---
# Fungsi ini akan dipanggil nanti, bukan saat import
@st.cache_resource
def init_connection() -> Client:
    """Initialize and return the Supabase client."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        # Kita tidak bisa menggunakan st.error() di sini.
        # Jika koneksi gagal, aplikasi tidak akan bisa berjalan.
        # Error akan muncul di log Streamlit Cloud.
        raise e

# --- Fungsi Autentikasi dan Pengguna ---

# Untuk kesederhanaan, kita tetap pakai user yang di-hardcode.
USERS = {
    "admin": {"name": "Admin Utama", "role": "superadmin"},
    "marketing_test": {"name": "Marketing Test", "role": "marketing"}
}

def login(username):
    """Simulates login by returning user info if username exists."""
    return USERS.get(username)

def get_all_users():
    """Returns the hardcoded list of users."""
    return [{"username": u, **i} for u, i in USERS.items()]

# --- Fungsi Aktivitas Pemasaran (CRUD) ---

def get_all_marketing_activities():
    """Mengambil semua aktivitas pemasaran dari Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        response = supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}")
        return []

def get_marketing_activities_by_username(username):
    """Mengambil aktivitas pemasaran berdasarkan username marketing."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        response = supabase.from_("marketing_activities").select("*").eq("marketer_username", username).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk {username}: {e}")
        return []

def get_activity_by_id(activity_id):
    """Mengambil satu aktivitas berdasarkan ID-nya."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        response = supabase.from_("marketing_activities").select("*").eq("id", activity_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}")
        return None

def add_marketing_activity(marketer_username, prospect_name, prospect_location, contact_person,
                           contact_position, contact_phone, contact_email, activity_date,
                           activity_type, description, status):
    """Menambahkan aktivitas pemasaran baru ke Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        if isinstance(activity_date, datetime):
            activity_date_str = activity_date.strftime("%Y-%m-%d")
        else:
            activity_date_str = str(activity_date)

        response = supabase.from_("marketing_activities").insert({
            "marketer_username": marketer_username,
            "prospect_name": prospect_name,
            "prospect_location": prospect_location,
            "contact_person": contact_person,
            "contact_position": contact_position,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "activity_date": activity_date_str,
            "activity_type": activity_type,
            "description": description,
            "status": status
        }).execute()

        if response.data:
            return True, "Aktivitas berhasil ditambahkan.", response.data[0]['id']
        else:
            if hasattr(response, 'error') and response.error:
                return False, f"Gagal menambahkan aktivitas: {response.error.message}", None
            return False, "Gagal menambahkan aktivitas.", None

    except Exception as e:
        return False, f"Terjadi error: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person,
                          contact_position, contact_phone, contact_email, activity_date,
                          activity_type, description, status):
    """Mengedit aktivitas pemasaran yang ada di Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        if isinstance(activity_date, datetime):
            activity_date_str = activity_date.strftime("%Y-%m-%d")
        else:
            activity_date_str = str(activity_date)

        response = supabase.from_("marketing_activities").update({
            "prospect_name": prospect_name,
            "prospect_location": prospect_location,
            "contact_person": contact_person,
            "contact_position": contact_position,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "activity_date": activity_date_str,
            "activity_type": activity_type,
            "description": description,
            "status": status
        }).eq("id", activity_id).execute()

        if response.data:
            return True, "Aktivitas berhasil diperbarui."
        else:
            if hasattr(response, 'error') and response.error:
                return False, f"Gagal memperbarui aktivitas: {response.error.message}"
            return False, "Gagal memperbarui aktivitas."
    except Exception as e:
        return False, f"Terjadi error: {e}"

def delete_marketing_activity(activity_id):
    """Menghapus aktivitas pemasaran dan follow-up terkait dari Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        supabase.from_("followups").delete().eq("activity_id", activity_id).execute()
        response = supabase.from_("marketing_activities").delete().eq("id", activity_id).execute()

        if response.data:
            return True, "Aktivitas berhasil dihapus."
        else:
             if hasattr(response, 'error') and response.error:
                return False, f"Gagal menghapus aktivitas: {response.error.message}"
             return False, "Gagal menghapus aktivitas."
    except Exception as e:
        return False, f"Terjadi error: {e}"

# --- Fungsi Follow-up (CRUD) ---

def get_followups_by_activity_id(activity_id):
    """Mengambil semua follow-up untuk sebuah aktivitas."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", activity_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}")
        return []

def add_followup(activity_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    """Menambahkan follow-up baru dan mengupdate status aktivitas utama."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()

        if isinstance(next_followup_date, datetime):
            next_followup_date_str = next_followup_date.strftime("%Y-%m-%d")
        else:
            next_followup_date_str = str(next_followup_date) if next_followup_date else None

        response = supabase.from_("followups").insert({
            "activity_id": activity_id,
            "marketer_username": marketer_username,
            "notes": notes,
            "next_action": next_action,
            "next_followup_date": next_followup_date_str,
            "interest_level": interest_level
        }).execute()

        if response.data:
            return True, "Follow-up berhasil ditambahkan."
        else:
            if hasattr(response, 'error') and response.error:
                return False, f"Gagal menambahkan follow-up: {response.error.message}"
            return False, "Gagal menambahkan follow-up."
    except Exception as e:
        return False, f"Terjadi error: {e}"

# --- Fungsi Konfigurasi ---

def get_app_config():
    """Mengambil konfigurasi aplikasi dari Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        response = supabase.from_("config").select("*").execute()
        config = {item['key']: item['value'] for item in response.data}
        return config
    except Exception as e:
        st.error(f"Error mengambil konfigurasi: {e}")
        return {"app_name": "Default Tracker"}

def update_app_config(new_config):
    """Memperbarui konfigurasi di Supabase."""
    supabase = init_connection() # Panggil koneksi di dalam fungsi
    try:
        for key, value in new_config.items():
            supabase.from_("config").update({"value": value}).eq("key", key).execute()
        return True, "Konfigurasi berhasil diperbarui."
    except Exception as e:
        return False, f"Terjadi error: {e}"