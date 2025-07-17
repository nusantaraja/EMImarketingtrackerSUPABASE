# --- START OF FILE app_supabase.py (Versi FINAL, Lengkap, dan Utuh) ---

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import db_supabase as db
from zoneinfo import ZoneInfo
import requests
from urllib.parse import urlencode
import streamlit.components.v1 as components
from gotrue.errors import AuthApiError

def sign_in(email, password):
    """
    Menangani proses login pengguna dengan penanganan error yang lebih baik.
    """
    supabase = init_connection()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except AuthApiError as e:
        # Menangkap error spesifik dari Supabase dengan lebih aman
        # Pesan ini sudah pasti "Invalid login credentials"
        return None, "Kombinasi email & password salah."
    except Exception as e:
        # Menangkap error lainnya yang mungkin terjadi (misal masalah jaringan)
        return None, f"Terjadi error tak terduga: {str(e)}"

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

# --- Mapping & Konstanta ---
STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Fungsi Helper ---
def clear_all_cache():
    """Membersihkan semua cache di aplikasi Streamlit."""
    st.cache_data.clear()
    st.cache_resource.clear()

def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    if not iso_string: return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        wib_tz = ZoneInfo("Asia/Jakarta")
        return dt_utc.astimezone(wib_tz).strftime(format_str)
    except (ValueError, TypeError): return iso_string

def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

def str_to_date(s):
    try: return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except (ValueError, TypeError): return None

def generate_html_email_template(prospect, user_profile):
    contact_name = prospect.get("contact_name", "Bapak/Ibu")
    company_name = prospect.get("company_name", "Perusahaan Anda")
    industry = prospect.get("industry", "Anda")
    sender_name = user_profile.get("full_name", "Tim Solusi AI")
    sender_role = user_profile.get("role")
    sender_title, sender_linkedin, email_body = "", "", ""
    if sender_role == 'superadmin':
        sender_title = "Founder & CEO, Solusi AI Indonesia"
        sender_linkedin = "https://www.linkedin.com/in/iwancahyo/"
        email_body = f"""<p>Perkenalkan, saya <strong>{sender_name}</strong>, Founder & CEO dari <strong>Solusi AI Indonesia</strong>.</p><p>Saya melihat <strong>{company_name}</strong> sebagai salah satu pemain kunci di industri {industry}. Di era digital yang sangat kompetitif ini, adopsi teknologi cerdas bukan lagi pilihan, melainkan sebuah keharusan untuk tetap relevan dan unggul.</p><p>Apakah Anda terbuka untuk sebuah diskusi singkat minggu depan?</p>"""
    elif sender_role == 'manager':
        sender_title = "AI Solutions Manager, Solusi AI Indonesia"
        email_body = f"""<p>Perkenalkan, saya <strong>{sender_name}</strong>, AI Solutions Manager dari <strong>Solusi AI Indonesia</strong>.</p><p>CEO kami, Iwan Cahyo, menugaskan saya untuk menjangkau perusahaan-perusahaan potensial seperti <strong>{company_name}</strong>.</p><p>Saya ingin mengundang Anda untuk sesi konsultasi 30 menit tanpa komitmen untuk memetakan potensi solusi AI yang paling efektif untuk tim Anda.</p>"""
    else:
        sender_title = "Business Development, Solusi AI Indonesia"
        email_body = f"""<p>Saya <strong>{sender_name}</strong> dari tim Business Development di <strong>Solusi AI Indonesia</strong>.</p><p>Apakah tim Anda di <strong>{company_name}</strong> menghabiskan banyak waktu menjawab pertanyaan pelanggan yang berulang?</p><p>Saya bisa siapkan demo singkat 15 menit untuk menunjukkan cara kerjanya. Apakah hari Selasa atau Kamis sore pekan ini cocok untuk Anda?</p>"""
    return f"""<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><h2 style="color: #1f77b4;">Penawaran AI untuk {company_name}</h2><p>Yth. Bapak/Ibu <strong>{contact_name}</strong>,</p>{email_body}<p>Terima kasih atas waktu dan perhatian Anda.</p><p>Hormat saya,</p><p style="margin-bottom: 0;"><strong>{sender_name}</strong></p><p style="margin-top: 0; margin-bottom: 0;"><em>{sender_title}</em></p><p style="margin-top: 0; margin-bottom: 0;"><a href="https://solusiai.id">solusiai.id</a></p>{f'<p style="margin-top: 0;"><a href="{sender_linkedin}">Profil LinkedIn</a></p>' if sender_linkedin else ""}</div>""".strip()

# --- Halaman & Fungsi Utama ---
def show_login_page():
    st.title("EMI Marketing Tracker 💼📊")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user, error = db.sign_in(email, password)
            if user:
                profile = db.get_profile(user.id)
                if profile:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.profile = profile
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Login berhasil, namun profil pengguna tidak dapat dimuat. Cek RLS pada tabel 'profiles'.")
            else: 
                st.error(f"Login Gagal: {error}")

def show_sidebar():
    with st.sidebar:
        profile = st.session_state.get('profile')
        if not profile:
            st.warning("Sesi tidak valid.")
            if st.button("Kembali ke Login"):
                st.session_state.clear()
                st.rerun()
            return None
        st.title("Menu Navigasi")
        st.write(f"Selamat datang, **{profile.get('full_name', 'User')}**!")
        st.write(f"Role: **{profile.get('role', 'N/A').capitalize()}**")
        st.divider()
        pages = ["Dashboard", "Aktivitas Pemasaran", "Riset Prospek"]
        if profile.get('role') in ['superadmin', 'manager']: pages.append("Manajemen Pengguna")
        if profile.get('role') == 'superadmin': pages.append("Pengaturan")
        page = st.radio("Pilih Halaman:", pages, key="page_selection")
        st.divider()
        if st.button("Logout"):
            clear_all_cache()
            st.session_state.clear()
            st.rerun()
        return page

@st.cache_data(ttl=600)
def get_data_based_on_role():
    user = st.session_state.user
    profile = st.session_state.profile
    role = profile.get('role')
    if role == 'superadmin':
        activities, prospects, profiles = db.get_all_marketing_activities(), db.get_all_prospect_research(), db.get_all_profiles()
    elif role == 'manager':
        activities, prospects, profiles = db.get_team_marketing_activities(user.id), db.get_team_prospect_research(user.id), db.get_team_profiles(user.id)
    else: # marketing
        activities, prospects, profiles = db.get_marketing_activities_by_user_id(user.id), db.get_prospect_research_by_marketer(user.id), [profile]
    return activities, prospects, profiles

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

        st.subheader("Analisis Aktivitas Pemasaran")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            if 'status' in df.columns and not df['status'].empty:
                status_counts = df['status'].map(STATUS_MAPPING).value_counts()
                fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="Distribusi Status Prospek")
                st.plotly_chart(fig, use_container_width=True)
        with col_chart2:
            if 'activity_type' in df.columns and not df['activity_type'].empty:
                type_counts = df['activity_type'].value_counts()
                fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values, title="Distribusi Jenis Aktivitas")
                st.plotly_chart(fig2, use_container_width=True)
        
        st.divider()
        
        # --- BAGIAN "AKTIVITAS TERBARU" DIKEMBALIKAN ---
        st.subheader("Aktivitas Terbaru")
        latest_activities = df.head(5).copy()
        # Periksa apakah 'created_at' ada sebelum menggunakannya
        if 'created_at' in latest_activities.columns:
            latest_activities['Waktu Dibuat'] = latest_activities['created_at'].apply(lambda x: convert_to_wib_and_format(x, format_str='%d %b %Y, %H:%M'))
            display_cols = ['Waktu Dibuat', 'prospect_name', 'marketer_username', 'status']
            if all(col in latest_activities.columns for col in display_cols):
                latest_activities_display = latest_activities[display_cols].rename(columns={'prospect_name': 'Prospek', 'marketer_username': 'Marketing', 'status': 'Status'})
                latest_activities_display['Status'] = latest_activities_display['Status'].map(STATUS_MAPPING)
                st.dataframe(latest_activities_display, use_container_width=True, hide_index=True)
        else:
            st.warning("Data 'created_at' untuk aktivitas terbaru tidak tersedia.")
        
        st.divider()

        # --- BAGIAN "JADWAL FOLLOW-UP" DIKEMBALIKAN ---
        st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
        # Mengambil semua follow-up terkait aktivitas yang sudah di-load
        all_followups = [fu for act in activities if act.get('id') for fu in db.get_followups_by_activity_id(act['id'])]
        
        if not all_followups:
            st.info("Tidak ada jadwal follow-up yang ditemukan.")
        else:
            # Menambahkan nama prospek ke setiap follow-up
            for fu in all_followups:
                fu['prospect_name'] = next((act.get('prospect_name', 'N/A') for act in activities if act.get('id') == fu.get('activity_id')), 'N/A')
            
            followups_df = pd.DataFrame(all_followups)
            # Pastikan kolom tanggal ada sebelum diproses
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
                    st.info("Tidak ada data follow-up dengan tanggal yang valid.")
            else:
                st.warning("Data 'next_followup_date' tidak tersedia.")

    st.divider()

    # --- KODE UNTUK SINKRONISASI APOLLO DIKEMBALIKAN DI SINI ---
    if st.session_state.profile.get('role') in ['superadmin', 'manager']:
        with st.container(border=True):
            st.subheader("Sinkron dari Apollo.io")
            apollo_query = st.text_input("Masukkan query pencarian Apollo.io", placeholder="Contoh: location:indonesia")
            if st.button("Tarik Data", type="primary"):
                if not apollo_query:
                    st.warning("Query pencarian tidak boleh kosong.")
                else:
                    # Kode diagnosis jaringan yang sudah kita buat sebelumnya
                    st.info("Memulai proses sinkronisasi...")
                    try:
                        requests.get("https://www.google.com", timeout=10)
                        st.success("✔️ Koneksi internet dari server: Stabil.")
                        
                        with st.spinner("Menghubungi Apollo.io dan menarik data..."):
                            raw_prospects = db.sync_prospect_from_apollo(apollo_query)
                        
                        if raw_prospects is not None:
                            st.success(f"✔️ Respon diterima. Ditemukan {len(raw_prospects)} prospek dari Apollo.")
                            if raw_prospects:
                                with st.spinner("Menyimpan prospek ke database..."):
                                    saved_count = 0
                                    for p in raw_prospects:
                                        success, _ = db.add_prospect_research(**p)
                                        if success: saved_count += 1
                                    st.success(f"{saved_count} dari {len(raw_prospects)} prospek berhasil disimpan ke 'Riset Prospek'.")
                                clear_all_cache() # Bersihkan cache agar data baru tampil di halaman lain
                                st.rerun()
                            else:
                                st.info("Tidak ada prospek baru yang cocok dengan query Anda.")
                        else:
                            # Jika db.sync_prospect_from_apollo mengembalikan None (karena ada error)
                            st.error("Gagal menarik data. Periksa pesan error di atas bagian ini jika ada.")
                    except requests.exceptions.Timeout:
                        st.error("❌ Koneksi internet dari server timeout. Coba lagi dalam beberapa saat.")
                    except Exception as e:
                        st.error(f"❌ Terjadi kesalahan jaringan tak terduga: {e}")

# --- Halaman Aktivitas Pemasaran ---
def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    activities, _, _ = get_data_based_on_role()
    valid_activities = [act for act in activities if act and act.get('id')]

    if not valid_activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
        st.divider()
        st.subheader("Form Tambah Aktivitas Baru")
        show_activity_form(None)
        return

    st.subheader("Semua Catatan Aktivitas")
    df = pd.DataFrame(valid_activities)
    df_display = df[['activity_date', 'prospect_name', 'prospect_location', 'marketer_username', 'activity_type', 'status']].rename(columns={
        'activity_date': 'Tanggal', 'prospect_name': 'Prospek', 'prospect_location': 'Lokasi',
        'marketer_username': 'Marketing', 'activity_type': 'Jenis', 'status': 'Status'
    })
    df_display['Status'] = df_display['Status'].map(STATUS_MAPPING)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    st.divider()
    options = {act['id']: f"{act.get('prospect_name','N/A')} - {act.get('contact_person', 'N/A')}" for act in valid_activities}
    options[0] = "<< Tambah Aktivitas Baru >>"
    selected_id = st.selectbox("Pilih aktivitas untuk detail/edit:", options.keys(), format_func=lambda x: options.get(x, 'N/A'), index=0, key="activity_select")

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
    with st.form(key=f"activity_form_{'edit' if activity else 'add'}"):
        st.subheader("Detail & Edit Aktivitas" if activity else "Form Aktivitas Baru")
        col1, col2 = st.columns(2)
        with col1:
            prospect_name = st.text_input("Nama Prospek*", value=activity.get('prospect_name', '') if activity else "")
            contact_person = st.text_input("Nama Kontak Person", value=activity.get('contact_person', '') if activity else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity.get('contact_phone', '') if activity else "")
            activity_type = st.selectbox("Jenis Aktivitas", options=ACTIVITY_TYPES, index=ACTIVITY_TYPES.index(activity.get('activity_type')) if activity and activity.get('activity_type') in ACTIVITY_TYPES else 0)
        with col2:
            prospect_location = st.text_input("Lokasi Prospek", value=activity.get('prospect_location', '') if activity else "")
            contact_position = st.text_input("Jabatan Kontak Person", value=activity.get('contact_position', '') if activity else "")
            contact_email = st.text_input("Email Kontak", value=activity.get('contact_email', '') if activity else "")
            default_date = str_to_date(activity.get('activity_date')) if activity else date.today()
            activity_date = st.date_input("Tanggal Aktivitas", value=default_date)
        
        status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity.get('status', 'baru'))) if activity else 0)
        description = st.text_area("Deskripsi", value=activity.get('description', '') if activity else "", height=150)
        
        submitted = st.form_submit_button("Simpan")
        if submitted:
            if not prospect_name:
                st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING.get(status_display)
                if activity:
                    success, msg = db.edit_marketing_activity(
                        activity_id=activity['id'], 
                        prospect_name=prospect_name, prospect_location=prospect_location, 
                        contact_person=contact_person, contact_position=contact_position, 
                        contact_phone=contact_phone, contact_email=contact_email, 
                        activity_date=date_to_str(activity_date), activity_type=activity_type, 
                        description=description, status=status_key
                    )
                else:
                    success, msg, _ = db.add_marketing_activity(
                        marketer_id=user.id, marketer_username=profile.get('full_name'), 
                        prospect_name=prospect_name, prospect_location=prospect_location, 
                        contact_person=contact_person, contact_position=contact_position, 
                        contact_phone=contact_phone, contact_email=contact_email, 
                        activity_date=date_to_str(activity_date), activity_type=activity_type, 
                        description=description, status=status_key
                    )
                if success:
                    st.success(msg)
                    clear_all_cache()
                    st.rerun()
                else:
                    st.error(msg)


def show_followup_section(activity):
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity.get('prospect_name', 'N/A')}")
    followups = db.get_followups_by_activity_id(activity['id'])
    if followups:
        for fu in reversed(followups):
            st.markdown(f"**{convert_to_wib_and_format(fu.get('created_at'))} oleh {fu.get('marketer_username', 'N/A')}**: {fu.get('notes', 'N/A')}")
    with st.form("new_followup_form", clear_on_submit=True):
        notes = st.text_area("Catatan Follow-up Baru*:")
        next_action = st.text_input("Rencana Tindak Lanjut")
        next_followup_date = st.date_input("Jadwal Berikutnya", value=None)
        interest_level = st.select_slider("Tingkat Ketertarikan", options=["Rendah", "Sedang", "Tinggi"], value="Sedang")
        current_status_display = STATUS_MAPPING.get(activity.get('status', 'baru'))
        new_status_display = st.selectbox("Update Status Prospek", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(current_status_display))
        submitted = st.form_submit_button("Simpan Follow-up")
        if submitted:
            if not notes:
                st.warning("Catatan tidak boleh kosong.")
            else:
                success, msg = db.add_followup(
                    activity_id=activity['id'],
                    marketer_id=st.session_state.user.id,
                    marketer_username=st.session_state.profile.get('full_name'),
                    notes=notes,
                    next_action=next_action,
                    next_followup_date=next_followup_date,
                    interest_level=interest_level,
                    status_update=REVERSE_STATUS_Mッピング.get(new_status_display)
                )
                if success:
                    st.success(msg)
                    clear_all_cache()
                    st.rerun()
                else:
                    st.error(msg)

# Ganti dengan ini di app_supabase.py
def page_prospect_research():
    st.title("Riset Prospek 🔍💼")
    # Mengambil data berdasarkan role pengguna
    _, prospects, _ = get_data_based_on_role()
    profile = st.session_state.profile

    # Inisialisasi session state untuk preview template email
    if 'preview_content' not in st.session_state: st.session_state.preview_content = ""
    if 'last_selected_id' not in st.session_state: st.session_state.last_selected_id = 0

    st.subheader("Cari Prospek")
    search_query = st.text_input("Ketik nama perusahaan, kontak, industri, atau lokasi untuk mencari...")
    filtered_prospects = db.search_prospect_research(search_query) if search_query else prospects

    st.divider()
    st.subheader("Daftar Prospek")
    if not filtered_prospects:
        st.info("Belum ada data prospek yang ditemukan.")
    else:
        df_prospect = pd.DataFrame(filtered_prospects)
        display_cols = ['company_name', 'contact_name', 'industry', 'status']
        # Memastikan kolom yang ditampilkan ada di dataframe untuk mencegah error
        display_cols_exist = [col for col in display_cols if col in df_prospect.columns]
        st.dataframe(df_prospect[display_cols_exist].rename(columns={'company_name': 'Perusahaan', 'contact_name': 'Kontak', 'industry': 'Industri', 'status': 'Status'}), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Pilih Prospek untuk Detail/Edit atau Tambah Baru")
    options = {p['id']: f"{p.get('company_name', 'N/A')} - {p.get('contact_name', 'N/A')}" for p in filtered_prospects}
    options[0] = "<< Tambah Prospek Baru >>"
    selected_id = st.selectbox("Pilih Prospek:", options.keys(), format_func=lambda x: options.get(x, 'N/A'), index=0, key="prospect_select")

    # Logika untuk mereset preview template email jika pilihan berubah
    if st.session_state.last_selected_id != selected_id:
        st.session_state.preview_content = ""
        st.session_state.last_selected_id = selected_id

    # === FORM TAMBAH PROSPEK BARU (LENGKAP) ===
    if selected_id == 0:
        st.subheader("Form Tambah Prospek Baru")
        with st.form("add_prospect_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Nama Perusahaan*")
                website = st.text_input("Website")
                industry = st.text_input("Industri")
                founded_year = st.number_input("Tahun Berdiri", min_value=1900, max_value=datetime.now().year + 1, step=1, value=2000)
                company_size = st.text_input("Jumlah Karyawan (Contoh: 51-200)")
                revenue = st.text_input("Pendapatan Tahunan (Contoh: $10M)")
            with col2:
                contact_name = st.text_input("Nama Kontak")
                contact_title = st.text_input("Jabatan")
                contact_email = st.text_input("Email Kontak")
                linkedin_url = st.text_input("URL LinkedIn Kontak")
                phone = st.text_input("Nomor Telepon Kontak")
                location = st.text_input("Lokasi Kantor (Kota/Negara)")
            
            st.subheader("Detail Tambahan")
            notes = st.text_area("Catatan Mengenai Prospek")
            next_step = st.text_input("Rencana Langkah Selanjutnya")
            next_step_date = st.date_input("Tanggal Follow-up Selanjutnya", value=None)
            status = st.selectbox("Status Prospek", ["baru", "dalam_proses", "berhasil", "gagal"], index=0)
            source = st.text_input("Sumber Prospek", value="manual")

            submitted = st.form_submit_button("Simpan Prospek Baru")
            if submitted:
                if not company_name:
                    st.error("Nama Perusahaan wajib diisi!")
                else:
                    success, msg = db.add_prospect_research(
                        company_name=company_name, website=website, industry=industry, 
                        founded_year=founded_year, company_size=company_size, revenue=revenue, 
                        location=location, contact_name=contact_name, contact_title=contact_title, 
                        contact_email=contact_email, linkedin_url=linkedin_url, phone=phone, 
                        notes=notes, next_step=next_step, next_step_date=date_to_str(next_step_date), 
                        status=status, source=source, 
                        marketer_id=st.session_state.user.id, marketer_username=profile.get("full_name")
                    )
                    if success:
                        st.success(msg)
                        clear_all_cache() # Hapus cache agar daftar prospek diperbarui
                    else:
                        st.error(msg)
    
    # === FORM EDIT PROSPEK (LENGKAP) ===
    else:
        prospect = db.get_prospect_by_id(selected_id)
        if prospect:
            st.subheader(f"Edit Prospek: {prospect.get('company_name')}")
            with st.form(f"edit_prospect_form_{selected_id}"):
                col1, col2 = st.columns(2)
                with col1:
                    company_name = st.text_input("Nama Perusahaan*", value=prospect.get('company_name', ''))
                    website = st.text_input("Website", value=prospect.get('website', ''))
                    industry = st.text_input("Industri", value=prospect.get('industry', ''))
                    founded_year = st.number_input("Tahun Berdiri", min_value=1900, max_value=datetime.now().year + 1, step=1, value=prospect.get('founded_year') or 2000)
                    company_size = st.text_input("Jumlah Karyawan", value=prospect.get('company_size', ''))
                    revenue = st.text_input("Pendapatan Tahunan", value=prospect.get('revenue', ''))
                with col2:
                    contact_name = st.text_input("Nama Kontak", value=prospect.get('contact_name', ''))
                    contact_title = st.text_input("Jabatan", value=prospect.get('contact_title', ''))
                    contact_email = st.text_input("Email Kontak", value=prospect.get('contact_email', ''))
                    linkedin_url = st.text_input("URL LinkedIn Kontak", value=prospect.get('linkedin_url', ''))
                    phone = st.text_input("Nomor Telepon Kontak", value=prospect.get('phone', ''))
                    location = st.text_input("Lokasi Kantor", value=prospect.get('location', ''))

                notes = st.text_area("Catatan Mengenai Prospek", value=prospect.get('notes', ''))
                next_step = st.text_input("Rencana Langkah Selanjutnya", value=prospect.get('next_step', ''))
                next_step_date = st.date_input("Tanggal Follow-up Selanjutnya", value=str_to_date(prospect.get('next_step_date')))
                
                status_options = ["baru", "dalam_proses", "berhasil", "gagal"]
                status = st.selectbox("Status Prospek", status_options, index=status_options.index(prospect.get('status', 'baru')) if prospect.get('status') in status_options else 0)
                source = st.text_input("Sumber Prospek", value=prospect.get('source', 'manual'))
                
                submitted = st.form_submit_button("Simpan Perubahan")
                if submitted:
                    success, msg = db.edit_prospect_research(
                        prospect_id=selected_id,
                        company_name=company_name, website=website, industry=industry,
                        founded_year=founded_year, company_size=company_size, revenue=revenue,
                        location=location, contact_name=contact_name, contact_title=contact_title,
                        contact_email=contact_email, linkedin_url=linkedin_url, phone=phone,
                        notes=notes, next_step=next_step, next_step_date=date_to_str(next_step_date),
                        status=status, source=source
                    )
                    if success:
                        st.success(msg)
                        clear_all_cache() # Hapus cache untuk update
                        st.rerun()
                    else:
                        st.error(msg)
            
            # --- Bagian Template Email ---
            st.divider()
            st.subheader("Template Email Profesional (Terkait Prospek ini)")
            html_template = generate_html_email_template(prospect, user_profile=profile)
            edited_html = st.text_area("Edit Template Email", value=html_template, height=300, key=f"editor_{selected_id}")
            
            if st.button("Kirim via Zoho", key=f"send_zoho_{selected_id}"):
                with st.spinner("Mengirim email via Zoho..."):
                    # Anda mungkin perlu menyesuaikan "from_email"
                    success, msg = db.send_email_via_zoho({"to": prospect.get("contact_email"), "subject": f"Penawaran AI untuk {prospect.get('company_name')}", "content": edited_html, "from": st.secrets.get("zoho", {}).get("from_email", "default_email@anda.com")})
                    if success: st.success(msg)
                    else: st.error(msg)

# Ganti dengan ini di app_supabase.py
def page_user_management():
    st.title("Manajemen Pengguna")
    profile = st.session_state.profile
    user = st.session_state.user

    # Verifikasi hak akses
    if profile.get('role') not in ['superadmin', 'manager']:
        st.error("Anda tidak memiliki akses ke halaman ini.")
        return

    if profile.get('role') == 'superadmin':
        profiles_data = db.get_all_profiles()
    else:  # Asumsi role manager
        profiles_data = db.get_team_profiles(user.id)

    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        st.subheader("Daftar Pengguna Saat Ini")
        if profiles_data:
            df = pd.DataFrame(profiles_data)
            # Menangani kolom manager yang mungkin tidak ada atau None
            if 'manager' in df.columns:
                df['Nama Manajer'] = df['manager'].apply(lambda x: x['full_name'] if isinstance(x, dict) and x else 'N/A')
            else:
                df['Nama Manajer'] = 'N/A'
            
            display_cols = ['id', 'full_name', 'email', 'role', 'Nama Manajer']
            df_display = df[[col for col in display_cols if col in df.columns]]
            st.dataframe(df_display.rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role', 'email': 'Email'}), use_container_width=True)
        else:
            st.info("Tidak ada pengguna untuk ditampilkan.")

    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        with st.form("add_user_form", clear_on_submit=True):
            full_name = st.text_input("Nama Lengkap*")
            email = st.text_input("Email*")
            password = st.text_input("Password*", type="password")
            
            role_options = ["manager", "marketing"] if profile.get('role') == 'superadmin' else ["marketing"]
            role = st.selectbox("Role*", role_options)
            
            manager_id = None
            if role == 'marketing':
                if profile.get('role') == 'superadmin':
                    managers = db.get_all_managers()
                    if not managers:
                        st.warning("Belum ada Manajer terdaftar. Harap buat pengguna dengan role 'manager' terlebih dahulu.")
                    else:
                        manager_options = {mgr['id']: mgr['full_name'] for mgr in managers}
                        manager_id = st.selectbox("Pilih Manajer*", options=manager_options.keys(), format_func=lambda x: manager_options.get(x, 'N/A'))
                else: # Jika yang menambah adalah manager
                    manager_id = user.id
                    st.info(f"Anda ({profile.get('full_name')}) akan otomatis menjadi manajer untuk pengguna baru ini.")
            
            submitted = st.form_submit_button("Daftarkan Pengguna Baru")
            if submitted:
                if not all([full_name, email, password]):
                    st.error("Field dengan tanda bintang (*) wajib diisi!")
                else:
                    new_user, error = db.create_user_as_admin(email, password, full_name, role, manager_id)
                    if new_user:
                        st.success(f"Pengguna {full_name} berhasil didaftarkan.")
                        clear_all_cache() # Hapus cache agar daftar pengguna diperbarui
                        st.rerun() # Tidak perlu, karena form sudah clear_on_submit
                    else:
                        st.error(f"Gagal mendaftarkan: {error}")

# Ganti dengan ini di app_supabase.py
def page_settings():
    st.title("Pengaturan Aplikasi")
    
    # Bagian Konfigurasi Aplikasi
    config = db.get_app_config()
    with st.form("config_form"):
        st.subheader("Konfigurasi Umum")
        app_name = st.text_input("Nama Aplikasi", value=config.get('app_name', 'EMI Marketing Tracker'))
        if st.form_submit_button("Simpan Pengaturan"):
            if not app_name:
                st.error("Nama aplikasi wajib diisi!")
            else:
                success, msg = db.update_app_config({'app_name': app_name})
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    st.divider()
    
    # Bagian Integrasi Zoho Mail
    st.subheader("Pengaturan Integrasi Zoho Mail")
    if "zoho" in st.secrets and st.secrets.get("zoho", {}).get("access_token"):
        st.success("Integrasi Zoho Mail Aktif.")
    else:
        st.warning("Integrasi Zoho Mail belum aktif. Silakan generate token awal.")
    st.write("Jika Anda perlu generate token untuk pertama kali atau jika refresh otomatis gagal, gunakan form di bawah ini.")
    
    with st.form("zoho_auth_form"):
        st.write("#### Langkah 1: Ambil Code dari Zoho")
        auth_url = get_authorization_url()
        st.markdown(f"[Klik di sini untuk mengizinkan akses Zoho Mail]({auth_url})")
        st.info("Setelah klik 'Accept', salin 'code' dari URL di browser Anda dan tempel di bawah.")
        code = st.text_input("Masukkan code dari Zoho:")
        if st.form_submit_button("Generate Access Token"):
            if not code:
                st.warning("Silakan masukkan code dari Zoho.")
            else:
                with st.spinner("Sedang menukar kode dengan token..."):
                    success, msg = db.exchange_code_for_tokens(code)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

# Jangan lupa untuk juga merekonstruksi `get_authorization_url()` jika hilang
def get_authorization_url():
    if "zoho" in st.secrets:
        zoho_secrets = st.secrets.get("zoho", {})
        params = {
            "response_type": "code", 
            "client_id": zoho_secrets.get("client_id"), 
            "scope": "ZohoMail.send,ZohoMail.read", 
            "redirect_uri": zoho_secrets.get("redirect_uri", "https://emimtsupabase.streamlit.app/")
        }
        base_url = "https://accounts.zoho.com/oauth/v2/auth?"
        # Pastikan tidak ada parameter None yang dikirim
        return base_url + urlencode({k: v for k, v in params.items() if v})
    return "#"

def get_authorization_url():
    if "zoho" in st.secrets:
        params = {"response_type": "code", "client_id": st.secrets["zoho"].get("client_id"), "scope": "ZohoMail.send,ZohoMail.read", "redirect_uri": st.secrets["zoho"].get("redirect_uri")}
        return "https://accounts.zoho.com/oauth/v2/auth?" + urlencode({k: v for k, v in params.items() if v is not None})
    return "#"

def main():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.get("logged_in"):
        show_login_page()
    else:
        page = show_sidebar()
        if page:
            if page == "Dashboard": page_dashboard()
            elif page == "Aktivitas Pemasaran": page_activities_management()
            elif page == "Riset Prospek": page_prospect_research()
            elif page == "Manajemen Pengguna": page_user_management()
            elif page == "Pengaturan": page_settings()

if __name__ == "__main__":
    main()