# --- START OF FILE app_supabase.py ---

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import db_supabase as db
import pytz
import requests
from urllib.parse import urlencode


# --- Konfigurasi Halaman ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

# --- Mapping & Konstanta ---
STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]
ROLES = ["superadmin", "manager", "marketing"]


# --- Helper Fungsi Waktu & Tanggal ---
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    if not iso_string: return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        wib_tz = pytz.timezone("Asia/Jakarta")
        return dt_utc.astimezone(wib_tz).strftime(format_str)
    except Exception: return iso_string

def date_to_str(dt): return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt
def str_to_date(s): return datetime.strptime(s, "%Y-%m-%d").date() if s else None


# --- Helper Template Email (Tidak diubah) ---
def generate_html_email_template(prospect, role=None, industry=None, follow_up_number=None):
    # Kode ini tetap sama, tidak perlu diubah
    contact_name = prospect.get("contact_name", "Bapak/Ibu")
    company_name = prospect.get("company_name", "Perusahaan")
    location = prospect.get("location", "Lokasi")
    next_step = prospect.get("next_step", "baru")
    default_template = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">...</div>""" # (Isi template Anda di sini)
    return default_template.strip() # Anda bisa copy-paste isi fungsi ini dari file asli Anda


# --- Halaman Login ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user, error = db.sign_in(email, password)
            if user:
                profile = db.get_profile(user.id)
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.profile = profile
                st.success("Login Berhasil!")
                st.rerun()
            else:
                st.error(f"Login Gagal: {error}")


# --- Sidebar Menu ---
def show_sidebar():
    with st.sidebar:
        profile = st.session_state.profile
        st.title("Menu Navigasi")
        st.write(f"Selamat datang, **{profile.get('full_name', 'User')}**!")
        st.write(f"Role: **{profile.get('role', 'N/A').capitalize()}**")
        st.divider()

        pages = ["Dashboard", "Aktivitas Pemasaran", "Riset Prospek"]
        # --- MODIFIKASI: Manager juga bisa akses Manajemen Pengguna ---
        if profile.get('role') in ['superadmin', 'manager']:
            pages.append("Manajemen Pengguna")
        if profile.get('role') == 'superadmin':
            pages.append("Pengaturan")

        page = st.radio("Pilih Halaman:", pages, key="page_selection")
        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        return page


# --- Fungsi Pengambilan Data Berdasarkan Role ---
def get_data_based_on_role():
    user = st.session_state.user
    profile = st.session_state.profile
    role = profile.get('role')

    if role == 'superadmin':
        activities = db.get_all_marketing_activities()
        prospects = db.get_all_prospect_research()
        profiles = db.get_all_profiles()
    elif role == 'manager':
        activities = db.get_team_marketing_activities(user.id)
        prospects = db.get_team_prospect_research(user.id)
        profiles = db.get_team_profiles(user.id)
    else: # marketing
        activities = db.get_marketing_activities_by_user_id(user.id)
        prospects = db.get_prospect_research_by_marketer(user.id)
        profiles = [profile] # Hanya profil diri sendiri
        
    return activities, prospects, profiles

# --- Dashboard ---
def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get('role', '').capitalize()}")
    activities, _, _ = get_data_based_on_role()

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    df = pd.DataFrame(activities)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if st.session_state.profile.get('role') in ['superadmin', 'manager']:
        col3.metric("Jumlah Anggota Tim", df['marketer_id'].nunique())

    st.subheader("Analisis Aktivitas Pemasaran")
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        type_counts = df['activity_type'].value_counts()
        fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas", labels={'x': 'Jenis', 'y': 'Jumlah'})
        st.plotly_chart(fig2, use_container_width=True)

    if st.session_state.profile.get('role') in ['superadmin', 'manager']:
        col3, col4 = st.columns(2)
        with col3:
            location_counts = df['prospect_location'].str.strip().str.title().value_counts().nlargest(10)
            fig3 = px.bar(location_counts, x=location_counts.index, y=location_counts.values, title="Top 10 Lokasi Prospek")
            st.plotly_chart(fig3, use_container_width=True)
        with col4:
            marketer_counts = df['marketer_username'].value_counts()
            fig4 = px.bar(marketer_counts, x=marketer_counts.index, y=marketer_counts.values, title="Aktivitas per Anggota Tim")
            st.plotly_chart(fig4, use_container_width=True)
    
    # Sisa dashboard (Aktivitas terbaru, jadwal follow-up, Apollo.io) bisa tetap sama
    # (Kode disembunyikan untuk keringkasan)


# --- Manajemen Aktivitas Pemasaran ---
def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    activities, _, _ = get_data_based_on_role()

    # Sisa kode untuk halaman ini (paginasi, form tambah/edit) sebagian besar sama
    # Anda bisa copy-paste dari file asli Anda, karena logika datanya sudah dihandle di atas.
    # Pastikan form tambah/edit juga menggunakan session state user.id & profile.get('full_name')
    # yang sudah benar.
    if not activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
    else:
        df = pd.DataFrame(activities)
        st.subheader("Semua Catatan Aktivitas")
        # Logika paginasi tetap sama...
        # ...
        # Tampilkan dataframe...

    st.divider()
    options = {act['id']: f"{act['prospect_name']} - {act.get('contact_person', 'N/A')}" for act in activities}
    options[0] = "<< Pilih ID untuk Detail / Edit >>"
    selected_id = st.selectbox("Pilih aktivitas untuk melihat detail:", options.keys(), format_func=lambda x: options[x], index=0, key="activity_select")

    if selected_id == 0:
        st.subheader("Form Tambah Aktivitas Baru")
        show_activity_form(None)
    else:
        activity = db.get_activity_by_id(selected_id)
        if activity:
            show_activity_form(activity)
            show_followup_section(activity)


# (Fungsi show_activity_form dan show_followup_section tidak perlu diubah)
def show_activity_form(activity):
    # Tidak ada perubahan di sini
    pass
def show_followup_section(activity):
    # Tidak ada perubahan di sini
    pass


# --- Riset Prospek ---
def page_prospect_research():
    st.title("Riset Prospek 🔍💼")
    _, prospects, _ = get_data_based_on_role()
    user = st.session_state.user
    profile = st.session_state.profile

    st.subheader("Cari Prospek")
    search_query = st.text_input("Ketik nama perusahaan, kontak, industri, atau lokasi...")
    if search_query:
        # --- MODIFIKASI: Search dengan konteks role ---
        filtered_prospects = db.search_prospect_research(search_query, user_id=user.id, role=profile.get('role'))
        st.info(f"Menemukan {len(filtered_prospects)} hasil pencarian untuk '{search_query}'")
    else:
        filtered_prospects = prospects

    # Sisa halaman ini (tabel, form tambah/edit, template email) juga sebagian besar sama.
    # Cukup pastikan data yang di-loop adalah `filtered_prospects`.
    # (Kode disembunyikan untuk keringkasan)


# --- Manajemen Pengguna ---
def page_user_management():
    st.title("Manajemen Pengguna")
    user = st.session_state.user
    profile = st.session_state.profile
    
    # Ambil daftar pengguna berdasarkan role
    if profile.get('role') == 'superadmin':
        profiles_data = db.get_all_profiles()
    elif profile.get('role') == 'manager':
        profiles_data = db.get_team_profiles(user.id)
    else:
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        if profiles_data:
            df = pd.DataFrame(profiles_data)
            # Menata kolom manager
            df['Nama Manajer'] = df['manager'].apply(lambda x: x['full_name'] if x else 'N/A')
            df = df.rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role', 'email': 'Email'})
            st.dataframe(df[['User ID', 'Nama Lengkap', 'Email', 'Role', 'Nama Manajer']], use_container_width=True)
        else:
            st.info("Belum ada pengguna terdaftar.")

    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        with st.form("add_user_form"):
            full_name = st.text_input("Nama Lengkap")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            # Opsi role berdasarkan siapa yang sedang login
            if profile.get('role') == 'superadmin':
                role_options = ["manager", "marketing"]
            else: # Manager
                role_options = ["marketing"]
            role = st.selectbox("Role", role_options)

            # Opsi pilih manajer jika role marketing dipilih
            manager_id = None
            if role == 'marketing':
                if profile.get('role') == 'superadmin':
                    managers = db.get_all_managers()
                    manager_options = {mgr['id']: mgr['full_name'] for mgr in managers}
                    manager_options['self'] = f"Jadikan Diri Sendiri ({profile.get('full_name')}) sebagai Manajer" # Opsi jika Superadmin juga jadi manager
                    selected_manager = st.selectbox("Pilih Manajer untuk user ini", options=manager_options.keys(), format_func=lambda x: manager_options[x])
                    manager_id = user.id if selected_manager == 'self' else selected_manager
                else: # Manager yg login otomatis jadi manager user baru
                    manager_id = user.id
                    st.info(f"Anda akan menjadi manajer untuk pengguna baru ini.")
            
            if st.form_submit_button("Daftarkan Pengguna Baru"):
                if not all([full_name, email, password]):
                    st.error("Semua field wajib diisi!")
                else:
                    new_user, error = db.create_user_as_admin(email, password, full_name, role, manager_id)
                    if new_user:
                        st.success(f"Pengguna {full_name} berhasil didaftarkan.")
                        st.rerun()
                    else:
                        st.error(f"Gagal mendaftarkan: {error}")


# --- Pengaturan Aplikasi ---
def page_settings():
    # Tidak ada perubahan di sini
    st.title("Pengaturan Aplikasi")
    # ... (kode Anda dari file asli)


# --- Logika Utama Aplikasi --- 
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.get("logged_in"):
        show_login_page()
    else:
        page = show_sidebar()
        if page == "Dashboard": page_dashboard()
        elif page == "Aktivitas Pemasaran": page_activities_management()
        elif page == "Manajemen Pengguna": page_user_management()
        elif page == "Pengaturan": page_settings()
        elif page == "Riset Prospek": page_prospect_research()

if __name__ == "__main__":
    main()