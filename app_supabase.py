# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db  # Import file database baru kita

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="EMI Marketing Tracker",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Halaman Login ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            success, message, user = db.sign_in(email, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# --- Sidebar ---
def show_sidebar():
    with st.sidebar:
        st.title("Menu Navigasi")
        user = st.session_state.user
        st.write(f"Selamat datang, **{user.get('full_name', 'User')}**!")
        st.write(f"Role: **{user.get('role', 'N/A').capitalize()}**")
        st.divider()

        # Menu dinamis berdasarkan peran
        if user.get('role') == 'superadmin':
            menu_options = ["Dashboard", "Aktivitas Pemasaran", "Manajemen Pengguna"]
        elif user.get('role') == 'manager':
            menu_options = ["Dashboard", "Aktivitas Tim"]
        else: # Marketing
            menu_options = ["Dashboard", "Aktivitas Saya"]

        menu = st.radio("Pilih Halaman:", menu_options)

        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    return menu

# --- Halaman Dashboard ---
def show_dashboard():
    user = st.session_state.user
    role = user.get('role')
    st.title(f"Dashboard {role.capitalize()}")

    activities = []
    if role == 'superadmin':
        activities = db.get_all_marketing_activities()
    elif role == 'manager':
        activities = db.get_activities_for_manager(user['id'])
    else: # Marketing
        activities = db.get_marketing_activities_by_user(user['id'])

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    # Logika untuk menampilkan metrik dan grafik (bisa disesuaikan)
    df = pd.DataFrame(activities)
    st.metric("Total Aktivitas", len(df))
    st.dataframe(df)

# --- Halaman Manajemen Pengguna (Hanya Superadmin) ---
def show_user_management_page():
    st.title("Manajemen Pengguna")
    
    users = db.get_all_users_with_profile()
    if users:
        st.dataframe(users)

    tab1, tab2 = st.tabs(["Tambah Pengguna Baru", "Edit Pengguna"])

    with tab1:
        st.subheader("Form Tambah Pengguna")
        with st.form("add_user_form"):
            full_name = st.text_input("Nama Lengkap")
            email = st.text_input("Email")
            password = st.text_input("Password Sementara", type="password")
            role = st.selectbox("Peran (Role)", ["marketing", "manager"])
            
            manager_id = None
            if role == 'marketing':
                managers = db.get_users_by_role('manager')
                manager_options = {mgr['full_name']: mgr['id'] for mgr in managers}
                selected_manager_name = st.selectbox("Pilih Manajer", list(manager_options.keys()))
                if selected_manager_name:
                    manager_id = manager_options[selected_manager_name]
            
            submitted = st.form_submit_button("Daftarkan Pengguna")
            if submitted:
                success, message, new_user = db.sign_up(email, password, full_name, role, manager_id)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    with tab2:
        st.subheader("Edit atau Hapus Pengguna")
        if not users:
            st.info("Tidak ada pengguna untuk diedit.")
            return

        user_options = {f"{u['full_name']} ({u['email']})": u['id'] for u in users if u['id'] != st.session_state.user['id']}
        selected_user_str = st.selectbox("Pilih Pengguna", list(user_options.keys()))
        
        if selected_user_str:
            user_id_to_edit = user_options[selected_user_str]
            user_to_edit = next((u for u in users if u['id'] == user_id_to_edit), None)

            if user_to_edit:
                with st.form("edit_user_form"):
                    st.write(f"Mengedit: **{user_to_edit['full_name']}**")
                    new_full_name = st.text_input("Nama Lengkap", value=user_to_edit['full_name'])
                    new_role = st.selectbox("Peran (Role)", ["marketing", "manager"], index=["marketing", "manager"].index(user_to_edit['role']))
                    
                    new_manager_id = user_to_edit.get('manager_id')
                    if new_role == 'marketing':
                        managers = db.get_users_by_role('manager')
                        manager_names = [mgr['full_name'] for mgr in managers]
                        current_manager_index = 0
                        # ... Logika untuk pre-select manajer saat ini ...

                        selected_manager_name = st.selectbox("Pilih Manajer", manager_names, index=current_manager_index)
                        if selected_manager_name:
                            new_manager_id = next((m['id'] for m in managers if m['full_name'] == selected_manager_name), None)
                    else:
                        new_manager_id = None # Manager tidak punya manager

                    edit_submitted = st.form_submit_button("Simpan Perubahan")
                    if edit_submitted:
                        success, message = db.update_user_profile(user_id_to_edit, new_full_name, new_role, new_manager_id)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                if st.button("Hapus Pengguna Ini", type="primary"):
                    success, message = db.delete_user(user_id_to_edit)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

# --- Logika Aplikasi Utama ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login_page()
else:
    menu = show_sidebar()
    if menu == "Dashboard":
        show_dashboard()
    elif menu in ["Aktivitas Pemasaran", "Aktivitas Tim", "Aktivitas Saya"]:
        # Di sini Anda bisa membuat halaman manajemen aktivitas seperti sebelumnya
        st.title(menu)
        st.info("Halaman untuk menambah, mengedit, dan melihat detail aktivitas akan ada di sini.")
    elif menu == "Manajemen Pengguna":
        show_user_management_page()