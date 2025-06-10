# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db

st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide", initial_sidebar_state="expanded")

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
            else: st.error(message)

def show_sidebar():
    with st.sidebar:
        user = st.session_state.user
        st.title(f"Halo, {user.get('full_name', 'User')}!")
        st.write(f"Role: **{user.get('role', 'N/A').capitalize()}**")
        st.divider()
        menu_options = ["Dashboard"]
        if user.get('role') == 'superadmin': menu_options.extend(["Aktivitas Pemasaran", "Manajemen Pengguna"])
        elif user.get('role') == 'manager': menu_options.append("Aktivitas Tim")
        else: menu_options.append("Aktivitas Saya")
        menu = st.radio("Pilih Halaman:", menu_options, key="menu_selection")
        st.divider()
        if st.button("Logout"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
    return menu

def show_dashboard():
    user = st.session_state.user
    role = user.get('role')
    st.title(f"Dashboard {role.capitalize()}")
    activities = []
    if role == 'superadmin': activities = db.get_all_marketing_activities()
    elif role == 'manager': activities = db.get_activities_for_manager(user['id'])
    else: activities = db.get_marketing_activities_by_user(user['id'])
    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return
    df = pd.DataFrame(activities)
    st.subheader("Statistik Utama")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    total_berhasil = 0
    if 'status' in df.columns and not df[df['status'] == 'berhasil'].empty:
        total_berhasil = len(df[df['status'] == 'berhasil'])
    col3.metric("Prospek Berhasil", total_berhasil)
    st.divider()
    st.subheader("Visualisasi Data")
    fig_col1, fig_col2 = st.columns(2)
    with fig_col1:
        st.write("**Distribusi Status Prospek**")
        status_counts = df['status'].value_counts()
        fig_status = px.pie(status_counts, values=status_counts.values, names=status_counts.index, hole=0.3)
        st.plotly_chart(fig_status, use_container_width=True)
    with fig_col2:
        if role in ['superadmin', 'manager']:
            st.write("**Aktivitas per Anggota Tim**")
            df['full_name'] = df['profiles'].apply(lambda x: x['full_name'] if x else 'N/A')
            activity_by_user = df['full_name'].value_counts()
            fig_by_user = px.bar(activity_by_user, x=activity_by_user.index, y=activity_by_user.values, labels={'x': 'Anggota Tim', 'y': 'Jumlah Aktivitas'})
            st.plotly_chart(fig_by_user, use_container_width=True)
        else:
            st.write("**Distribusi Jenis Aktivitas**")
            type_counts = df['activity_type'].value_counts()
            if not type_counts.empty:
                fig_type = px.pie(type_counts, values=type_counts.values, names=type_counts.index, hole=0.3)
                st.plotly_chart(fig_type, use_container_width=True)
            else: st.info("Belum ada jenis aktivitas yang tercatat.")

def show_activity_management_page():
    user = st.session_state.user
    role = user.get('role')
    st.title("Manajemen Aktivitas Pemasaran")
    activities = []
    if role == 'superadmin': activities = db.get_all_marketing_activities()
    elif role == 'manager': activities = db.get_activities_for_manager(user['id'])
    else: activities = db.get_marketing_activities_by_user(user['id'])
    if not activities:
        st.info("Belum ada aktivitas. Silakan tambahkan aktivitas baru di bawah.")
    else:
        df = pd.DataFrame(activities)
        df['marketer_name'] = df['profiles'].apply(lambda x: x['full_name'] if x else 'N/A')
        display_cols = ['created_at', 'marketer_name', 'prospect_name', 'activity_date', 'activity_type', 'status']
        st.dataframe(df[display_cols], use_container_width=True)
    st.divider()
    activity_to_edit = None
    if activities:
        activity_options = {f"{act['id']} - {act['prospect_name']}": act for act in activities}
        options_list = ["Tambah Aktivitas Baru"] + list(activity_options.keys())
        selected_option = st.selectbox("Pilih untuk mengedit aktivitas atau menambah baru:", options_list)
        if selected_option != "Tambah Aktivitas Baru":
            activity_to_edit = activity_options[selected_option]
    with st.form(key="activity_form"):
        st.subheader("Edit Aktivitas" if activity_to_edit else "Tambah Aktivitas Baru")
        col1, col2 = st.columns(2)
        with col1:
            prospect_name = st.text_input("Nama Prospek*", value=activity_to_edit['prospect_name'] if activity_to_edit else "")
            prospect_location = st.text_input("Lokasi Prospek", value=activity_to_edit.get('prospect_location', '') if activity_to_edit else "")
            contact_person = st.text_input("Nama Kontak", value=activity_to_edit.get('contact_person', '') if activity_to_edit else "")
            contact_position = st.text_input("Jabatan Kontak", value=activity_to_edit.get('contact_position', '') if activity_to_edit else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity_to_edit.get('contact_phone', '') if activity_to_edit else "")
            contact_email = st.text_input("Email Kontak", value=activity_to_edit.get('contact_email', '') if activity_to_edit else "")
        with col2:
            default_date = datetime.strptime(activity_to_edit['activity_date'], '%Y-%m-%d') if activity_to_edit and activity_to_edit.get('activity_date') else datetime.today()
            activity_date = st.date_input("Tanggal Aktivitas*", value=default_date)
            activity_type_options = ["Telepon", "Meeting", "Presentasi", "Demo Produk", "Email", "Lainnya"]
            type_index = activity_type_options.index(activity_to_edit['activity_type']) if activity_to_edit and activity_to_edit.get('activity_type') in activity_type_options else 0
            activity_type = st.selectbox("Jenis Aktivitas*", activity_type_options, index=type_index)
            status_options = ["baru", "dalam_proses", "berhasil", "gagal"]
            status_index = status_options.index(activity_to_edit['status']) if activity_to_edit and activity_to_edit.get('status') in status_options else 0
            status = st.selectbox("Status*", status_options, index=status_index)
        description = st.text_area("Deskripsi / Catatan*", value=activity_to_edit.get('description', '') if activity_to_edit else "")
        submitted = st.form_submit_button("Simpan Aktivitas")
        if submitted:
            if not all([prospect_name, activity_date, activity_type, description]):
                st.error("Mohon isi semua field yang bertanda bintang (*).")
            else:
                data_dict = {"prospect_name": prospect_name, "prospect_location": prospect_location, "contact_person": contact_person, "contact_position": contact_position, "contact_phone": contact_phone, "contact_email": contact_email, "activity_date": activity_date.strftime('%Y-%m-%d'), "activity_type": activity_type, "status": status, "description": description}
                if activity_to_edit:
                    success, message = db.edit_marketing_activity(activity_to_edit['id'], data_dict)
                else:
                    success, message, new_id = db.add_marketing_activity(marketer_id=user['id'], data_dict=data_dict)
                if success:
                    st.success(message); st.rerun()
                else: st.error(message)
    if activity_to_edit:
        st.divider()
        st.subheader(f"Riwayat & Tambah Follow-up untuk: {activity_to_edit['prospect_name']}")
        followups = db.get_followups_by_activity_id(activity_to_edit['id'])
        if followups:
            st.write("**Riwayat Follow-up:**")
            st.dataframe(pd.DataFrame(followups)[['followup_date', 'notes', 'next_action', 'interest_level']], use_container_width=True)
        else: st.info("Belum ada follow-up untuk aktivitas ini.")
        with st.form("followup_form"):
            st.write("**Tambah Follow-up Baru**")
            fu_col1, fu_col2 = st.columns(2)
            with fu_col1:
                followup_date = st.date_input("Tanggal Follow-up", value=datetime.today())
                notes = st.text_area("Catatan Hasil Follow-up*")
                next_action = st.text_input("Rencana Tindak Lanjut")
            with fu_col2:
                next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None)
                interest_level = st.selectbox("Tingkat Ketertarikan", ["Rendah", "Sedang", "Tinggi"])
                status_options = ["baru", "dalam_proses", "berhasil", "gagal"]
                current_status_index = status_options.index(activity_to_edit['status']) if activity_to_edit.get('status') in status_options else 0
                status_update = st.selectbox("Update Status Prospek Menjadi:", status_options, index=current_status_index)
            fu_submitted = st.form_submit_button("Simpan Follow-up")
            if fu_submitted:
                if not notes:
                    st.error("Mohon isi field Catatan Hasil Follow-up.")
                else:
                    fu_data_dict = {"followup_date": followup_date.strftime('%Y-%m-%d'), "notes": notes, "next_action": next_action, "next_followup_date": next_followup_date.strftime('%Y-%m-%d') if next_followup_date else None, "interest_level": interest_level, "status_update": status_update}
                    success, message = db.add_followup(activity_to_edit['id'], fu_data_dict)
                    if success:
                        st.success(message); st.rerun()
                    else: st.error(message)
    if activity_to_edit and role == 'superadmin':
        st.divider()
        if st.button(f"Hapus Aktivitas '{activity_to_edit['prospect_name']}'", type="primary"):
            success, message = db.delete_marketing_activity(activity_to_edit['id'])
            if success:
                st.success(message); st.rerun()
            else: st.error(message)

def show_user_management_page():
    st.title("Manajemen Pengguna")
    users = db.get_all_users_with_profile()
    if users: st.dataframe(pd.DataFrame(users))
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
                if managers:
                    manager_options = {mgr['full_name']: mgr['id'] for mgr in managers}
                    selected_manager_name = st.selectbox("Pilih Manajer", list(manager_options.keys()))
                    if selected_manager_name: manager_id = manager_options[selected_manager_name]
                else: st.warning("Belum ada Manajer terdaftar.")
            submitted = st.form_submit_button("Daftarkan Pengguna")
            if submitted:
                success, message, new_user = db.sign_up(email, password, full_name, role, manager_id)
                if success:
                    st.success(message); st.rerun()
                else: st.error(message)
    with tab2:
        st.subheader("Edit atau Hapus Pengguna")
        if not users:
            st.info("Tidak ada pengguna untuk diedit.")
            return
        user_options = {f"{u.get('full_name', 'N/A')} ({u.get('email', 'N/A')})": u['id'] for u in users if u['id'] != st.session_state.user['id']}
        selected_user_str = st.selectbox("Pilih Pengguna", list(user_options.keys()))
        if selected_user_str:
            user_id_to_edit = user_options[selected_user_str]
            user_to_edit = next((u for u in users if u['id'] == user_id_to_edit), None)
            if user_to_edit:
                with st.form("edit_user_form"):
                    st.write(f"Mengedit: **{user_to_edit.get('full_name', 'N/A')}**")
                    new_full_name = st.text_input("Nama Lengkap", value=user_to_edit.get('full_name', ''))
                    new_role = st.selectbox("Peran (Role)", ["marketing", "manager"], index=["marketing", "manager"].index(user_to_edit['role']) if user_to_edit.get('role') in ["marketing", "manager"] else 0)
                    new_manager_id = user_to_edit.get('manager_id')
                    if new_role == 'marketing':
                        managers = db.get_users_by_role('manager')
                        manager_options = {m['full_name']: m['id'] for m in managers}
                        manager_names = list(manager_options.keys())
                        current_manager_name = next((name for name, id in manager_options.items() if id == new_manager_id), None)
                        current_manager_index = manager_names.index(current_manager_name) if current_manager_name in manager_names else 0
                        selected_manager_name = st.selectbox("Pilih Manajer", manager_names, index=current_manager_index)
                        if selected_manager_name: new_manager_id = manager_options[selected_manager_name]
                    else: new_manager_id = None
                    edit_submitted = st.form_submit_button("Simpan Perubahan")
                    if edit_submitted:
                        success, message = db.update_user_profile(user_id_to_edit, new_full_name, new_role, new_manager_id)
                        if success: st.success(message); st.rerun()
                        else: st.error(message)
                if st.button("Hapus Pengguna Ini", type="primary"):
                    success, message = db.delete_user(user_id_to_edit)
                    if success: st.success(message); st.rerun()
                    else: st.error(message)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    show_login_page()
else:
    menu = show_sidebar()
    if menu == "Dashboard": show_dashboard()
    elif menu in ["Aktivitas Pemasaran", "Aktivitas Tim", "Aktivitas Saya"]: show_activity_management_page()
    elif menu == "Manajemen Pengguna":
        if st.session_state.user.get('role') == 'superadmin': show_user_management_page()
        else: st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")