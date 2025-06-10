# db_supabase.py

import streamlit as st
from supabase import create_client, Client
from datetime import datetime

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase. Pastikan URL dan KEY di Streamlit Secrets sudah benar. Error: {e}")
        return None

def sign_in(email, password):
    supabase = init_connection()
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        profile = get_user_profile(res.user.id)
        if profile:
            user_data = {'id': res.user.id, 'email': res.user.email, **profile}
            return True, "Login berhasil!", user_data
        else:
            return False, "Login berhasil, tapi profil tidak ditemukan.", None
    except Exception as e:
        return False, f"Gagal login: {e}", None

def sign_up(email, password, full_name, role='marketing', manager_id=None):
    supabase = init_connection()
    try:
        res = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {'full_name': full_name, 'role': role, 'manager_id': manager_id}}})
        return True, "Pengguna berhasil didaftarkan. Silakan cek email untuk verifikasi.", res.user
    except Exception as e:
        return False, f"Gagal mendaftarkan pengguna: {e}", None

def get_user_profile(user_id):
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('*').eq('id', user_id).single().execute()
        return res.data
    except Exception: return None

def get_all_users_with_profile():
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('*').execute()
        return res.data
    except Exception as e:
        st.error(f"Gagal mengambil daftar pengguna: {e}"); return []

def get_users_by_role(role):
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('id, full_name').eq('role', role).execute()
        return res.data
    except Exception as e:
        st.error(f"Gagal mengambil pengguna dengan peran {role}: {e}"); return []

def update_user_profile(user_id, full_name, role, manager_id):
    supabase = init_connection()
    try:
        supabase.from_('profiles').update({'full_name': full_name, 'role': role, 'manager_id': manager_id}).eq('id', user_id).execute()
        return True, "Profil pengguna berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui profil: {e}"

def delete_user(user_id):
    supabase_admin = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        return True, "Pengguna berhasil dihapus."
    except Exception as e:
        return False, f"Gagal menghapus pengguna: {e}"

def get_team_member_ids(manager_id):
    supabase = init_connection()
    try:
        res = supabase.from_('profiles').select('id').eq('manager_id', manager_id).execute()
        return [item['id'] for item in res.data]
    except Exception as e:
        st.error(f"Gagal mengambil anggota tim: {e}"); return []

def get_all_marketing_activities():
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*, profiles(full_name)").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil semua data aktivitas: {e}"); return []

def get_activities_for_manager(manager_id):
    supabase = init_connection()
    team_ids = get_team_member_ids(manager_id)
    if not team_ids: return []
    try:
        response = supabase.from_("marketing_activities").select("*, profiles(full_name)").in_("marketer_id", team_ids).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas tim: {e}"); return []

def get_marketing_activities_by_user(user_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*, profiles(full_name)").eq("marketer_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk pengguna: {e}"); return []

def add_marketing_activity(marketer_id, data_dict):
    supabase = init_connection()
    try:
        data_to_insert = {"marketer_id": marketer_id, **data_dict}
        response = supabase.from_("marketing_activities").insert(data_to_insert).execute()
        if response.data:
            return True, "Aktivitas berhasil ditambahkan.", response.data[0]['id']
        else: return False, f"Gagal menambahkan aktivitas: {getattr(response, 'error', 'Unknown error')}", None
    except Exception as e:
        return False, f"Terjadi error: {e}", None

def edit_marketing_activity(activity_id, data_to_update):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").update(data_to_update).eq("id", activity_id).execute()
        if response.data: return True, "Aktivitas berhasil diperbarui."
        else: return False, f"Gagal memperbarui aktivitas: {getattr(response, 'error', 'Unknown error')}"
    except Exception as e:
        return False, f"Terjadi error: {e}"

def delete_marketing_activity(activity_id):
    supabase = init_connection()
    try:
        supabase.from_("followups").delete().eq("activity_id", activity_id).execute()
        response = supabase.from_("marketing_activities").delete().eq("id", activity_id).execute()
        if response.data: return True, "Aktivitas berhasil dihapus."
        return False, f"Gagal menghapus aktivitas: {getattr(response, 'error', 'Unknown error')}"
    except Exception as e:
        return False, f"Terjadi error: {e}"

def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", activity_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}"); return []

def add_followup(activity_id, data_dict):
    supabase = init_connection()
    try:
        supabase.from_("marketing_activities").update({"status": data_dict["status_update"]}).eq("id", activity_id).execute()
        data_to_insert = {"activity_id": activity_id, **data_dict}
        response = supabase.from_("followups").insert(data_to_insert).execute()
        if response.data: return True, "Follow-up berhasil ditambahkan."
        else: return False, f"Gagal menambahkan follow-up: {getattr(response, 'error', 'Unknown error')}"
    except Exception as e:
        return False, f"Terjadi error: {e}"