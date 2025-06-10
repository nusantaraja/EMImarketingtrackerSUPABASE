# db_supabase.py

import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- Inisialisasi Client Supabase ---
@st.cache_resource
def init_connection() -> Client:
    """Initialize and return the Supabase client."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase. Pastikan URL dan KEY di Streamlit Secrets sudah benar. Error: {e}")
        return None

# --- Fungsi Autentikasi dan Pengguna ---
# - DIPERBARUI: Menggunakan Supabase Auth sepenuhnya

def sign_up(email, password, full_name, role='marketing', manager_id=None):
    """Mendaftarkan pengguna baru via Supabase Auth."""
    supabase = init_connection()
    try:
        # Mendaftarkan user di sistem Auth, sambil menyelipkan data tambahan (metadata)
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    'full_name': full_name,
                    'role': role,
                    'manager_id': manager_id
                }
            }
        })
        # Fungsi trigger di database akan otomatis membuat profilnya
        return True, "Pengguna berhasil didaftarkan. Silakan cek email untuk verifikasi.", res.user
    except Exception as e:
        return False, f"Gagal mendaftarkan pengguna: {e}", None

def sign_in(email, password):
    """Login pengguna via Supabase Auth."""
    supabase = init_connection()
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        # Setelah login, ambil profilnya untuk mendapatkan role
        profile = get_user_profile(res.user.id)
        if profile:
            # Gabungkan info dari auth dan profile
            user_data = {
                'id': res.user.id,
                'email': res.user.email,
                'full_name': profile.get('full_name'),
                'role': profile.get('role')
            }
            return True, "Login berhasil!", user_data
        else:
            return False, "Login berhasil, tapi profil tidak ditemukan.", None
    except Exception as e:
        return False, f"Gagal login: {e}", None

def get_user_profile(user_id):
    """Mengambil data profil (termasuk role) dari tabel profiles."""
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('*').eq('id', user_id).single().execute()
        return res.data
    except Exception:
        return None

def get_all_users_with_profile():
    """Mengambil semua profil pengguna untuk ditampilkan di manajemen pengguna."""
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('*').execute()
        return res.data
    except Exception as e:
        st.error(f"Gagal mengambil daftar pengguna: {e}")
        return []

def get_users_by_role(role):
    """Mengambil pengguna berdasarkan peran, contoh: semua manajer."""
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('id, full_name').eq('role', role).execute()
        return res.data
    except Exception as e:
        st.error(f"Gagal mengambil pengguna dengan peran {role}: {e}")
        return []

def update_user_profile(user_id, full_name, role, manager_id):
    """Memperbarui profil pengguna oleh Admin."""
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').update({
            'full_name': full_name,
            'role': role,
            'manager_id': manager_id
        }).eq('id', user_id).execute()
        return True, "Profil pengguna berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui profil: {e}"

def delete_user(user_id):
    """Menghapus pengguna dari sistem (hanya bisa dilakukan oleh Superadmin di backend)."""
    supabase_admin = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    try:
        # Menghapus dari Supabase Auth akan otomatis menghapus dari profiles berkat trigger ON DELETE CASCADE
        res = supabase_admin.auth.admin.delete_user(user_id)
        return True, "Pengguna berhasil dihapus."
    except Exception as e:
        return False, f"Gagal menghapus pengguna: {e}"

# --- Fungsi Logika Tim (BARU) ---

def get_team_member_ids(manager_id):
    """Mengambil daftar ID dari anggota tim seorang manajer."""
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('id').eq('manager_id', manager_id).execute()
        return [item['id'] for item in res.data]
    except Exception as e:
        st.error(f"Gegal mengambil anggota tim: {e}")
        return []

# --- Fungsi Aktivitas Pemasaran (CRUD) - DIPERBARUI ---

def get_all_marketing_activities():
    """Untuk Superadmin: Mengambil semua aktivitas pemasaran."""
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil semua data aktivitas: {e}")
        return []

def get_activities_for_manager(manager_id):
    """Untuk Manager: Mengambil aktivitas dari timnya."""
    supabase = init_connection()
    team_ids = get_team_member_ids(manager_id)
    if not team_ids:
        return []
    try:
        response = supabase.from_("marketing_activities").select("*").in_("marketer_id", team_ids).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas tim: {e}")
        return []

def get_marketing_activities_by_user(user_id):
    """Untuk Marketing: Mengambil aktivitas miliknya sendiri."""
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("marketer_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk {user_id}: {e}")
        return []

def add_marketing_activity(marketer_id, prospect_name, **kwargs):
    """Menambahkan aktivitas baru."""
    supabase = init_connection()
    try:
        data_to_insert = {"marketer_id": marketer_id, "prospect_name": prospect_name, **kwargs}
        response = supabase.from_("marketing_activities").insert(data_to_insert).execute()
        if response.data:
            return True, "Aktivitas berhasil ditambahkan.", response.data[0]['id']
        else:
            return False, f"Gagal: {getattr(response, 'error', 'Unknown error')}", None
    except Exception as e:
        return False, f"Terjadi error: {e}", None

def edit_marketing_activity(activity_id, data_to_update):
    """Mengedit aktivitas yang ada."""
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").update(data_to_update).eq("id", activity_id).execute()
        if response.data:
            return True, "Aktivitas berhasil diperbarui."
        else:
            return False, f"Gagal: {getattr(response, 'error', 'Unknown error')}"
    except Exception as e:
        return False, f"Terjadi error: {e}"

# Fungsi lain seperti delete_marketing_activity, get_followups, add_followup tetap sama secara konsep
# Cukup pastikan mereka menggunakan `init_connection()` di awal.

def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    # ... implementasi sama seperti sebelumnya ...
    pass
# ... dan seterusnya ...