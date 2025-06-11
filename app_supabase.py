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

# --- Fungsi-fungsi Halaman (Pages) ---

def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user, error = db.sign_in(email, password)
            if user:
                # Ambil profil setelah login berhasil
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
            # Membersihkan semua session state saat logout
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
    
    # --- Baris Grafik ---
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, 
                     title="Distribusi Status Prospek", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        type_counts = df['activity_type'].value_counts()
        fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, 
                      title="Distribusi Jenis Aktivitas", labels={'x': 'Jenis Aktivitas', 'y': 'Jumlah'})
        st.plotly_chart(fig2, use_container_width=True)

    # --- Tabel Follow-up Mendatang ---
    st.divider()
    st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
    
    all_followups = [fu for act in activities for fu in db.get_followups_by_activity_id(act['id'])]
    for fu in all_followups:
        fu['prospect_name'] = next((act['prospect_name'] for act in activities if act['id'] == fu['activity_id']), 'N/A')

    if not all_followups:
        st.info("Tidak ada data follow-up yang ditemukan.")
    else:
        followups_df = pd.DataFrame(all_followups)
        followups_df['next_followup_date'] = pd.to_datetime(followups_df['next_followup_date'], errors='coerce')
        today = pd.Timestamp.now().normalize()
        next_week = today + pd.Timedelta(days=7)
        
        upcoming_df = followups_df[(followups_df['next_followup_date'] >= today) & (followups_df['next_followup_date'] <= next_week)].sort_values(by='next_followup_date')

        if upcoming_df.empty:
            st.info("Tidak ada jadwal follow-up dalam 7 hari ke depan.")
        else:
            display_cols = ['next_followup_date', 'prospect_name', 'marketer_username', 'next_action']
            upcoming_df = upcoming_df[display_cols].rename(columns={
                'next_followup_date': 'Tanggal', 'prospect_name': 'Prospek',
                'marketer_username': 'Marketing', 'next_action': 'Tindakan'
            })
            upcoming_df['Tanggal'] = upcoming_df['Tanggal'].dt.strftime('%A, %d %b %Y')
            st.dataframe(upcoming_df, use_container_width=True, hide_index=True)


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
            # --- PENAMBAHAN FIELD JABATAN ---
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
            if not prospect_name: st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING[status_display]
                # --- MENYELARASKAN PANGGILAN FUNGSI DENGAN MENAMBAHKAN contact_position ---
                if activity:
                    success, msg = db.edit_marketing_activity(activity['id'], prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                else:
                    success, msg, new_id = db.add_marketing_activity(user.id, profile.get('full_name', 'N/A'), prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, activity_date, activity_type, description, status_key)
                
                if success: st.success(msg); st.rerun()
                else: st.error(msg)
    
    if activity and profile.get('role') == 'superadmin':
        if st.button("Hapus Aktivitas Ini", type="primary"):
            success, msg = db.delete_marketing_activity(activity['id'])
            if success: st.success(msg); st.rerun()
            else: st.error(msg)

def show_followup_section(activity):
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
            if not notes: st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                # --- MENYELARASKAN PANGGILAN FUNGSI add_followup ---
                success, msg = db.add_followup(
                    activity['id'], 
                    st.session_state.user.id, 
                    st.session_state.profile.get('full_name', 'N/A'), 
                    notes, next_action, 
                    next_followup_date, 
                    interest_level, 
                    new_status_key
                )
                if success: st.success(msg); st.rerun()
                else: st.error(msg)
                    
def page_user_management():
    st.title("Manajemen Pengguna")
    
    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        st.subheader("Daftar Pengguna Terdaftar")
        profiles = db.get_all_profiles()
        if profiles:
            df = pd.DataFrame(profiles).rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role'})
            st.dataframe(df[['User ID', 'Nama Lengkap', 'Role']], use_container_width=True)
            
            # Opsi Hapus (jika ingin diaktifkan)
            # user_to_delete_id = st.selectbox("Pilih pengguna untuk dihapus", ...)
            # ...
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
    # Inisialisasi session state jika belum ada
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