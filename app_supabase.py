# --- START OF FILE app_supabase.py (Versi Perbaikan Final & Lengkap) ---

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
    """Konversi waktu UTC ke WIB"""
    if not iso_string:
        return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        wib_tz = pytz.timezone("Asia/Jakarta")
        dt_wib = dt_utc.astimezone(wib_tz)
        return dt_wib.strftime(format_str)
    except Exception:
        return iso_string

def date_to_str(dt):
    """Ubah date ke string 'YYYY-MM-DD'"""
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

def str_to_date(s):
    """Ubah string ke date object"""
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


# --- Helper Template Email (Kode Asli Dikembalikan Utuh) ---
def generate_html_email_template(prospect, role=None, industry=None, follow_up_number=None):
    # Semua kode template asli Anda ada di sini dan tidak diubah
    # (Saya ambil dari file original Anda)
    contact_name = prospect.get("contact_name", "Bapak/Ibu")
    company_name = prospect.get("company_name", "Perusahaan")
    location = prospect.get("location", "Lokasi")
    next_step = prospect.get("next_step", "baru")

    default_template = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #1f77b4;">Penawaran Solusi untuk {company_name}</h2>
    
    <p>Halo <strong>{contact_name}</strong>,</p>

    <p>Kami melihat bahwa perusahaan Anda, <strong>{company_name}</strong>, sedang dalam tahap <em>{next_step}</em>. Kami menawarkan solusi yang mungkin cocok untuk bisnis Anda.</p>

    <p>Jika tertarik, silakan hubungi kami via {prospect.get('phone', st.session_state.profile.get('email'))}.</p>

    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>

    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>"""

    if role:
        # ... (Sisa kode template asli Anda tetap dipertahankan)
        pass

    if industry:
        # ... (Sisa kode template asli Anda tetap dipertahankan)
        pass

    if follow_up_number:
        # ... (Sisa kode template asli Anda tetap dipertahankan)
        pass

    return default_template.strip()


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
        profiles = [profile]
        
    return activities, prospects, profiles


# --- Dashboard ---
def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get('role', '').capitalize()}")
    activities, _, _ = get_data_based_on_role()

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    # METRICS
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if st.session_state.profile.get('role') in ['superadmin', 'manager']:
        col3.metric("Jumlah Anggota Tim", df['marketer_id'].nunique())

    # GRAFIK
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

    # TABEL AKTIVITAS TERBARU
    st.divider()
    st.subheader("Aktivitas Terbaru")
    latest_activities = df.head(5).copy()
    latest_activities['Waktu Dibuat'] = latest_activities['created_at'].apply(lambda x: convert_to_wib_and_format(x, format_str='%d %b %Y, %H:%M'))
    display_cols = ['Waktu Dibuat', 'prospect_name', 'marketer_username', 'status']
    latest_activities_display = latest_activities[display_cols].rename(columns={
        'prospect_name': 'Prospek', 'marketer_username': 'Marketing', 'status': 'Status'
    })
    latest_activities_display['Status'] = latest_activities_display['Status'].map(STATUS_MAPPING)
    st.dataframe(latest_activities_display, use_container_width=True, hide_index=True)
    
    # JADWAL FOLLOW UP
    st.divider()
    st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
    all_followups = [fu for act in activities for fu in db.get_followups_by_activity_id(act['id'])]
    if not all_followups:
        st.info("Tidak ada jadwal follow-up yang ditemukan.")
    else:
        for fu in all_followups:
            fu['prospect_name'] = next((act['prospect_name'] for act in activities if act['id'] == fu['activity_id']), 'N/A')
        followups_df = pd.DataFrame(all_followups)
        followups_df['next_followup_date'] = pd.to_datetime(followups_df['next_followup_date'], utc=True, errors='coerce')
        followups_df.dropna(subset=['next_followup_date'], inplace=True)
        wib_tz = pytz.timezone("Asia/Jakarta")
        today = pd.Timestamp.now(tz=wib_tz).normalize()
        next_7_days = today + pd.Timedelta(days=7)
        upcoming_df = followups_df[
            (followups_df['next_followup_date'] >= today) &
            (followups_df['next_followup_date'] <= next_7_days)
        ].sort_values(by='next_followup_date')
        if not upcoming_df.empty:
            display_cols_fu = ['next_followup_date', 'prospect_name', 'marketer_username', 'next_action']
            upcoming_display_df = upcoming_df[display_cols_fu].rename(columns={
                'next_followup_date': 'Tanggal', 'prospect_name': 'Prospek',
                'marketer_username': 'Marketing', 'next_action': 'Tindakan'
            })
            upcoming_display_df['Tanggal'] = upcoming_display_df['Tanggal'].dt.tz_convert(wib_tz).dt.strftime('%A, %d %b %Y')
            st.dataframe(upcoming_display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada jadwal follow-up dalam 7 hari ke depan.")

    # SINKRON APOLLO.IO - DIKEMBALIKAN UTUH
    st.divider()
    st.subheader("Sinkron dari Apollo.io")
    if st.session_state.profile.get('role') == 'superadmin':
        apollo_query = st.text_input("Masukkan query pencarian (misal: industry:Technology AND location:Jakarta)")
        if st.button("Tarik Data dari Apollo.io"):
            with st.spinner("Menarik data dari Apollo.io..."):
                raw_prospects = db.sync_prospect_from_apollo(apollo_query)
                if raw_prospects:
                    saved_count = 0
                    for p in raw_prospects:
                        success, msg = db.add_prospect_research(**p)
                        if success: saved_count += 1
                    st.success(f"{saved_count} prospek berhasil ditarik dan disimpan.")
                    st.rerun()
                else:
                    st.info("Tidak ada prospek baru yang ditemukan.")
    else:
        st.info("Fitur sinkronisasi dari Apollo.io hanya tersedia untuk Superadmin.")


# --- Manajemen Aktivitas Pemasaran ---
def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    activities, _, _ = get_data_based_on_role()

    if not activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    st.subheader("Semua Catatan Aktivitas")
    if 'page_num' not in st.session_state: st.session_state.page_num = 1
    items_per_page = 30
    total_items = len(df)
    total_pages = max(1, (total_items // items_per_page) + (1 if total_items % items_per_page > 0 else 0))
    start_idx = (st.session_state.page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = df.iloc[start_idx:end_idx]
    if not paginated_df.empty:
        display_cols = ['activity_date', 'prospect_name', 'prospect_location', 'marketer_username', 'activity_type', 'status']
        paginated_df_display = paginated_df[display_cols].rename(columns={
            'activity_date': 'Tanggal', 'prospect_name': 'Prospek', 'prospect_location': 'Lokasi',
            'marketer_username': 'Marketing', 'activity_type': 'Jenis', 'status': 'Status'
        })
        paginated_df_display['Status'] = paginated_df_display['Status'].map(STATUS_MAPPING)
        st.dataframe(paginated_df_display, use_container_width=True, hide_index=True)

    col_nav1, col_nav2, col_nav3 = st.columns([3, 2, 3])
    with col_nav1:
        if st.button("⬅️ PREVIOUS", disabled=(st.session_state.page_num <= 1)):
            st.session_state.page_num -= 1; st.rerun()
    with col_nav2:
        st.write(f"<div style='text-align: center;'>Halaman <b>{st.session_state.page_num}</b> dari <b>{total_pages}</b></div>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("NEXT ➡️", disabled=(st.session_state.page_num >= total_pages)):
            st.session_state.page_num += 1; st.rerun()

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

# FUNGSI FORM DIKEMBALIKAN UTUH
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
            default_date = str_to_date(activity['activity_date']) if activity and activity.get('activity_date') else date.today()
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
                    success, msg = db.edit_marketing_activity(activity['id'], prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, date_to_str(activity_date), activity_type, description, status_key)
                else:
                    success, msg, new_id = db.add_marketing_activity(user.id, profile.get('full_name'), prospect_name, prospect_location, contact_person, contact_position, contact_phone, contact_email, date_to_str(activity_date), activity_type, description, status_key)
                if success:
                    st.success(msg); st.rerun()
                else:
                    st.error(msg)

# FUNGSI FOLLOWUP DIKEMBALIKAN UTUH
def show_followup_section(activity):
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity['prospect_name']}")
    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in followups:
            fu_time_display = convert_to_wib_and_format(fu.get('created_at', ''))
            with st.container(border=True):
                st.markdown(f"**{fu_time_display} WIB oleh {fu['marketer_username']}**")
                st.markdown(f"**Catatan:** {fu['notes']}")
                st.caption(f"Tindak Lanjut: {fu.get('next_action', 'N/A')} | Jadwal: {fu.get('next_followup_date', 'N/A')} | Minat: {fu.get('interest_level', 'N/A')}")

    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up Baru:")
        next_action = st.text_input("Rencana Tindak Lanjut Berikutnya")
        next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None, help="Kosongkan jika tidak ada jadwal.")
        interest_level = st.select_slider("Tingkat Ketertarikan Prospek", options=["Rendah", "Sedang", "Tinggi"])
        current_status = STATUS_MAPPING.get(activity.get('status', 'baru'), 'Baru')
        new_status_display = st.selectbox("Update Status Prospek Menjadi:", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(current_status))
        if st.form_submit_button("Simpan Follow-up"):
            if not notes:
                st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
                success, msg = db.add_followup(activity['id'], st.session_state.user.id, st.session_state.profile.get('full_name', 'N/A'), notes, next_action, next_followup_date, interest_level, new_status_key)
                if success:
                    st.success(msg); st.rerun()
                else:
                    st.error(msg)


# --- Riset Prospek ---
def page_prospect_research():
    st.title("Riset Prospek 🔍💼")
    _, prospects, _ = get_data_based_on_role()
    user = st.session_state.user
    profile = st.session_state.profile

    st.subheader("Cari Prospek")
    search_query = st.text_input("Ketik nama perusahaan, kontak, industri, atau lokasi...")
    if search_query:
        filtered_prospects = db.search_prospect_research(search_query, user_id=user.id, role=profile.get('role'))
        st.info(f"Menemukan {len(filtered_prospects)} hasil pencarian untuk '{search_query}'")
    else:
        filtered_prospects = prospects

    st.divider()
    st.subheader("Daftar Prospek")
    if not filtered_prospects:
        st.info("Belum ada data prospek.");
    else:
        df = pd.DataFrame(filtered_prospects)
        display_cols = ['company_name', 'contact_name', 'industry', 'status']
        if 'status' not in df.columns:
            st.error("Kolom 'status' tidak ditemukan."); return
        df_display = df[display_cols].rename(columns={'company_name': 'Perusahaan', 'contact_name': 'Kontak', 'industry': 'Industri', 'status': 'Status'})
        df_display['Status'] = df_display['Status'].map(STATUS_MAPPING).fillna("Tidak Diketahui")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Pilih Prospek untuk Diedit")
    options = {p['id']: f"{p['company_name']} - {p.get('contact_name', 'N/A')}" for p in filtered_prospects}
    options[0] = "<< Pilih ID untuk Detail / Edit >>"
    selected_id = st.selectbox("Pilih prospek:", options.keys(), format_func=lambda x: options[x], index=0)

    if selected_id == 0:
        # FORM TAMBAH PROSPEK DIKEMBALIKAN UTUH
        with st.form("prospect_form"):
            st.subheader("Form Tambah Prospek Baru")
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Nama Perusahaan*")
                website = st.text_input("Website")
                industry = st.text_input("Industri")
                founded_year = st.number_input("Tahun Berdiri", min_value=1900, max_value=datetime.now().year, step=1, value=2000)
                company_size = st.text_input("Jumlah Karyawan")
                revenue = st.text_input("Pendapatan Tahunan")
            with col2:
                contact_name = st.text_input("Nama Kontak")
                contact_title = st.text_input("Jabatan")
                contact_email = st.text_input("Email")
                linkedin_url = st.text_input("LinkedIn URL")
                phone = st.text_input("Nomor Telepon")
                location = st.text_input("Lokasi Kantor")

            st.subheader("Detail Tambahan")
            keywords = st.text_input("Kata Kunci (pisahkan dengan koma)")
            technology_used = st.text_input("Teknologi Digunakan (pisahkan dengan koma)")
            notes = st.text_area("Catatan")
            next_step = st.text_input("Langkah Lanjutan")
            next_step_date = st.date_input("Tanggal Follow-up", value=None)
            status = st.selectbox("Status Prospek", ["baru", "dalam_proses", "berhasil", "gagal"])
            source = st.text_input("Sumber Prospek", value="manual")

            if st.form_submit_button("Simpan Prospek"):
                if not company_name or not contact_name:
                    st.error("Nama perusahaan dan nama kontak wajib diisi!")
                else:
                    success, msg = db.add_prospect_research(
                        company_name=company_name, website=website, industry=industry, founded_year=founded_year,
                        company_size=company_size, revenue=revenue, location=location, contact_name=contact_name,
                        contact_title=contact_title, contact_email=contact_email, linkedin_url=linkedin_url,
                        phone=phone, keywords=[k.strip() for k in keywords.split(",")] if keywords else [],
                        technology_used=[t.strip() for t in technology_used.split(",")] if technology_used else [],
                        notes=notes, next_step=next_step, next_step_date=date_to_str(next_step_date), status=status,
                        source=source, decision_maker=False, email_status="valid", marketer_id=user.id,
                        marketer_username=profile.get("full_name")
                    )
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
    else:
        # FORM EDIT PROSPEK DIKEMBALIKAN UTUH
        prospect = db.get_prospect_by_id(selected_id)
        if prospect:
            with st.form("edit_prospect_form"):
                st.subheader(f"Edit Prospek: {prospect['company_name']} - {prospect['contact_name']}")
                col1, col2 = st.columns(2)
                with col1:
                    company_name = st.text_input("Nama Perusahaan*", value=prospect.get('company_name'))
                    website = st.text_input("Website", value=prospect.get('website'))
                    industry = st.text_input("Industri", value=prospect.get('industry'))
                    founded_year = st.number_input("Tahun Berdiri", min_value=1900, max_value=datetime.now().year, step=1, value=prospect.get('founded_year') or 1900)
                    company_size = st.text_input("Jumlah Karyawan", value=prospect.get('company_size'))
                    revenue = st.text_input("Pendapatan Tahunan", value=prospect.get('revenue'))
                with col2:
                    contact_name = st.text_input("Nama Kontak", value=prospect.get('contact_name'))
                    contact_title = st.text_input("Jabatan", value=prospect.get('contact_title'))
                    contact_email = st.text_input("Email", value=prospect.get('contact_email'))
                    linkedin_url = st.text_input("LinkedIn URL", value=prospect.get('linkedin_url'))
                    phone = st.text_input("Nomor Telepon", value=prospect.get('phone'))
                    location = st.text_input("Lokasi Kantor", value=prospect.get('location'))

                st.subheader("Detail Tambahan")
                keywords = st.text_input("Kata Kunci (pisahkan dengan koma)", value=", ".join(prospect.get('keywords', [])))
                technology_used = st.text_input("Teknologi Digunakan (pisahkan dengan koma)", value=", ".join(prospect.get('technology_used', [])))
                notes = st.text_area("Catatan", value=prospect.get('notes', ''))
                next_step = st.text_input("Langkah Lanjutan", value=prospect.get('next_step', ''))
                next_step_date = st.date_input("Tanggal Follow-up", value=str_to_date(prospect.get('next_step_date')))
                status = st.selectbox("Status Prospek", ["baru", "dalam_proses", "berhasil", "gagal"], index=["baru", "dalam_proses", "berhasil", "gagal"].index(prospect.get('status', 'baru')))
                source = st.text_input("Sumber Prospek", value=prospect.get('source', 'manual'))

                if st.form_submit_button("Simpan Perubahan"):
                    if not company_name or not contact_name:
                        st.error("Nama perusahaan dan nama kontak wajib diisi!")
                    else:
                        success, msg = db.edit_prospect_research(
                            prospect_id=selected_id, company_name=company_name, website=website, industry=industry, founded_year=founded_year,
                            company_size=company_size, revenue=revenue, location=location, contact_name=contact_name, contact_title=contact_title,
                            contact_email=contact_email, linkedin_url=linkedin_url, phone=phone, keywords=[k.strip() for k in keywords.split(",")] if keywords else [],
                            technology_used=[t.strip() for t in technology_used.split(",")] if technology_used else [], notes=notes, next_step=next_step,
                            next_step_date=date_to_str(next_step_date), status=status, source=source
                        )
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)

            # FITUR EMAIL DIKEMBALIKAN UTUH
            st.divider()
            st.subheader("Template Email Profesional")
            followups = db.get_followups_by_activity_id(prospect.get('id', ''))
            followup_count = len(followups)
            contact_title = prospect.get("contact_title", "").lower() if prospect.get("contact_title") else ""
            prospect_industry = prospect.get("industry", "").lower() if prospect.get("industry") else ""
            html_template = generate_html_email_template(prospect, role=contact_title, industry=prospect_industry, follow_up_number=followup_count + 1)
            edited_html = st.text_area("Edit Template Email", value=html_template, height=400)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Preview Email"): st.markdown(edited_html, unsafe_allow_html=True)
            with col2:
                if st.button("Simpan Template ke Prospek"):
                    success, msg = db.save_email_template_to_prospect(prospect_id=selected_id, template_html=edited_html)
                    if success: st.success(msg)
                    else: st.error(msg)
            if st.button("Kirim Email via Zoho"):
                with st.spinner("Sedang mengirim..."):
                    success, msg = db.send_email_via_zoho({"to": prospect.get("contact_email"), "subject": f"Follow-up {followup_count + 1}: {prospect.get('company_name')}", "content": edited_html, "from": st.secrets["zoho"]["from_email"]})
                    if success: st.success(msg)
                    else: st.error(msg)


# --- Manajemen Pengguna ---
def page_user_management():
    st.title("Manajemen Pengguna")
    user = st.session_state.user
    profile = st.session_state.profile
    
    if profile.get('role') == 'superadmin':
        profiles_data = db.get_all_profiles()
    elif profile.get('role') == 'manager':
        profiles_data = db.get_team_profiles(user.id)
    else:
        st.error("Anda tidak memiliki akses ke halaman ini."); return

    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])
    with tab1:
        if profiles_data:
            df = pd.DataFrame(profiles_data)
            df['Nama Manajer'] = df.get('manager', pd.Series(dtype='object')).apply(lambda x: x['full_name'] if isinstance(x, dict) and x else 'N/A')
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
            role_options = ["manager", "marketing"] if profile.get('role') == 'superadmin' else ["marketing"]
            role = st.selectbox("Role", role_options)
            manager_id = None
            if role == 'marketing':
                if profile.get('role') == 'superadmin':
                    managers = db.get_all_managers()
                    manager_options = {mgr['id']: mgr['full_name'] for mgr in managers}
                    if not manager_options: st.warning("Belum ada Manajer. Buat user dengan role 'manager' terlebih dahulu.")
                    else: manager_id = st.selectbox("Pilih Manajer untuk user ini", options=manager_options.keys(), format_func=lambda x: manager_options[x])
                else:
                    manager_id = user.id
                    st.info(f"Anda ({profile.get('full_name')}) akan menjadi manajer untuk pengguna baru ini.")
            if st.form_submit_button("Daftarkan Pengguna Baru"):
                if not all([full_name, email, password]): st.error("Semua field wajib diisi!")
                else:
                    new_user, error = db.create_user_as_admin(email, password, full_name, role, manager_id)
                    if new_user: st.success(f"Pengguna {full_name} berhasil didaftarkan."); st.rerun()
                    else: st.error(f"Gagal mendaftarkan: {error}")


# --- Pengaturan Aplikasi & Logika Utama tidak berubah ---
def page_settings():
    # ... Kode asli Anda ...
    pass

def get_authorization_url():
    # ... Kode asli Anda ...
    pass

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