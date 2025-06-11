# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db
import pytz

# --- Konfigurasi Halaman & Variabel Global ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Fungsi Helper untuk Waktu ---
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    """Mengkonversi string ISO 8601 dari Supabase ke WIB dan memformatnya."""
    if not iso_string:
        return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string)
        wib_tz = pytz.timezone("Asia/Jakarta")
        dt_wib = dt_utc.astimezone(wib_tz)
        return dt_wib.strftime(format_str)
    except (ValueError, TypeError):
        return iso_string

# --- Fungsi-fungsi Halaman (Pages) ---

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

def show_sidebar():
    with st.sidebar:
        profile = st.session_state.profile
        st.title("Menu Navigasi")
        st.write(f"Selamat datang, **{profile.get('full_name', 'User')}**!")
        st.write(f"Role: **{profile.get('role', 'N/A').capitalize()}**")
        st.divider()
        pages = ["Dashboard", "Aktivitas Pemasaran"]
        if profile.get('role') == 'superadmin':
            pages.extend(["Manajemen Pengguna", "Pengaturan"])
        page = st.radio("Pilih Halaman:", pages)
        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return page

def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get('role', '').capitalize()}")
    user = st.session_state.user
    profile = st.session_state.profile
    
    activities = db.get_all_marketing_activities() if profile.get('role') == 'superadmin' else db.get_marketing_activities_by_user_id(user.id)
    
    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    df = pd.DataFrame(activities)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if profile.get('role') == 'superadmin':
        col3.metric("Jumlah Tim Marketing", df['marketer_id'].nunique())

    st.divider()
    st.subheader("Analisis Aktivitas Pemasaran")
    
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        type_counts = df['activity_type'].value_counts()
        fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas", labels={'x': 'Jenis Aktivitas', 'y': 'Jumlah'})
        st.plotly_chart(fig2, use_container_width=True)

    # --- [PERCANTIK 1] MENAMBAHKAN TABEL AKTIVITAS TERBARU ---
    st.divider()
    st.subheader("Aktivitas Terbaru")
    latest_activities = df.head(5)
    display_cols = ['activity_date', 'prospect_name', 'marketer_username', 'status']
    latest_activities_display = latest_activities[display_cols].rename(columns={
        'activity_date': 'Tanggal', 'prospect_name': 'Prospek', 'marketer_username': 'Marketing', 'status': 'Status'
    })
    latest_activities_display['Status'] = latest_activities_display['Status'].map(STATUS_MAPPING)
    st.dataframe(latest_activities_display, use_container_width=True, hide_index=True)

def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    profile = st.session_state.profile

    activities = db.get_all_marketing_activities() if profile.get('role') == 'superadmin' else db.get_marketing_activities_by_user_id(st.session_state.user.id)
    
    if not activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    st.subheader("Semua Catatan Aktivitas")

    # Inisialisasi state untuk paginasi
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1
    
    items_per_page = 30
    total_items = len(df)
    total_pages = max(1, (total_items // items_per_page) + (1 if total_items % items_per_page > 0 else 0))

    # Potong dataframe sesuai halaman
    start_idx = (st.session_state.page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = df.iloc[start_idx:end_idx]

    # Menampilkan tabel data yang sudah dipaginasi
    if not paginated_df.empty:
        display_cols = ['activity_date', 'prospect_name', 'prospect_location', 'marketer_username', 'activity_type', 'status']
        paginated_df_display = paginated_df[display_cols].rename(columns={
            'activity_date': 'Tanggal', 'prospect_name': 'Prospek', 'prospect_location': 'Lokasi',
            'marketer_username': 'Marketing', 'activity_type': 'Jenis', 'status': 'Status'
        })
        paginated_df_display['Status'] = paginated_df_display['Status'].map(STATUS_MAPPING)
        st.dataframe(paginated_df_display, use_container_width=True, hide_index=True)
    
    # --- [PERCANTIK FINAL] KONTROL PAGINASI DI BAWAH TABEL ---
    st.divider() # Tambahkan garis pemisah agar rapi
    
    # Menggunakan kolom untuk menata tombol dan teks
    col_nav1, col_nav2, col_nav3 = st.columns([3, 2, 3])
    
    with col_nav1:
        # Tombol PREVIOUS di sebelah kiri, tanpa use_container_width
        if st.button("⬅️ PREVIOUS", disabled=(st.session_state.page_num <= 1)):
            st.session_state.page_num -= 1
            st.rerun()
    
    with col_nav2:
        # Teks "Halaman X dari Y" di tengah
        st.write(f"<div style='text-align: center; margin-top: 5px;'>Halaman <b>{st.session_state.page_num}</b> dari <b>{total_pages}</b></div>", unsafe_allow_html=True)

    with col_nav3:
        # Tombol NEXT di sebelah kanan, tanpa use_container_width
        if st.button("NEXT ➡️", disabled=(st.session_state.page_num >= total_pages)):
            st.session_state.page_num += 1
            st.rerun()
    
    st.divider()

    # --- Bagian untuk Detail, Edit, dan Follow-up ---
    options = {act['id']: f"ID: {act['id']} - {act['prospect_name']}" for act in activities}
    options[0] = "<< Pilih ID untuk Detail / Edit / Follow-up >>"
    
    selected_id = st.selectbox("Pilih aktivitas untuk melihat detail:", 
                               options.keys(), format_func=lambda x: options[x], index=0)

    if selected_id == 0:
        st.subheader("Form Tambah Aktivitas Baru")
        show_activity_form(None)
    else:
        activity = db.get_activity_by_id(selected_id)
        if activity:
            show_activity_form(activity)
            show_followup_section(activity)

def show_activity_form(activity):
    profile = st.session_state.profile
    user = st.session_state.user
    form_title = "Detail & Edit Aktivitas" if activity else "Form Aktivitas Baru"
    button_label = "Simpan Perubahan" if activity else "Simpan Aktivitas Baru"

    with st.form(key="activity_form"):
        st.subheader(form_title)
        
        col1, col2 = st.columns(2)
        with col1:
            prospect_name = st.text_input("Nama Prospek*", value=activity.get('prospect_name', '') if activity else "")
            contact_person = st.text_input("Nama Kontak Person", value=activity.get('contact_person', '') if activity else "")
            contact_position = st.text_input("Jabatan Kontak Person", value=activity.get('contact_position', '') if activity else "")
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
                if activity:
                    success, msg = db.edit_marketing_activity(activity['id'], prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                else:
                    success, msg, new_id = db.add_marketing_activity(user.id, profile.get('full_name', 'N/A'), prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                
                if success: 
                    st.success(msg)
                    st.rerun()
                else: 
                    st.error(msg)
    
    if activity and profile.get('role') == 'superadmin':
        if st.button("Hapus Aktivitas Ini", type="primary"):
            success, msg = db.delete_marketing_activity(activity['id'])
            if success: 
                st.success(msg)
                st.rerun()
            else: 
                st.error(msg)

def show_followup_section(activity):
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity['prospect_name']}")

    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in followups:
            fu_time_display = fu.get('created_at', 'Waktu tidak tersedia')
            if fu.get('created_at'):
                try:
                    fu_time_display = convert_to_wib_and_format(fu['created_at'])
                except Exception:
                    pass 
            
            with st.container(border=True):
                st.markdown(f"**{fu_time_display} WIB oleh {fu['marketer_username']}**")
                st.markdown(f"**Catatan:** {fu['notes']}")
                st.caption(f"Tindak Lanjut: {fu.get('next_action', 'N/A')} | Jadwal: {fu.get('next_followup_date', 'N/A')} | Minat: {fu.get('interest_level', 'N/A')}")
    else:
        st.caption("Belum ada follow-up untuk aktivitas ini.")

    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up Baru:")
        next_action = st.text_input("Rencana Tindak Lanjut Berikutnya")
        next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None, help="Kosongkan jika tidak ada jadwal.")
        interest_level = st.select_slider("Tingkat Ketertarikan Prospek", options=["Rendah", "Sedang", "Tinggi"])
        current_status = STATUS_MAPPING.get(activity['status'], 'Baru')
        new_status_display = st.selectbox("Update Status Prospek Menjadi:", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(current_status))

        if st.form_submit_button("Simpan Follow-up"):
            if not notes: 
                st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                success, msg = db.add_followup(activity['id'], st.session_state.user.id, st.session_state.profile.get('full_name', 'N/A'), notes, next_action, next_followup_date, interest_level, new_status_key)
                if success: 
                    st.success(msg)
                    st.rerun()
                else: 
                    st.error(msg)

def page_user_management():
    st.title("Manajemen Pengguna")
    
    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        st.subheader("Daftar Pengguna Terdaftar")
        profiles = db.get_all_profiles()
        if profiles:
            df = pd.DataFrame(profiles).rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role', 'email': 'Email'})
            st.dataframe(df[['User ID', 'Nama Lengkap', 'Email', 'Role']], use_container_width=True)
        else:
            st.info("Belum ada pengguna terdaftar.")

    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        with st.form("signup_form"):
            full_name = st.text_input("Nama Lengkap")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["marketing", "superadmin"])
            if st.form_submit_button("Daftarkan Pengguna Baru"):
                if not all([full_name, email, password]):
                    st.error("Semua field wajib diisi!")
                else:
                    user, error = db.sign_up(email, password, full_name, role)
                    if user:
                        st.success(f"Pengguna {full_name} berhasil didaftarkan! Silakan login.")
                        st.rerun()
                    else:
                        st.error(f"Gagal mendaftarkan: {error}")

def page_settings():
    st.title("Pengaturan Aplikasi")
    config = db.get_app_config()
    with st.form("config_form"):
        app_name = st.text_input("Nama Aplikasi", value=config.get('app_name', ''))
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
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "user" not in st.session_state:
        st.session_state.user = None
        
    if "profile" not in st.session_state:
        st.session_state.profile = None

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