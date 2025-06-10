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
                st.session_state.selected_activity_id = None # Reset pilihan saat login
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
        
        # Gunakan st.page_link jika pakai Streamlit 1.33+, atau st.button jika tidak
        if st.button("⬅️ Kembali ke Daftar Aktivitas"):
            st.session_state.page = "Aktivitas Pemasaran"
            st.session_state.selected_activity_id = None
            st.rerun()
        
        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

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
        status_counts = df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        if not df.empty:
            type_counts = df['activity_type'].value_counts()
            fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas")
            st.plotly_chart(fig2, use_container_width=True)

def page_activities_list():
    st.title("Daftar Aktivitas Pemasaran")
    user = st.session_state.user
    activities = db.get_all_marketing_activities() if user['role'] == 'superadmin' else db.get_marketing_activities_by_username(user['username'])

    if st.button("➕ Tambah Aktivitas Baru"):
        st.session_state.page = "Form Aktivitas"
        st.session_state.selected_activity_id = None # Mode Tambah
        st.rerun()

    if not activities:
        st.info("Belum ada aktivitas. Silakan tambahkan yang baru.")
        return

    df = pd.DataFrame(activities)
    st.write(f"Total: {len(df)} aktivitas")
    
    for index, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.markdown(f"**{row['prospect_name']}**")
            col1.caption(f"Oleh: {row['marketer_username']} | Lokasi: {row.get('prospect_location', 'N/A')}")
            col2.info(f"Jenis: {row.get('activity_type', 'N/A')}")
            col3.warning(f"Status: {STATUS_MAPPING.get(row['status'], 'N/A')}")
            if col4.button("Lihat Detail / Follow-up", key=f"detail_{row['id']}"):
                st.session_state.page = "Detail Aktivitas"
                st.session_state.selected_activity_id = row['id']
                st.rerun()
            st.divider()

def page_activity_detail_and_followup():
    activity_id = st.session_state.selected_activity_id
    activity = db.get_activity_by_id(activity_id)

    if not activity:
        st.error("Aktivitas tidak ditemukan. Kembali ke daftar.")
        st.session_state.page = "Aktivitas Pemasaran"
        st.session_state.selected_activity_id = None
        st.rerun()
        return

    st.title(f"Detail: {activity['prospect_name']}")
    
    # Menampilkan detail aktivitas
    with st.expander("Lihat/Edit Detail Aktivitas", expanded=True):
        with st.form("edit_activity_form"):
            # ... (semua field form dari kode lama Anda) ...
            prospect_name = st.text_input("Nama Prospek", value=activity['prospect_name'])
            prospect_location = st.text_input("Lokasi", value=activity.get('prospect_location', ''))
            contact_person = st.text_input("Kontak Person", value=activity.get('contact_person', ''))
            contact_phone = st.text_input("Telepon", value=activity.get('contact_phone', ''))
            status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity['status'], 'baru')))
            
            # ... tambahkan field lainnya ...
            
            if st.form_submit_button("Simpan Perubahan Aktivitas"):
                status_key = REVERSE_STATUS_MAPPING[status_display]
                # Panggil fungsi edit dari db_supabase.py
                success, msg = db.edit_marketing_activity(activity_id, prospect_name, prospect_location, contact_person, contact_phone, activity.get('contact_email'), activity.get('activity_date'), activity.get('activity_type'), activity.get('description'), status_key)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    # Bagian Follow-up
    st.subheader("Riwayat & Tambah Follow-up")
    followups = db.get_followups_by_activity_id(activity_id)
    if followups:
        for fu in followups:
            fu_time = datetime.fromisoformat(fu['created_at']).strftime('%d %b %Y, %H:%M')
            st.info(f"**{fu_time} oleh {fu['marketer_username']}**\n\n{fu['notes']}\n\n*Next Action:* {fu['next_action']}")
    else:
        st.caption("Belum ada follow-up untuk aktivitas ini.")

    with st.form("new_followup_form"):
        notes = st.text_area("Catatan Follow-up Baru:")
        if st.form_submit_button("Simpan Follow-up"):
            if not notes:
                st.warning("Catatan tidak boleh kosong.")
            else:
                # Panggil fungsi add_followup dari db_supabase.py
                # Untuk kesederhanaan, kita hardcode beberapa nilai
                success, msg = db.add_followup(activity_id, st.session_state.user['username'], notes, "Hubungi lagi", None, "Sedang", activity['status'])
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
def page_activity_form():
    st.title("Form Aktivitas Pemasaran Baru")
    with st.form("new_activity_form"):
        # ... (semua field untuk form BARU) ...
        prospect_name = st.text_input("Nama Prospek*")
        prospect_location = st.text_input("Lokasi")
        activity_type = st.selectbox("Jenis Aktivitas", ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"])
        status_display = st.selectbox("Status Awal", options=list(STATUS_MAPPING.values()))
        description = st.text_area("Deskripsi")
        
        if st.form_submit_button("Simpan Aktivitas Baru"):
            if not prospect_name:
                st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING[status_display]
                success, msg, new_id = db.add_marketing_activity(
                    st.session_state.user['username'], prospect_name, prospect_location,
                    "", "", "", "", datetime.today(), activity_type, description, status_key
                )
                if success:
                    st.success(msg)
                    st.session_state.page = "Detail Aktivitas"
                    st.session_state.selected_activity_id = new_id
                    st.rerun()
                else:
                    st.error(msg)

def main():
    # Inisialisasi session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    if 'selected_activity_id' not in st.session_state:
        st.session_state.selected_activity_id = None

    if not st.session_state.logged_in:
        show_login_page()
        return

    show_sidebar()
    
    # Navigasi Halaman
    if st.session_state.page == "Dashboard":
        page_dashboard()
    elif st.session_state.page == "Aktivitas Pemasaran":
        page_activities_list()
    elif st.session_state.page == "Detail Aktivitas":
        page_activity_detail_and_followup()
    elif st.session_state.page == "Form Aktivitas":
        page_activity_form()
    # Halaman lain bisa ditambahkan di sini
    # elif st.session_state.page == "Manajemen Pengguna":
    #     ...

if __name__ == "__main__":
    main()