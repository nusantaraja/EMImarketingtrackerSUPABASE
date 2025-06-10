# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db

# --- Konfigurasi Halaman & Variabel Global ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Fungsi UI ---

def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        username = st.text_input("Username", help="Coba login dengan 'admin' atau 'marketing_test'")
        password = st.text_input("Password", type="password", help="Password tidak dicek di versi ini.")
        if st.form_submit_button("Login"):
            user = db.login(username)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = {"username": username, **user}
                st.success("Login Berhasil!")
                st.rerun()
            else:
                st.error("Username tidak ditemukan.")

def show_sidebar():
    with st.sidebar:
        st.title("Menu Navigasi")
        user = st.session_state.user
        st.write(f"Selamat datang, **{user['name']}**!")
        st.write(f"Role: **{user['role'].capitalize()}**")
        st.divider()

        pages = ["Dashboard", "Aktivitas Pemasaran"]
        if user['role'] == 'superadmin':
            pages.extend(["Manajemen Pengguna", "Pengaturan"])
        
        # Menggunakan radio button untuk navigasi utama
        page = st.radio("Pilih Halaman:", pages)
        
        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        return page

# --- Halaman-Halaman Aplikasi ---

def page_dashboard():
    st.title(f"Dashboard {st.session_state.user['role'].capitalize()}")
    user = st.session_state.user
    activities = db.get_all_marketing_activities() if user['role'] == 'superadmin' else db.get_marketing_activities_by_username(user['username'])
    
    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    df = pd.DataFrame(activities)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if user['role'] == 'superadmin':
        col3.metric("Jumlah Tim Marketing", df['marketer_username'].nunique())

    st.subheader("Analisis Aktivitas")
    col1, col2 = st.columns(2)
    with col1:
        if not df.empty and 'status' in df.columns:
            status_counts = df['status'].map(STATUS_MAPPING).value_counts()
            fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if not df.empty and 'activity_type' in df.columns:
            type_counts = df['activity_type'].value_counts()
            fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas")
            st.plotly_chart(fig2, use_container_width=True)

def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    user = st.session_state.user

    # Dropdown untuk memilih aktivitas atau tambah baru
    activities = db.get_all_marketing_activities() if user['role'] == 'superadmin' else db.get_marketing_activities_by_username(user['username'])
    
    options = {act['id']: f"{act['prospect_name']} (Status: {STATUS_MAPPING.get(act['status'], 'N/A')})" for act in activities}
    options[0] = "<< Tambah Aktivitas Baru >>" # 0 sebagai ID untuk 'Tambah Baru'
    
    selected_id = st.selectbox("Pilih aktivitas untuk dilihat/diedit, atau pilih 'Tambah Baru'", 
                               options.keys(), format_func=lambda x: options[x])

    st.divider()

    # Logika untuk menampilkan Form Tambah atau Form Edit/Detail
    if selected_id == 0:
        # Tampilkan Form untuk Menambah Aktivitas Baru
        show_activity_form(None) # None menandakan ini form baru
    else:
        # Tampilkan Detail, Form Edit, dan Follow-up untuk Aktivitas yang Dipilih
        activity = db.get_activity_by_id(selected_id)
        if activity:
            show_activity_form(activity) # activity menandakan ini form edit
            show_followup_section(activity)

def show_activity_form(activity):
    """Menampilkan form untuk menambah atau mengedit aktivitas."""
    user = st.session_state.user
    form_title = "Detail & Edit Aktivitas" if activity else "Form Aktivitas Baru"
    button_label = "Simpan Perubahan" if activity else "Simpan Aktivitas Baru"

    with st.form(key="activity_form"):
        st.subheader(form_title)
        
        col1, col2 = st.columns(2)
        with col1:
            prospect_name = st.text_input("Nama Prospek*", value=activity['prospect_name'] if activity else "")
            contact_person = st.text_input("Nama Kontak Person", value=activity.get('contact_person', '') if activity else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity.get('contact_phone', '') if activity else "")
        with col2:
            prospect_location = st.text_input("Lokasi Prospek", value=activity.get('prospect_location', '') if activity else "")
            contact_email = st.text_input("Email Kontak", value=activity.get('contact_email', '') if activity else "")
            default_date = datetime.strptime(activity['activity_date'], '%Y-%m-%d') if activity and activity.get('activity_date') else datetime.today()
            activity_date = st.date_input("Tanggal Aktivitas", value=default_date)

        activity_type = st.selectbox("Jenis Aktivitas", options=ACTIVITY_TYPES, index=ACTIVITY_TYPES.index(activity['activity_type']) if activity and activity.get('activity_type') in ACTIVITY_TYPES else 0)
        status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity['status'], 'baru')) if activity else 0)
        description = st.text_area("Deskripsi", value=activity.get('description', '') if activity else "", height=150)
        
        submitted = st.form_submit_button(button_label)
        if submitted:
            if not prospect_name:
                st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING[status_display]
                if activity: # Mode Edit
                    success, msg = db.edit_marketing_activity(activity['id'], prospect_name, prospect_location, contact_person, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                else: # Mode Tambah
                    success, msg, new_id = db.add_marketing_activity(user['username'], prospect_name, prospect_location, contact_person, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    # Tombol Hapus (hanya untuk mode edit dan superadmin)
    if activity and user['role'] == 'superadmin':
        if st.button("Hapus Aktivitas Ini", type="primary"):
            success, msg = db.delete_marketing_activity(activity['id'])
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

def show_followup_section(activity):
    """Menampilkan riwayat dan form tambah follow-up."""
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity['prospect_name']}")

    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in followups:
            fu_time = datetime.fromisoformat(fu['created_at']).strftime('%d %b %Y, %H:%M')
            with st.container(border=True):
                st.markdown(f"**{fu_time} oleh {fu['marketer_username']}**")
                st.markdown(f"**Catatan:** {fu['notes']}")
                st.caption(f"Tindak Lanjut: {fu.get('next_action', 'N/A')} | Jadwal: {fu.get('next_followup_date', 'N/A')} | Minat: {fu.get('interest_level', 'N/A')}")
    else:
        st.caption("Belum ada follow-up untuk aktivitas ini.")

    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up Baru:")
        next_action = st.text_input("Rencana Tindak Lanjut Berikutnya")
        next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None)
        interest_level = st.select_slider("Tingkat Ketertarikan Prospek", options=["Rendah", "Sedang", "Tinggi"])
        new_status_display = st.selectbox("Update Status Prospek Menjadi:", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity['status'], 'baru')))

        if st.form_submit_button("Simpan Follow-up"):
            if not notes:
                st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                success, msg = db.add_followup(activity['id'], st.session_state.user['username'], notes, next_action, next_followup_date, interest_level, new_status_key)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
def page_user_management():
    st.title("Manajemen Pengguna")
    st.info("Saat ini, daftar pengguna dikelola secara manual di dalam kode (`db_supabase.py`). Untuk fitur penuh, integrasikan dengan Supabase Auth.")
    users = db.get_all_users()
    st.dataframe(users)

def page_settings():
    st.title("Pengaturan Aplikasi")
    config = db.get_app_config()
    with st.form("config_form"):
        app_name = st.text_input("Nama Aplikasi", value=config.get('app_name', ''))
        # Tambahkan field lain jika ada di tabel config
        submitted = st.form_submit_button("Simpan Pengaturan")
        if submitted:
            success, msg = db.update_app_config({'app_name': app_name})
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# --- Logika Utama Aplikasi ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        show_login_page()
    else:
        page = show_sidebar()
        if page == "Dashboard":
            page_dashboard()
        elif page == "Aktivitas Pemasaran":
            page_activities_management()
        elif page == "Manajemen Pengguna":
            page_user_management()
        elif page == "Pengaturan":
            page_settings()

if __name__ == "__main__":
    main()