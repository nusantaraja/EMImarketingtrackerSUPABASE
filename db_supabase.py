# db_supabase.py

import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- Inisialisasi Koneksi ---
@st.cache_resource
def init_connection() -> Client:
    """Menginisialisasi dan mengembalikan koneksi ke Supabase."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        # Menampilkan error di UI jika secrets tidak ditemukan
        st.error("Gagal terhubung ke Supabase. Pastikan Anda telah mengatur `url` dan `key` Supabase di Streamlit Secrets.")
        # Menghentikan eksekusi aplikasi jika koneksi gagal
        st.stop()
        return None

# --- Fungsi Autentikasi Profesional ---
def sign_in(email, password):
    """Melakukan sign-in menggunakan Supabase Auth."""
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        # Mengambil pesan error yang lebih spesifik dari Supabase
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, error_message

def sign_up(email, password, full_name, role):
    """Mendaftarkan pengguna baru dan membuat profilnya."""
    supabase = init_connection()
    try:
        # 1. Daftarkan user ke sistem Auth Supabase
        response = supabase.auth.sign_up({"email": email, "password": password})
        user = response.user
        
        if user:
            # 2. Jika berhasil, buat profilnya di tabel 'profiles'
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

def get_profile(user_id):
    """Mengambil profil (termasuk role dan nama lengkap) dari pengguna."""
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
    """Menghapus pengguna. Memerlukan kunci service_role untuk production."""
    return False, "Fitur Hapus Pengguna sedang dalam pengembangan demi keamanan."

# --- Fungsi CRUD Aktivitas Pemasaran ---

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
        
        data_to_insert = {
            "marketer_id": marketer_id,
            "marketer_username": marketer_username,
            "prospect_name": prospect_name, "prospect_location": prospect_location,
            "contact_person": contact_person, "contact_position": contact_position, # Jabatan ditambahkan
            "contact_phone": contact_phone, "contact_email": contact_email,
            "activity_date": activity_date_str, "activity_type": activity_type,
            "description": description, "status": status
        }
        
        response = supabase.from_("marketing_activities").insert(data_to_insert).execute()
        
        if response.data:
            return True, "Aktivitas berhasil ditambahkan.", response.data[0]['id']
        else:
            raise Exception(response.error.message if hasattr(response, 'error') and response.error else "Unknown error")
            
    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None

def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        activity_date_str = activity_date.strftime("%Y-%m-%d") if isinstance(activity_date, datetime) else str(activity_date)
        
        data_to_update = {
            "prospect_name": prospect_name, "prospect_location": prospect_location,
            "contact_person": contact_person, "contact_position": contact_position, # Jabatan ditambahkan
            "contact_phone": contact_phone, "contact_email": contact_email,
            "activity_date": activity_date_str, "activity_type": activity_type,
            "description": description, "status": status
        }
        
        response = supabase.from_("marketing_activities").update(data_to_update).eq("id", activity_id).execute()
        
        if response.data:
            return True, "Aktivitas berhasil diperbarui."
        else:
            raise Exception(response.error.message if hasattr(response, 'error') and response.error else "Unknown error")
            
    except Exception as e:
        return False, f"Gagal memperbarui: {e}"

def delete_marketing_activity(activity_id):
    supabase = init_connection()
    try:
        # Hapus follow-up terkait terlebih dahulu
        supabase.from_("followups").delete().eq("activity_id", activity_id).execute()
        # Kemudian hapus aktivitas utamanya
        response = supabase.from_("marketing_activities").delete().eq("id", activity_id).execute()
        
        if response.data:
            return True, "Aktivitas berhasil dihapus."
        else:
            raise Exception(response.error.message if hasattr(response, 'error') and response.error else "Unknown error")
            
    except Exception as e:
        return False, f"Gagal menghapus: {e}"

# --- Fungsi CRUD Follow-up ---

def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", activity_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}")
        return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        # 1. Update status aktivitas utama
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        
        # 2. Siapkan dan simpan data follow-up
        next_followup_date_str = next_followup_date.strftime("%Y-%m-%d") if next_followup_date else None
        
        data_to_insert = {
            "activity_id": activity_id,
            "marketer_id": marketer_id, # Kolom baru ditambahkan
            "marketer_username": marketer_username,
            "notes": notes, "next_action": next_action,
            "next_followup_date": next_followup_date_str, "interest_level": interest_level
        }
        
        response = supabase.from_("followups").insert(data_to_insert).execute()
        
        if response.data:
            return True, "Follow-up berhasil ditambahkan."
        else:
            raise Exception(response.error.message if hasattr(response, 'error') and response.error else "Unknown error")

    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

# --- Fungsi Konfigurasi ---
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
        return False, f"Error: {e}"

def add_prospect_research(**kwargs):
    supabase = init_connection()
    try:
        data_to_insert = {
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
            "keywords": kwargs.get("keywords", []),
            "technology_used": kwargs.get("technology_used", []),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status", "baru"),
            "source": kwargs.get("source", "manual"),
            "decision_maker": kwargs.get("decision_maker", False),
            "email_status": kwargs.get("email_status"),
            "marketer_id": kwargs.get("marketer_id"),  # Harus berupa UUID
            "marketer_username": kwargs.get("marketer_username")
        }

        response = supabase.from_("prospect_research").insert(data_to_insert).execute()
        return True, "Prospek berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"

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

def get_prospect_by_id(prospect_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").eq("id", prospect_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}")
        return None

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
            "keywords": kwargs.get("keywords", []),
            "technology_used": kwargs.get("technology_used", []),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status", "baru"),
            "source": kwargs.get("source"),
            "decision_maker": kwargs.get("decision_maker", False),
            "email_status": kwargs.get("email_status")
        }

        response = supabase.from_("prospect_research").update(data_to_update).eq("id", prospect_id).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"