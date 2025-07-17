# --- START OF FILE app_supabase.py (Versi Final Absolut) ---

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import db_supabase as db
from zoneinfo import ZoneInfo

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

# --- MAPPING & KONSTANTA ---
STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- FUNGSI HELPER ---
def clear_all_cache(): st.cache_data.clear(); st.cache_resource.clear()
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    if not iso_string: return "N/A"
    try: dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00')); wib_tz = ZoneInfo("Asia/Jakarta"); return dt_utc.astimezone(wib_tz).strftime(format_str)
    except: return iso_string
def date_to_str(dt): return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt
def str_to_date(s):
    try: return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except: return None

# --- BAGIAN TAMPILAN (UI) ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email"); password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user, error = db.sign_in(email, password)
            if user:
                profile = db.get_profile(user.id)
                if profile:
                    st.session_state.logged_in = True; st.session_state.user = user; st.session_state.profile = profile
                    st.success("Login Berhasil!"); st.rerun()
                else: st.error("Login berhasil, namun profil tidak dapat dimuat.")
            else: st.error(f"Login Gagal: {error}")

def show_sidebar():
    with st.sidebar:
        profile = st.session_state.get('profile')
        if not profile: st.stop()
        st.title("Menu Navigasi"); st.write(f"Selamat datang, **{profile.get('full_name')}**!")
        st.write(f"Role: **{profile.get('role', 'N/A').capitalize()}**"); st.divider()
        pages = ["Dashboard", "Aktivitas Pemasaran"] # Menu Riset Prospek disembunyikan
        if profile.get('role') in ['superadmin', 'manager']: pages.append("Manajemen Pengguna")
        page = st.radio("Pilih Halaman:", pages, key="page_selection"); st.divider()
        if st.button("Logout"): clear_all_cache(); st.session_state.clear(); st.rerun()
        return page

@st.cache_data(ttl=300)
def get_data_based_on_role():
    user = st.session_state.user
    profile = st.session_state.profile
    role = profile.get('role')

    if role == 'superadmin':
        activities = db.get_all_marketing_activities()
        profiles = db.get_all_profiles()
        # Untuk konsistensi, kita kembalikan 3 nilai, meskipun satu mungkin kosong
        prospects = [] # Asumsi riset prospek tidak dipakai
        return activities, prospects, profiles
        
    elif role == 'manager':
        activities = db.get_team_marketing_activities(user.id)
        profiles = db.get_team_profiles(user.id)
        prospects = [] # Asumsi riset prospek tidak dipakai
        return activities, prospects, profiles
        
    else: # marketing
        activities = db.get_marketing_activities_by_user_id(user.id)
        profiles = [profile] # Hanya profil diri sendiri
        prospects = [] # Asumsi riset prospek tidak dipakai
        return activities, prospects, profiles

# --- FUNGSI UNTUK SETIAP HALAMAN ---
def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get('role', '').capitalize()}")
    activities, _, _ = get_data_based_on_role()

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan di Dashboard.")
    else:
        df = pd.DataFrame(activities)

        # Bagian Metrik
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Aktivitas", len(df))
        col2.metric("Total Prospek Unik", df['prospect_name'].nunique() if 'prospect_name' in df.columns else 0)
        if st.session_state.profile.get('role') in ['superadmin', 'manager']:
            col3.metric("Jumlah Anggota Tim", df['marketer_id'].nunique() if 'marketer_id' in df.columns else 0)

        # === GRAFIK DIKEMBALIKAN ===
        st.subheader("Analisis Aktivitas Pemasaran")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            if 'status' in df.columns and not df['status'].empty:
                status_counts = df['status'].map(STATUS_MAPPING).value_counts()
                fig_pie = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
                st.plotly_chart(fig_pie, use_container_width=True)
        with col_chart2:
            if 'activity_type' in df.columns and not df['activity_type'].empty:
                type_counts = df['activity_type'].value_counts()
                fig_bar = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas")
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # === DAFTAR AKTIVITAS TERBARU DIKEMBALIKAN ===
        st.subheader("Aktivitas Terbaru")
        latest_activities = df.head(5).copy()
        if 'created_at' in latest_activities.columns:
            latest_activities['Waktu Dibuat'] = latest_activities['created_at'].apply(lambda x: convert_to_wib_and_format(x, format_str='%d %b %Y, %H:%M'))
            display_cols = ['Waktu Dibuat', 'prospect_name', 'marketer_username', 'status']
            if all(col in latest_activities.columns for col in display_cols):
                latest_display = latest_activities[display_cols].rename(columns={'prospect_name': 'Prospek', 'marketer_username': 'Marketing', 'status': 'Status'})
                latest_display['Status'] = latest_display['Status'].map(STATUS_MAPPING)
                st.dataframe(latest_display, use_container_width=True, hide_index=True)

        st.divider()

        # === JADWAL FOLLOW-UP DIKEMBALIKAN ===
        st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
        all_followups = [fu for act in activities if act.get('id') for fu in db.get_followups_by_activity_id(act['id'])]
        if not all_followups:
            st.info("Tidak ada jadwal follow-up yang ditemukan.")
        else:
            for fu in all_followups:
                fu['prospect_name'] = next((act.get('prospect_name', 'N/A') for act in activities if act.get('id') == fu.get('activity_id')), 'N/A')
            
            followups_df = pd.DataFrame(all_followups)
            if 'next_followup_date' in followups_df.columns:
                followups_df['next_followup_date'] = pd.to_datetime(followups_df['next_followup_date'], utc=True, errors='coerce')
                followups_df.dropna(subset=['next_followup_date'], inplace=True)
                
                if not followups_df.empty:
                    wib_tz = ZoneInfo("Asia/Jakarta")
                    today = pd.Timestamp.now(tz=wib_tz).normalize()
                    next_7_days = today + pd.Timedelta(days=7)
                    upcoming_df = followups_df[(followups_df['next_followup_date'] >= today) & (followups_df['next_followup_date'] <= next_7_days)].sort_values(by='next_followup_date')
                    
                    if not upcoming_df.empty:
                        upcoming_df['Tanggal'] = upcoming_df['next_followup_date'].dt.tz_convert(wib_tz).dt.strftime('%A, %d %b %Y')
                        display_cols_fu = ['Tanggal', 'prospect_name', 'marketer_username', 'next_action']
                        st.dataframe(upcoming_df[display_cols_fu].rename(columns={'prospect_name': 'Prospek', 'marketer_username': 'Marketing', 'next_action': 'Tindakan'}), use_container_width=True, hide_index=True)
                    else:
                        st.info("Tidak ada jadwal follow-up dalam 7 hari ke depan.")
            else:
                st.warning("Data follow-up tidak memiliki kolom 'next_followup_date'.")

    # Fitur Apollo tetap di-skip untuk sementara
    st.divider()

def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran"); activities, _ = get_data_based_on_role()
    valid_activities = [act for act in activities if act and act.get('id')]
    if not valid_activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru."); st.divider()
        show_activity_form(None)
        return

    st.subheader("Semua Catatan Aktivitas")
    df = pd.DataFrame(valid_activities)
    # Menampilkan tabel yang lebih rapi
    display_cols = ['activity_date', 'prospect_name', 'prospect_location', 'marketer_username', 'activity_type', 'status']
    df_display = df[display_cols].rename(columns={'activity_date': 'Tanggal', 'prospect_name': 'Prospek', 'prospect_location': 'Lokasi', 'marketer_username': 'Marketing', 'activity_type': 'Jenis', 'status': 'Status'})
    df_display['Status'] = df_display['Status'].map(STATUS_MAPPING)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.divider()

    options = {act['id']: f"{act['prospect_name']} - {act.get('contact_person', 'N/A')}" for act in valid_activities}
    options[0] = "<< Tambah Aktivitas Baru >>"
    selected_id = st.selectbox("Pilih aktivitas untuk detail/edit:", options.keys(), format_func=lambda x: options.get(x), index=0)
    
    if selected_id == 0: show_activity_form(None)
    else:
        activity = db.get_activity_by_id(selected_id)
        if activity:
            show_activity_form(activity)
            show_followup_section(activity)

def show_activity_form(activity):
    profile = st.session_state.profile; user = st.session_state.user; is_edit_mode = activity is not None
    with st.form(key=f"activity_form_{'edit' + str(activity.get('id')) if is_edit_mode else 'add'}"):
        st.subheader("Form Aktivitas")
        col1, col2 = st.columns(2)
        with col1:
            prospect_name = st.text_input("Nama Prospek*", value=activity.get('prospect_name', '') if is_edit_mode else "")
            contact_person = st.text_input("Kontak Person", value=activity.get('contact_person', '') if is_edit_mode else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity.get('contact_phone', '') if is_edit_mode else "")
        with col2:
            prospect_location = st.text_input("Lokasi Prospek", value=activity.get('prospect_location', '') if is_edit_mode else "")
            contact_position = st.text_input("Jabatan", value=activity.get('contact_position', '') if is_edit_mode else "")
            contact_email = st.text_input("Email Kontak", value=activity.get('contact_email', '') if is_edit_mode else "")
        activity_date = st.date_input("Tanggal Aktivitas", value=str_to_date(activity.get('activity_date')) if is_edit_mode else date.today())
        activity_type = st.selectbox("Jenis Aktivitas", ACTIVITY_TYPES, index=ACTIVITY_TYPES.index(activity.get('activity_type')) if is_edit_mode and activity.get('activity_type') in ACTIVITY_TYPES else 0)
        status_display = st.selectbox("Status", list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity.get('status', 'baru'))) if is_edit_mode else 0)
        description = st.text_area("Deskripsi", value=activity.get('description', '') if is_edit_mode else "")
        if st.form_submit_button("Simpan"):
            if not prospect_name: st.error("Nama Prospek wajib diisi!")
            else:
                with st.spinner("Menyimpan..."):
                    status_key = REVERSE_STATUS_MAPPING.get(status_display)
                    if is_edit_mode:
                        success, msg = db.edit_marketing_activity(activity['id'], prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, date_to_str(activity_date), activity_type, description, status_key)
                    else:
                        success, msg, _ = db.add_marketing_activity(user.id, profile.get('full_name'), prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, date_to_str(activity_date), activity_type, description, status_key)
                    if success: st.success(msg); clear_all_cache(); st.rerun()
                    else: st.error(f"Gagal: {msg}")

def show_followup_section(activity):
    st.divider(); st.subheader(f"Riwayat & Tambah Follow-up untuk {activity.get('prospect_name')}")
    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in reversed(followups): st.markdown(f"**{convert_to_wib_and_format(fu.get('created_at'))}**: {fu.get('notes')}")
    with st.form("new_followup_form", clear_on_submit=True):
        notes = st.text_area("Catatan Follow-up*", key="followup_notes")
        next_action = st.text_input("Tindak Lanjut")
        next_followup_date = st.date_input("Jadwal Berikutnya", value=None)
        interest_level = st.select_slider("Minat", ["Rendah", "Sedang", "Tinggi"])
        status_display = st.selectbox("Update Status", list(STATUS_MAPPING.values()))
        if st.form_submit_button("Simpan Follow-up"):
            if notes:
                success, msg = db.add_followup(activity['id'], st.session_state.user.id, st.session_state.profile.get('full_name'), notes, next_action, next_followup_date, interest_level, REVERSE_STATUS_MAPPING.get(status_display))
                if success: st.success(msg); clear_all_cache(); st.rerun()
                else: st.error(msg)
            else: st.warning("Catatan tidak boleh kosong.")

def page_user_management():
    st.title("Manajemen Pengguna")
    profile = st.session_state.profile; user = st.session_state.user
    if profile.get('role') not in ['superadmin', 'manager']: st.error("Akses ditolak."); return
    profiles_data = db.get_all_profiles() if profile.get('role') == 'superadmin' else db.get_team_profiles(user.id)
    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])
    with tab1:
        st.subheader("Daftar Pengguna Saat Ini")
        if profiles_data:
            df = pd.DataFrame(profiles_data)
            df['Nama Manajer'] = df.get('manager', pd.Series(dtype=object)).apply(lambda x: x.get('full_name') if isinstance(x, dict) else 'N/A')
            st.dataframe(df[['full_name', 'email', 'role', 'Nama Manajer']], use_container_width=True)
        else: st.info("Tidak ada pengguna.")
    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        with st.form("add_user_form", clear_on_submit=True):
            full_name = st.text_input("Nama Lengkap*"); email = st.text_input("Email*"); password = st.text_input("Password*", type="password")
            role_options = ["manager", "marketing"] if profile.get('role') == 'superadmin' else ["marketing"]; role = st.selectbox("Role*", role_options)
            manager_id = None
            if role == 'marketing' and profile.get('role') == 'superadmin':
                managers = db.get_all_managers(); manager_options = {mgr['id']: mgr['full_name'] for mgr in managers}
                if managers: manager_id = st.selectbox("Pilih Manajer*", list(manager_options.keys()), format_func=lambda x: manager_options.get(x))
                else: st.warning("Belum ada manajer.")
            elif role == 'marketing' and profile.get('role') == 'manager': manager_id = user.id
            if st.form_submit_button("Daftarkan"):
                if all([full_name, email, password]):
                    _, error = db.create_user_as_admin(email, password, full_name, role, manager_id)
                    if not error: st.success("Pengguna berhasil didaftarkan."); clear_all_cache()
                    else: st.error(f"Gagal: {error}")
                else: st.error("Field dengan tanda bintang (*) wajib diisi!")

def main():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.get("logged_in"):
        show_login_page()
    else:
        page = show_sidebar()
        if page:
            if page == "Dashboard": page_dashboard()
            elif page == "Aktivitas Pemasaran": page_activities_management()
            elif page == "Manajemen Pengguna": page_user_management()
            # Halaman yang tidak digunakan dinonaktifkan dari router utama
            # elif page == "Riset Prospek": page_prospect_research()
            # elif page == "Pengaturan": page_settings()

if __name__ == "__main__":
    main()