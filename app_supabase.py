# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db # Import file database baru kita

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="EMI Marketing Tracker",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

STATUS_MAPPING = {
    'baru': 'Baru',
    'dalam_proses': 'Dalam Proses',
    'berhasil': 'Berhasil',
    'gagal': 'Gagal'
}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}


# --- Halaman Login ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        username = st.text_input("Username")
        # Password field for UI, but not used for auth in this simple version
        password = st.text_input("Password", type="password", help="Untuk saat ini, cukup masukkan username yang valid.")
        submitted = st.form_submit_button("Login")

        if submitted:
            user = db.login(username)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = {"username": username, **user}
                st.success("Login Berhasil!")
                st.rerun()
            else:
                st.error("Username tidak ditemukan.")

# --- Sidebar ---
def show_sidebar():
    with st.sidebar:
        st.title("Menu Navigasi")
        user = st.session_state.user
        st.write(f"Selamat datang, **{user['name']}**!")
        st.write(f"Role: **{user['role'].capitalize()}**")
        st.divider()

        if user['role'] == 'superadmin':
            menu = st.radio("Pilih Halaman:", ["Dashboard", "Aktivitas Pemasaran", "Manajemen Pengguna", "Pengaturan"])
        else:
            menu = st.radio("Pilih Halaman:", ["Dashboard", "Aktivitas Pemasaran"])

        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    return menu

# --- Halaman Utama & Logika Lainnya (Sebagian besar sama, hanya panggilan fungsi yang berubah) ---

def show_dashboard():
    st.title(f"Dashboard {st.session_state.user['role'].capitalize()}")
    user = st.session_state.user
    
    if user['role'] == 'superadmin':
        activities = db.get_all_marketing_activities()
        users = db.get_all_users()
    else:
        activities = db.get_marketing_activities_by_username(user['username'])
        users = []

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    activities_df = pd.DataFrame(activities)
    total_activities = len(activities_df)
    total_prospects = activities_df['prospect_name'].nunique()
    total_marketing = len([u for u in users if u.get('role') == 'marketing']) if users else 1

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", total_activities)
    col2.metric("Total Prospek Unik", total_prospects)
    if user['role'] == 'superadmin':
        col3.metric("Jumlah Tim Marketing", total_marketing)

    # Visualisasi
    st.subheader("Analisis Aktivitas")
    col1, col2 = st.columns(2)

    with col1:
        status_counts = activities_df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if user['role'] == 'superadmin':
            marketer_counts = activities_df['marketer_username'].value_counts()
            fig2 = px.bar(marketer_counts, x=marketer_counts.index, y=marketer_counts.values, title="Aktivitas per Marketing", labels={'x': 'Marketing', 'y': 'Jumlah Aktivitas'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
             activity_type_counts = activities_df['activity_type'].value_counts()
             fig2 = px.pie(activity_type_counts, values=activity_type_counts.values, names=activity_type_counts.index, title="Distribusi Jenis Aktivitas")
             st.plotly_chart(fig2, use_container_width=True)

def show_marketing_activities_page():
    st.title("Manajemen Aktivitas Pemasaran")
    user = st.session_state.user

    if user['role'] == 'superadmin':
        activities = db.get_all_marketing_activities()
    else:
        activities = db.get_marketing_activities_by_username(user['username'])

    if not activities:
        st.info("Belum ada aktivitas. Silakan tambahkan aktivitas baru.")
    else:
        df = pd.DataFrame(activities)
        df['status'] = df['status'].map(STATUS_MAPPING)
        st.dataframe(df[['created_at', 'marketer_username', 'prospect_name', 'activity_type', 'status']], use_container_width=True)

    # Form untuk Tambah / Edit
    activity_to_edit = None
    if activities:
        ids = ["Tambah Baru"] + [f"{act['id']} - {act['prospect_name']}" for act in activities]
        selected_id_str = st.selectbox("Pilih aktivitas untuk diedit, atau pilih 'Tambah Baru'", ids)
        if selected_id_str != "Tambah Baru":
            selected_id = int(selected_id_str.split(" - ")[0])
            activity_to_edit = db.get_activity_by_id(selected_id)
    
    with st.form("activity_form"):
        st.subheader("Form Aktivitas")
        prospect_name = st.text_input("Nama Prospek", value=activity_to_edit['prospect_name'] if activity_to_edit else "")
        # ... tambahkan field input lainnya seperti di app lama ...
        status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING[activity_to_edit['status']]) if activity_to_edit else 0)

        # Tambahkan field lainnya di sini sesuai contoh dari kode lama
        prospect_location = st.text_input("Lokasi Prospek", value=activity_to_edit['prospect_location'] if activity_to_edit else "")
        contact_person = st.text_input("Nama Kontak", value=activity_to_edit['contact_person'] if activity_to_edit else "")
        contact_phone = st.text_input("Telepon Kontak", value=activity_to_edit['contact_phone'] if activity_to_edit else "")
        contact_email = st.text_input("Email Kontak", value=activity_to_edit['contact_email'] if activity_to_edit else "")
        
        default_date = datetime.strptime(activity_to_edit['activity_date'], '%Y-%m-%d') if activity_to_edit and activity_to_edit['activity_date'] else datetime.today()
        activity_date = st.date_input("Tanggal Aktivitas", value=default_date)

        activity_type_options = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]
        activity_type = st.selectbox("Jenis Aktivitas", options=activity_type_options, index=activity_type_options.index(activity_to_edit['activity_type']) if activity_to_edit and activity_to_edit.get('activity_type') in activity_type_options else 0)
        description = st.text_area("Deskripsi", value=activity_to_edit['description'] if activity_to_edit else "")
        
        submitted = st.form_submit_button("Simpan Aktivitas")

        if submitted:
            status_key = REVERSE_STATUS_MAPPING[status_display]
            if activity_to_edit: # Mode Edit
                success, message = db.edit_marketing_activity(activity_to_edit['id'], prospect_name, prospect_location, contact_person, contact_phone, contact_email, activity_date, activity_type, description, status_key)
            else: # Mode Tambah Baru
                success, message, new_id = db.add_marketing_activity(user['username'], prospect_name, prospect_location, contact_person, contact_phone, contact_email, activity_date, activity_type, description, status_key)
            
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # Hapus aktivitas (hanya untuk admin)
    if activity_to_edit and user['role'] == 'superadmin':
        if st.button("Hapus Aktivitas Ini", type="primary"):
            success, message = db.delete_marketing_activity(activity_to_edit['id'])
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # Tampilkan Follow-ups
    if activity_to_edit:
        st.divider()
        st.subheader(f"Follow-up untuk {activity_to_edit['prospect_name']}")
        followups = db.get_followups_by_activity_id(activity_to_edit['id'])
        if followups:
            for fu in followups:
                with st.expander(f"Follow-up pada {fu['created_at']}"):
                    st.write(f"**Catatan:** {fu['notes']}")
                    st.write(f"**Tindak Lanjut:** {fu['next_action']} (Jadwal: {fu.get('next_followup_date', 'N/A')})")
                    st.write(f"**Tingkat Ketertarikan:** {fu.get('interest_level', 'N/A')}")
        
        with st.form("followup_form"):
            st.write("**Tambah Follow-up Baru**")
            notes = st.text_area("Catatan")
            next_action = st.text_input("Tindakan Selanjutnya")
            next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None)
            interest_level = st.select_slider("Tingkat Ketertarikan", options=["Rendah", "Sedang", "Tinggi"])
            
            # Saat follow-up ditambahkan, status aktivitas utama juga diupdate
            new_status_display = st.selectbox("Update Status Prospek Menjadi:", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING[activity_to_edit['status']]))
            
            fu_submitted = st.form_submit_button("Simpan Follow-up")
            if fu_submitted:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                success, message = db.add_followup(activity_to_edit['id'], user['username'], notes, next_action, next_followup_date, interest_level, new_status_key)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def show_settings_page():
    st.title("Pengaturan Aplikasi")
    config = db.get_app_config()
    with st.form("config_form"):
        app_name = st.text_input("Nama Aplikasi", value=config.get('app_name'))
        submitted = st.form_submit_button("Simpan")
        if submitted:
            success, message = db.update_app_config({'app_name': app_name})
            if success:
                st.success(message)
            else:
                st.error(message)

# --- Main App Logic ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login_page()
else:
    menu = show_sidebar()
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Aktivitas Pemasaran":
        show_marketing_activities_page()
    elif menu == "Manajemen Pengguna":
        st.title("Manajemen Pengguna")
        st.info("Fitur ini dapat dikembangkan lebih lanjut dengan Supabase Auth.")
        users = db.get_all_users()
        st.dataframe(users)
    elif menu == "Pengaturan":
        show_settings_page()