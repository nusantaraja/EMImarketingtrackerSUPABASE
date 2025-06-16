# --- START OF COMBINED APP WITH FIXES ---

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from supabase import create_client, Client
import pytz
import requests
from urllib.parse import urlencode
import streamlit.components.v1 as components

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

# --- Inisialisasi Koneksi Supabase ---
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

# --- Fungsi Autentikasi & Manajemen Pengguna (FIXED) ---
def sign_in(email, password):
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        error_message = str(e.args[0]['message']) if e.args and isinstance(e.args[0], dict) else str(e)
        return None, error_message

def create_user_as_admin(email, password, full_name, role, manager_id=None):
    supabase = init_connection()
    try:
        # Buat user di auth system
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        
        if auth_response.user:
            # Validasi role dan manager_id
            if role == "marketing" and not manager_id:
                return None, "Marketing harus memiliki manager"
            if role in ["superadmin", "manager"] and manager_id:
                return None, f"{role.capitalize()} tidak boleh memiliki manager"
            
            # Buat profil pengguna
            profile_data = {
                "id": auth_response.user.id,
                "full_name": full_name,
                "role": role,
                "email": email,
                "manager_id": manager_id if role == "marketing" else None
            }
            
            # Insert ke tabel profiles
            supabase.table("profiles").insert(profile_data).execute()
            return auth_response.user, None
        return None, "Gagal membuat user"
    except Exception as e:
        error_msg = str(e)
        if "User already exists" in error_msg:
            return None, "Email sudah terdaftar"
        elif "duplicate key" in error_msg:
            return None, "User sudah memiliki profil"
        else:
            return None, f"Error: {error_msg}"

def get_profile(user_id):
    supabase = init_connection()
    try:
        return supabase.table("profiles").select("*").eq("id", user_id).single().execute().data
    except Exception: return None

def get_all_profiles():
    supabase = init_connection()
    try:
        return supabase.table("profiles").select("*, manager:manager_id(full_name)").execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data pengguna: {e}"); return []

def get_team_profiles(manager_id):
    supabase = init_connection()
    try:
        return supabase.table("profiles").select("*, manager:manager_id(full_name)").or_(f"id.eq.{manager_id},manager_id.eq.{manager_id}").execute().data
    except Exception as e:
        st.error(f"Gagal mengambil data tim: {e}"); return []

def get_all_managers():
    supabase = init_connection()
    try:
        return supabase.table("profiles").select("id, full_name").eq("role", "manager").execute().data
    except Exception: return []

# --- Fungsi Helper Lainnya ---
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    if not iso_string: return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        wib_tz = pytz.timezone("Asia/Jakarta")
        return dt_utc.astimezone(wib_tz).strftime(format_str)
    except Exception: return iso_string

def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

def str_to_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

# --- Halaman Aplikasi ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user, error = sign_in(email, password)
            if user:
                profile = get_profile(user.id)
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.profile = profile
                st.success("Login Berhasil!")
                st.rerun()
            else: st.error(f"Login Gagal: {error}")

def show_sidebar():
    with st.sidebar:
        profile = st.session_state.profile
        st.title("Menu Navigasi")
        st.write(f"Selamat datang, **{profile.get('full_name', 'User')}**!")
        st.write(f"Role: **{profile.get('role', 'N/A').capitalize()}**")
        st.divider()
        
        # Menu berdasarkan role
        menu_items = ["Dashboard", "Aktivitas Pemasaran", "Riset Prospek"]
        if profile.get('role') in ['superadmin', 'manager']: 
            menu_items.append("Manajemen Pengguna")
        if profile.get('role') == 'superadmin': 
            menu_items.append("Pengaturan")
        
        page = st.radio("Pilih Halaman:", menu_items, key="page_selection")
        st.divider()
        
        if st.button("Logout"):
            for key in list(st.session_state.keys()): 
                del st.session_state[key]
            st.rerun()
        return page

def page_user_management():
    st.title("Manajemen Pengguna")
    profile = st.session_state.profile
    user = st.session_state.user
    
    # Cek akses
    if profile.get('role') not in ['superadmin', 'manager']: 
        st.error("Akses ditolak: Hanya untuk Superadmin/Manager")
        return

    # Dapatkan data berdasarkan role
    if profile.get('role') == 'superadmin':
        profiles_data = get_all_profiles()
        manager_options = get_all_managers()
    else:  # manager
        profiles_data = get_team_profiles(user.id)
        manager_options = [{"id": user.id, "full_name": profile.get('full_name')}]

    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])
    
    with tab1:
        st.subheader("Daftar Pengguna")
        if profiles_data:
            df = pd.DataFrame(profiles_data)
            
            # Format untuk tampilan yang lebih baik
            df['Role'] = df['role'].str.capitalize()
            df['Manajer'] = df['manager'].apply(
                lambda x: x['full_name'] if isinstance(x, dict) else 'N/A'
            )
            
            cols_to_show = ['full_name', 'email', 'Role', 'Manajer']
            st.dataframe(
                df[cols_to_show].rename(columns={
                    'full_name': 'Nama',
                    'email': 'Email'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Belum ada pengguna terdaftar.")

    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Nama Lengkap*", placeholder="Nama lengkap pengguna")
                email = st.text_input("Email*", placeholder="email@domain.com")
                password = st.text_input("Password*", type="password")
            
            with col2:
                # Sesuaikan opsi role berdasarkan hak akses
                if profile.get('role') == 'superadmin':
                    role = st.selectbox("Role*", ["manager", "marketing"])
                else:
                    role = "marketing"
                    st.info("Anda hanya bisa menambahkan marketing")
                
                # Field manager hanya untuk marketing
                manager_id = None
                if role == "marketing":
                    if manager_options:
                        manager_id = st.selectbox(
                            "Manajer*",
                            options=[m['id'] for m in manager_options],
                            format_func=lambda x: next(
                                m['full_name'] for m in manager_options 
                                if m['id'] == x
                            )
                        )
                    else:
                        st.warning("Belum ada manajer tersedia")

            if st.form_submit_button("Daftarkan Pengguna"):
                if not all([full_name, email, password]):
                    st.error("Harap isi semua field wajib (*)")
                elif role == "marketing" and not manager_id:
                    st.error("Harap pilih manajer untuk marketing")
                else:
                    with st.spinner("Mendaftarkan pengguna..."):
                        new_user, error = create_user_as_admin(
                            email=email,
                            password=password,
                            full_name=full_name,
                            role=role,
                            manager_id=manager_id
                        )
                        
                        if new_user:
                            st.success(f"Berhasil mendaftarkan {full_name} sebagai {role}")
                            st.rerun()
                        else:
                            st.error(f"Gagal: {error}")

def main():
    if "logged_in" not in st.session_state: 
        st.session_state.logged_in = False
    
    if not st.session_state.get("logged_in"):
        show_login_page()
    else:
        page = show_sidebar()
        if page == "Manajemen Pengguna":
            page_user_management()
        else:
            st.title("Halaman Lainnya")
            st.write("Implementasi halaman lainnya bisa ditambahkan di sini")

if __name__ == "__main__":
    main()

# --- END OF COMBINED APP WITH FIXES ---