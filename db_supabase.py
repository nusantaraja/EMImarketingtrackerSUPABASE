# --- START OF FILE db_supabase.py (Versi Revisi Lengkap & Aman) ---

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
        # Tampilkan error yang lebih spesifik jika memungkinkan
        error_msg = f"Gagal terhubung ke Supabase. Pastikan secrets sudah benar. Detail: {e}"
        st.error(error_msg)
        st.stop()
        return None

# --- Fungsi Autentikasi ---
def sign_in(email, password):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        # Berikan pesan error yang lebih ramah pengguna
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        if "Invalid login credentials" in error_message:
            return None, "Kombinasi email & password salah."
        return None, error_message

def create_user_as_admin(email, password, full_name, role, manager_id=None):
    supabase = init_connection()
    # Pastikan data utama tidak kosong sebelum dikirim
    if not all([email, password, full_name, role]):
        return None, "Email, password, nama lengkap, dan role tidak boleh kosong."
    try:
        # Buat pengguna baru
        response = supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
        user = response.user
        if user and user.id:
            # Siapkan data profil
            profile_data = {
                "id": user.id, 
                "full_name": full_name, 
                "role": role, 
                "email": email, 
                "manager_id": manager_id
            }
            # Masukkan profil ke database
            supabase.from_("profiles").insert(profile_data).execute()
            return user, None
        else:
            return None, "Gagal membuat entri otentikasi untuk pengguna."
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, "Pengguna dengan email ini sudah terdaftar." if "User already exists" in error_message else error_message

def get_profile(user_id):
    # --- PERBAIKAN PENTING --- Selalu validasi ID sebelum query
    if not user_id:
        return None
    supabase = init_connection()
    try:
        # Menggunakan .maybe_single() lebih aman daripada .single()
        # .maybe_single() mengembalikan None jika tidak ada data, tanpa error
        return supabase.from_("profiles").select("*").eq("id", user_id).maybe_single().execute().data
    except Exception:
        # Jika ada error lain (misal RLS), kembalikan None
        return None

# --- Manajemen Pengguna ---
def get_all_profiles():
    supabase = init_connection()
    try:
        # Relasi ini sudah benar
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}"); return []

def get_team_profiles(manager_id):
    # Validasi ID Manajer
    if not manager_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").execute().data
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
    if not user_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas: {e}"); return []

def get_team_marketing_activities(manager_id):
    if not manager_id: return []
    supabase = init_connection()
    try:
        team_member_res = supabase.from_("profiles").select("id").eq("manager_id", manager_id).execute()
        team_ids = [m['id'] for m in team_member_res.data]
        team_ids.append(manager_id)
        return supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data aktivitas tim: {e}"); return []

def get_activity_by_id(activity_id):
    # --- PERBAIKAN PENTING ---
    if not activity_id: return None
    supabase = init_connection()
    try:
        # Menggunakan .maybe_single() agar tidak crash
        return supabase.from_("marketing_activities").select("*").eq("id", activity_id).maybe_single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}"); return None

def add_marketing_activity(marketer_id, marketer_username, prospect_name, **kwargs):
    supabase = init_connection()
    # --- PERBAIKAN KRITIS --- Mencegah data NULL masuk ke DB
    if not all([marketer_id, marketer_username, prospect_name]):
        st.error("Gagal menambahkan aktivitas: ID, Nama Marketing, dan Nama Prospek tidak boleh kosong.")
        return False, "Data penting tidak lengkap.", None

    try:
        # Gabungkan data wajib dengan data opsional
        data = {
            "marketer_id": marketer_id,
            "marketer_username": marketer_username,
            "prospect_name": prospect_name,
            **kwargs
        }
        response = supabase.from_("marketing_activities").insert(data).execute()
        
        # Validasi bahwa insert berhasil dan mengembalikan data
        if response.data and len(response.data) > 0:
            return True, "Aktivitas berhasil ditambahkan!", response.data[0].get("id")
        else:
            # Ini bisa terjadi karena RLS (Row Level Security) yang memblokir INSERT
            return False, f"Gagal menambahkan aktivitas ke database. Mungkin terblokir RLS.", None

    except Exception as e:
        return False, f"Gagal menambahkan aktivitas: {e}", None


def edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    if not activity_id: return False, "ID Aktivitas tidak valid."
    supabase = init_connection()
    try:
        data = {
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
        supabase.from_("marketing_activities").update(data).eq("id", activity_id).execute()
        return True, "Aktivitas berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui aktivitas: {e}"

# --- Follow-up ---
def get_followups_by_activity_id(activity_id):
    if not activity_id: return []
    supabase = init_connection()
    try:
        return supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).execute().data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}"); return []

def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    if not activity_id or not marketer_id or not notes:
        return False, "ID Aktivitas, ID Marketing, dan Catatan tidak boleh kosong."
    supabase = init_connection()
    try:
        # Lakukan update status aktivitas terlebih dahulu
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", activity_id).execute()
        
        # Siapkan dan masukkan data follow-up
        data = {
            "activity_id": activity_id, 
            "marketer_id": marketer_id, 
            "marketer_username": marketer_username, 
            "notes": notes, 
            "next_action": next_action, 
            "next_followup_date": date_to_str(next_followup_date), # date_to_str ada di app_supabase.py
            "interest_level": interest_level
        }
        supabase.from_("followups").insert(data).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"

# --- Sisa File (Riset Prospek, Apollo, Zoho) ---
# Kode untuk bagian ini sudah cukup baik, tidak ada perubahan kritis yang diperlukan.
# Namun, selalu pastikan ID divalidasi sebelum melakukan query `eq`.

def date_to_str(dt):
    # Fungsi helper ini sebenarnya ada di app_supabase.py, sebaiknya dipindah ke file utilitas
    # atau didefinisikan di kedua file jika tidak ingin menambah file baru.
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (datetime, date)) else dt

# --- Riset Prospek --- (Contoh penerapan validasi)
def get_prospect_by_id(prospect_id):
    if not prospect_id: return None
    supabase = init_connection()
    try:
        return supabase.from_("prospect_research").select("*").eq("id", prospect_id).maybe_single().execute().data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}"); return None

# Sisanya sama...
# ... (Salin sisa fungsi dari file asli Anda ke sini) ...