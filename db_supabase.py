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
        st.error(f"Gagal mengambil data pengguna: {e}")
        return []


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
        response = supabase.from_("marketing_activities").select("*").eq("marketer_id", str(user_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data aktivitas untuk pengguna: {e}")
        return []


def get_activity_by_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("marketing_activities").select("*").eq("id", str(activity_id)).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail aktivitas: {e}")
        return None


def add_marketing_activity(marketer_id, marketer_username, prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status):
    supabase = init_connection()
    try:
        data_to_insert = {
            "marketer_id": str(marketer_id),
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

# --- Follow-up CRUD ---
def get_followups_by_activity_id(activity_id):
    supabase = init_connection()
    try:
        response = supabase.from_("followups").select("*").eq("activity_id", str(activity_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data follow-up: {e}")
        return []


def add_followup(activity_id, marketer_id, marketer_username, notes, next_action, next_followup_date, interest_level, status_update):
    supabase = init_connection()
    try:
        # Update status utama
        supabase.from_("marketing_activities").update({"status": status_update}).eq("id", str(activity_id)).execute()

        # Format tanggal follow-up
        next_followup_date_str = next_followup_date.strftime("%Y-%m-%d") if next_followup_date else None

        data_to_insert = {
            "activity_id": str(activity_id),
            "marketer_id": marketer_id,
            "marketer_username": marketer_username,
            "notes": notes,
            "next_action": next_action,
            "next_followup_date": next_followup_date_str,
            "interest_level": interest_level
        }

        response = supabase.from_("followups").insert(data_to_insert).execute()
        return True, "Follow-up berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan follow-up: {e}"