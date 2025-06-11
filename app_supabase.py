# app_supabase.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db
import pytz # <-- TAMBAHKAN BARIS INI

def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    """Mengkonversi string ISO 8601 dari Supabase ke WIB dan memformatnya."""
    if not iso_string:
        return "N/A"
    try:
        # Buat objek datetime dari string ISO, sudah termasuk info timezone (UTC)
        dt_utc = datetime.fromisoformat(iso_string)
        
        # Tentukan zona waktu WIB
        wib_tz = pytz.timezone("Asia/Jakarta") # Menggunakan nama timezone resmi
        
        # Konversi ke WIB
        dt_wib = dt_utc.astimezone(wib_tz)
        
        # Format menjadi string yang mudah dibaca
        return dt_wib.strftime(format_str)
    except (ValueError, TypeError):
        # Jika format string tidak valid atau None
        return iso_string

# --- Konfigurasi Halaman & Variabel Global ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

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
    
    # Ambil data aktivitas
    if profile.get('role') == 'superadmin':
        activities = db.get_all_marketing_activities()
    else:
        activities = db.get_marketing_activities_by_user_id(user.id)
    
    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        return

    df = pd.DataFrame(activities)
    
    # --- Metrik Utama ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if profile.get('role') == 'superadmin':
        col3.metric("Jumlah Tim Marketing", df['marketer_id'].nunique())

    st.divider()
    st.subheader("Analisis Aktivitas Pemasaran")
    
    # --- Baris Grafik Pertama (Status & Jenis Aktivitas) ---
    col1, col2 = st.columns(2)
    with col1:
        if not df.empty and 'status' in df.columns:
            status_counts = df['status'].map(STATUS_MAPPING).value_counts()
            fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, 
                         title="Distribusi Status Prospek", color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
            
    with col2:
        if not df.empty and 'activity_type' in df.columns:
            type_counts = df['activity_type'].value_counts()
            fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, 
                          title="Distribusi Jenis Aktivitas", labels={'x': 'Jenis Aktivitas', 'y': 'Jumlah'})
            st.plotly_chart(fig2, use_container_width=True)

    # --- [SENTUHAN AKHIR 1] Baris Grafik Kedua (Lokasi & Nama Marketing) ---
    # Hanya ditampilkan untuk superadmin untuk analisis yang lebih dalam
    if profile.get('role') == 'superadmin':
        col3, col4 = st.columns(2)
        with col3:
            if not df.empty and 'prospect_location' in df.columns:
                # Membersihkan dan menghitung 10 lokasi teratas
                location_counts = df['prospect_location'].str.strip().str.title().value_counts().nlargest(10)
                fig3 = px.bar(location_counts, x=location_counts.index, y=location_counts.values, 
                              title="Top 10 Lokasi Prospek", labels={'x': 'Kota/Lokasi', 'y': 'Jumlah Prospek'})
                st.plotly_chart(fig3, use_container_width=True)
                
        with col4:
            if not df.empty and 'marketer_username' in df.columns:
                marketer_counts = df['marketer_username'].value_counts()
                fig4 = px.bar(marketer_counts, x=marketer_counts.index, y=marketer_counts.values, 
                              title="Aktivitas per Marketing", labels={'x': 'Nama Marketing', 'y': 'Jumlah Aktivitas'},
                              color=marketer_counts.values, color_continuous_scale=px.colors.sequential.Viridis)
                st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    
    # --- [SENTUHAN AKHIR 2] Tabel Follow-up Mendatang (5 Hari ke Depan) ---
    st.subheader("Jadwal Follow-up (5 Hari Mendatang)")

    # Mengambil semua data follow-up dari semua aktivitas yang ada
    # Ini kurang efisien untuk data besar, tapi sangat efektif untuk dashboard
    all_followups = [fu for act in activities for fu in db.get_followups_by_activity_id(act['id'])]
    
    # Menambahkan nama prospek ke setiap data follow-up untuk ditampilkan di tabel
    for fu in all_followups:
        fu['prospect_name'] = next((act['prospect_name'] for act in activities if act['id'] == fu['activity_id']), 'N/A')

    if not all_followups:
        st.info("Tidak ada data follow-up yang ditemukan.")
    else:
        followups_df = pd.DataFrame(all_followups)
        
        # Konversi kolom tanggal menjadi tipe datetime untuk perbandingan
        followups_df['next_followup_date'] = pd.to_datetime(followups_df['next_followup_date'], errors='coerce')
        
        # Tentukan rentang waktu: hari ini sampai 5 hari ke depan
        today = pd.Timestamp.now().normalize()
        next_5_days = today + pd.Timedelta(days=5)
        
        # Filter dataframe untuk menampilkan hanya yang akan datang
        upcoming_followups_df = followups_df[
            (followups_df['next_followup_date'] >= today) &
            (followups_df['next_followup_date'] <= next_5_days)
        ].sort_values(by='next_followup_date')

        if upcoming_followups_df.empty:
            st.info("Tidak ada jadwal follow-up dalam 5 hari ke depan.")
        else:
            # Pilih dan ganti nama kolom untuk tampilan yang lebih rapi
            display_cols = ['next_followup_date', 'prospect_name', 'marketer_username', 'next_action']
            upcoming_followups_df = upcoming_followups_df[display_cols].rename(columns={
                'next_followup_date': 'Tanggal Follow-up',
                'prospect_name': 'Nama Prospek',
                'marketer_username': 'Marketing',
                'next_action': 'Tindakan Selanjutnya'
            })
            # Format tanggal agar lebih mudah dibaca oleh manusia
            upcoming_followups_df['Tanggal Follow-up'] = upcoming_followups_df['Tanggal Follow-up'].dt.strftime('%A, %d %B %Y')
            
            st.dataframe(upcoming_followups_df, use_container_width=True, hide_index=True)

def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    profile = st.session_state.profile

    activities = db.get_all_marketing_activities() if profile.get('role') == 'superadmin' else db.get_marketing_activities_by_user_id(st.session_state.user.id)
    
    options = {act['id']: f"{act['prospect_name']} (Status: {STATUS_MAPPING.get(act['status'], 'N/A')})" for act in activities}
    options[0] = "<< Tambah Aktivitas Baru >>"
    
    selected_id = st.selectbox("Pilih aktivitas untuk dilihat/diedit, atau pilih 'Tambah Baru'", 
                               options.keys(), format_func=lambda x: options[x])
    st.divider()

    if selected_id == 0:
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
                    # INI ADALAH BARIS YANG DIPERBAIKI
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

# Di dalam file app_supabase.py, ganti seluruh fungsi show_followup_section() dengan ini:

def show_followup_section(activity):
    """Menampilkan riwayat follow-up dan form untuk menambah follow-up baru."""
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity['prospect_name']}")

    # Mengambil dan menampilkan follow-up yang sudah ada
    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in followups:
            # --- LOGIKA YANG DIPERBAIKI ---
            fu_time_display = fu.get('created_at', 'Waktu tidak tersedia') # Nilai default
            fu_time_str = fu.get('created_at')
            
            # Coba konversi ke format yang lebih bagus jika memungkinkan
            if fu_time_str:
                try:
                    fu_time_display = convert_to_wib_and_format(fu_time_str)
                except Exception:
                    # Jika gagal, biarkan apa adanya (nilai dari database)
                    pass 
            # -----------------------------
            
            # Menggunakan st.container agar setiap follow-up terpisah rapi
            with st.container(border=True):
                st.markdown(f"**{fu_time_display} WIB oleh {fu['marketer_username']}**")
                st.markdown(f"**Catatan:** {fu['notes']}")
                st.caption(f"Tindak Lanjut: {fu.get('next_action', 'N/A')} | Jadwal: {fu.get('next_followup_date', 'N/A')} | Minat: {fu.get('interest_level', 'N/A')}")
    else:
        st.caption("Belum ada follow-up untuk aktivitas ini.")

    # Form untuk menambah follow-up baru
    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up Baru:")
        next_action = st.text_input("Rencana Tindak Lanjut Berikutnya")
        next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None, help="Kosongkan jika tidak ada jadwal.")
        interest_level = st.select_slider("Tingkat Ketertarikan Prospek", options=["Rendah", "Sedang", "Tinggi"])
        
        # Opsi untuk mengupdate status aktivitas induk saat follow-up ditambahkan
        current_status = STATUS_MAPPING.get(activity['status'], 'Baru')
        new_status_display = st.selectbox(
            "Update Status Prospek Menjadi:", 
            options=list(STATUS_MAPPING.values()), 
            index=list(STATUS_MAPPING.values()).index(current_status)
        )

        if st.form_submit_button("Simpan Follow-up"):
            if not notes: 
                st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                # Memanggil fungsi add_followup dari db_supabase
                success, msg = db.add_followup(
                    activity['id'], 
                    st.session_state.user.id, 
                    st.session_state.profile.get('full_name', 'N/A'), 
                    notes, 
                    next_action, 
                    next_followup_date, 
                    interest_level, 
                    new_status_key
                )
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
            if success: st.success(msg); st.rerun()
            else: st.error(msg)

# --- Logika Utama Aplikasi ---
def main():
    if "logged_in" not in st.session_state:
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