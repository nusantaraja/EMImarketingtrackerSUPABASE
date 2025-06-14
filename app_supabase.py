import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db_supabase as db
import pytz
import json

# --- Konfigurasi Halaman & Variabel Global ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")
STATUS_MAPPING = {"baru": "Baru", "dalam_proses": "Dalam Proses", "berhasil": "Berhasil", "gagal": "Gagal"}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Fungsi Helper untuk Waktu ---
def convert_to_wib_and_format(iso_string, format_str=\'%A, %d %b %Y, %H:%M\'):
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
        st.write(f"Selamat datang, **{profile.get(\'full_name\', \'User\')}**!")
        st.write(f"Role: **{profile.get(\'role\', \'N/A\').capitalize()}**")
        st.divider()

        # Daftar halaman utama
        pages = ["Dashboard", "Aktivitas Pemasaran", "Riset Prospek"]
        if profile.get(\'role\') == \'superadmin\':
            pages.extend(["Manajemen Pengguna", "Pengaturan"])

        page = st.radio("Pilih Halaman:", pages)
        st.divider()

        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        return page


def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get(\'role\', \'\').capitalize()}")
    user = st.session_state.user
    profile = st.session_state.profile

    activities = db.get_all_marketing_activities() if profile.get(\'role\') == \'superadmin\' else db.get_marketing_activities_by_user_id(user.id)
    
    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df[\'prospect_name\'].nunique())
    if profile.get(\'role\') == \'superadmin\':
        col3.metric("Jumlah Tim Marketing", df[\'marketer_id\'].nunique())

    st.divider()
    st.subheader("Analisis Aktivitas Pemasaran")

    col1, col2 = st.columns(2)
    with col1:
        status_counts = df[\'status\'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index,
                     title="Distribusi Status Prospek", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        type_counts = df[\'activity_type\'].value_counts()
        fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values,
                      title="Distribusi Jenis Aktivitas", labels={\'x\': \'Jenis Aktivitas\', \'y\': \'Jumlah\'})
        st.plotly_chart(fig2, use_container_width=True)

    if profile.get(\'role\') == \'superadmin\':
        col3, col4 = st.columns(2)
        with col3:
            location_counts = df[\'prospect_location\'].str.strip().str.title().value_counts().nlargest(10)
            fig3 = px.bar(location_counts, x=location_counts.index, y=location_counts.values,
                          title="Top 10 Lokasi Prospek", labels={\'x\': \'Kota/Lokasi\', \'y\': \'Jumlah Prospek\'})
            st.plotly_chart(fig3, use_container_width=True)
        with col4:
            marketer_counts = df[\'marketer_username\'].value_counts()
            fig4 = px.bar(marketer_counts, x=marketer_counts.index, y=marketer_counts.values,
                          title="Aktivitas per Marketing", labels={\'x\': \'Nama Marketing\', \'y\': \'Jumlah Aktivitas\'},
                          color=marketer_counts.values, color_continuous_scale=px.colors.sequential.Viridis)
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("Aktivitas Terbaru")
    latest_activities = df.head(5).copy()
    latest_activities[\'Waktu Dibuat\'] = latest_activities[\'created_at\'].apply(lambda x: convert_to_wib_and_format(x, format_str=\'%d %b %Y, %H:%M\'))
    display_cols = [\'Waktu Dibuat\', \'prospect_name\', \'marketer_username\', \'status\']
    latest_activities_display = latest_activities[display_cols].rename(columns={
        \'prospect_name\': \'Prospek\', \'marketer_username\': \'Marketing\', \'status\': \'Status\'
    })
    latest_activities_display[\'Status\'] = latest_activities_display[\'Status\'].map(STATUS_MAPPING)
    st.dataframe(latest_activities_display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
    all_followups = [fu for act in activities for fu in db.get_followups_by_activity_id(act[\'id\'])]
    if not all_followups:
        st.info("Tidak ada jadwal follow-up yang ditemukan.")
    else:
        for fu in all_followups:
            fu[\'prospect_name\'] = next((act[\'prospect_name\'] for act in activities if act[\'id\'] == fu[\'activity_id\']), \'N/A\')
        followups_df = pd.DataFrame(all_followups)
        followups_df[\'next_followup_date\'] = pd.to_datetime(followups_df[\'next_followup_date\'], utc=True)
        wib_tz = pytz.timezone("Asia/Jakarta")
        today = pd.Timestamp.now(tz=wib_tz).normalize()
        next_7_days = today + pd.Timedelta(days=7)
        upcoming_df = followups_df[
            (followups_df[\'next_followup_date\'] >= today) &
            (followups_df[\'next_followup_date\'] <= next_7_days)
        ].sort_values(by=\'next_followup_date\')

        if not upcoming_df.empty:
            display_cols_fu = [\'next_followup_date\', \'prospect_name\', \'marketer_username\', \'next_action\']
            upcoming_display_df = upcoming_df[display_cols_fu].rename(columns={
                \'next_followup_date\': \'Tanggal\', \'prospect_name\': \'Prospek\',
                \'marketer_username\': \'Marketing\', \'next_action\': \'Tindakan\'
            })
            upcoming_display_df[\'Tanggal\'] = upcoming_display_df[\'Tanggal\'].dt.tz_convert(wib_tz).dt.strftime(\'%A, %d %b %Y\')
            st.dataframe(upcoming_display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada jadwal follow-up dalam 7 hari ke depan.")

    # --- Sinkron dari Apollo.io (Superadmin Only) ---
    st.divider()
    st.subheader("Sinkron dari Apollo.io")
    
    if profile.get(\'role\') == \'superadmin\':
        st.write("Masukkan filter pencarian dalam format JSON (misal: `{\"q_organization_industries\": [\"Technology\"], \"organization_locations\": [\"Jakarta\"]}`)")
        apollo_filters_input = st.text_area("Filter Apollo.io", height=100, value="{}")
        if st.button("Tarik Data dari Apollo.io"):
            try:
                apollo_filters = json.loads(apollo_filters_input)
                with st.spinner("Menarik data dari Apollo.io..."):
                    raw_prospects = db.sync_prospect_from_apollo(apollo_filters)
                    if raw_prospects:
                        saved_count = 0
                        for p in raw_prospects:
                            p["marketer_id"] = st.session_state.user.id
                            p["marketer_username"] = st.session_state.profile.get("full_name")

                            success, msg = db.add_prospect_research(**p)
                            if success:
                                saved_count += 1

                        st.success(f"{saved_count} prospek berhasil ditarik dan disimpan.")
                        st.rerun()
                    else:
                        st.info("Tidak ada prospek baru yang ditemukan.")
            except json.JSONDecodeError:
                st.error("Format filter JSON tidak valid. Pastikan input Anda adalah JSON yang benar.")
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
    else:
        st.warning("Fitur ini hanya tersedia untuk superadmin.")


def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    profile = st.session_state.profile
    user = st.session_state.user
    activities = db.get_all_marketing_activities() if profile.get(\'role\') == \'superadmin\' else db.get_marketing_activities_by_user_id(user.id)

    if not activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    st.subheader("Semua Catatan Aktivitas")
    if \'page_num\' not in st.session_state:
        st.session_state.page_num = 1
    items_per_page = 30
    total_items = len(df)
    total_pages = max(1, (total_items // items_per_page) + (1 if total_items % items_per_page > 0 else 0))

    start_idx = (st.session_state.page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = df.iloc[start_idx:end_idx]

    if not paginated_df.empty:
        display_cols = [\'activity_date\', \'prospect_name\', \'prospect_location\', \'marketer_username\', \'activity_type\', \'status\']
        paginated_df_display = paginated_df[display_cols].rename(columns={
            \'activity_date\': \'Tanggal\', \'prospect_name\': \'Prospek\', \'prospect_location\': \'Lokasi\',
            \'marketer_username\': \'Marketing\', \'activity_type\': \'Jenis\', \'status\': \'Status\'
        })
        paginated_df_display[\'Status\'] = paginated_df_display[\'Status\'].map(STATUS_MAPPING)
        st.dataframe(paginated_df_display, use_container_width=True, hide_index=True)

    st.divider()
    col_nav1, col_nav2, col_nav3 = st.columns([3, 2, 3])
    with col_nav1:
        if st.button("⬅️ PREVIOUS", disabled=(st.session_state.page_num <= 1)):
            st.session_state.page_num -= 1
            st.rerun()
    with col_nav2:
        st.write(f"<div style=\'text-align: center; margin-top: 5px;\'>Halaman <b>{st.session_state.page_num}</b> dari <b>{total_pages}</b></div>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("NEXT ➡️", disabled=(st.session_state.page_num >= total_pages)):
            st.session_state.page_num += 1
            st.rerun()

    st.divider()
    options = {act[\'id\']: f"{act[\'prospect_name\']} - {act[\'contact_person\'] or \'N/A\'}" for act in activities}
    options[0] = "<< Pilih ID untuk Detail / Edit >>"
    selected_id = st.selectbox("Pilih aktivitas untuk melihat detail:", options.keys(), format_func=lambda x: options[x], index=0)

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
            prospect_name = st.text_input("Nama Prospek*", value=activity.get(\'prospect_name\', \'\') if activity else "")
            contact_person = st.text_input("Nama Kontak Person", value=activity.get(\'contact_person\', \'\') if activity else "")
            contact_position = st.text_input("Jabatan Kontak Person", value=activity.get(\'contact_position\', \'\') if activity else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity.get(\'contact_phone\', \'\') if activity else "")
        with col2:
            prospect_location = st.text_input("Lokasi Prospek", value=activity.get(\'prospect_location\', \'\') if activity else "")
            contact_email = st.text_input("Email Kontak", value=activity.get(\'contact_email\', \'\') if activity else "")
            default_date = datetime.strptime(activity[\'activity_date\'], \'%Y-%m-%d\') if activity and activity.get(\'activity_date\') else datetime.today()
            activity_date = st.date_input("Tanggal Aktivitas", value=default_date)
        activity_type = st.selectbox("Jenis Aktivitas", options=ACTIVITY_TYPES, index=ACTIVITY_TYPES.index(activity[\'activity_type\']) if activity and activity.get(\'activity_type\') in ACTIVITY_TYPES else 0)
        status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity[\'status\'], \'baru\')) if activity else 0)
        description = st.text_area("Deskripsi", value=activity.get(\'description\', \'\') if activity else "", height=150)
        submitted = st.form_submit_button(button_label)
        if submitted:
            if not prospect_name:
                st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING[status_display]
                if activity:
                    success, msg = db.edit_marketing_activity(
                        activity[\'id\'],
                        prospect_name,
                        prospect_location,
                        contact_person,
                        contact_position,
                        contact_phone,
                        contact_email,
                        activity_date,
                        activity_type,
                        description,
                        status_key
                    )
                else:
                    success, msg, new_id = db.add_marketing_activity(
                        user.id,
                        profile.get(\'full_name\'),
                        prospect_name,
                        prospect_location,
                        contact_person,
                        contact_position,
                        contact_phone,
                        contact_email,
                        activity_date,
                        activity_type,
                        description,
                        status_key
                    )

                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    if activity and profile.get(\'role\') == \'superadmin\':
        if st.button("Hapus Aktivitas Ini", type="primary"):
            success, msg = db.delete_marketing_activity(activity[\'id\'])
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def show_followup_section(activity):
    st.divider()
    st.subheader(f"Riwayat & Tambah Follow-up untuk {activity[\'prospect_name\']}")
    followups = db.get_followups_by_activity_id(activity[\'id\'])
    if followups:
        for fu in followups:
            fu_time_display = fu.get(\'created_at\', \'Waktu tidak tersedia\')
            if fu.get(\'created_at\'):
                try:
                    fu_time_display = convert_to_wib_and_format(fu[\'created_at\'])
                except Exception:
                    pass
            with st.container(border=True):
                st.markdown(f"**{fu_time_display} WIB oleh {fu[\'marketer_username\']}**")
                st.markdown(f"**Catatan:** {fu[\'notes\']}")
                st.caption(f"Tindak Lanjut: {fu.get(\'next_action\', \'N/A\')} | Jadwal: {fu.get(\'next_followup_date\', \'N/A\')} | Minat: {fu.get(\'interest_level\', \'N/A\')}")

    else:
        st.caption("Belum ada follow-up untuk aktivitas ini.")

    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up", height=100)
        col_fu1, col_fu2, col_fu3 = st.columns(3)
        with col_fu1:
            next_action = st.text_input("Tindakan Selanjutnya")
        with col_fu2:
            next_followup_date = st.date_input("Tanggal Follow-up Selanjutnya", value=datetime.today())
        with col_fu3:
            interest_level = st.selectbox("Tingkat Minat", ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"])
        status_update = st.selectbox("Perbarui Status Aktivitas", ["Tidak Diperbarui"] + list(STATUS_MAPPING.values()))
        
        submitted_fu = st.form_submit_button("Simpan Follow-up")
        if submitted_fu:
            status_key_fu = REVERSE_STATUS_MAPPING[status_update] if status_update != "Tidak Diperbarui" else None
            success, msg = db.add_followup(
                activity[\'id\'],
                user.id,
                profile.get(\'full_name\'),
                notes,
                next_action,
                next_followup_date,
                interest_level,
                status_key_fu
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def page_prospect_research():
    st.title("Riset Prospek")
    profile = st.session_state.profile
    user = st.session_state.user

    if profile.get(\'role\') == \'superadmin\':
        prospects = db.get_all_prospect_research()
    else:
        prospects = db.get_prospect_research_by_marketer(user.id)

    if not prospects:
        st.info("Belum ada data prospek. Silakan tambahkan prospek baru.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(prospects)

    st.subheader("Daftar Prospek")
    search_keyword = st.text_input("Cari Prospek (Nama Perusahaan, Kontak, Industri, Lokasi)")
    if search_keyword:
        df = pd.DataFrame(db.search_prospect_research(search_keyword))

    if not df.empty:
        display_cols = [\'company_name\', \'contact_name\', \'industry\', \'location\', \'status\', \'marketer_username\', \'created_at\']
        df_display = df[display_cols].rename(columns={
            \'company_name\': \'Perusahaan\', \'contact_name\': \'Kontak\', \'industry\': \'Industri\',
            \'location\': \'Lokasi\', \'status\': \'Status\', \'marketer_username\': \'Marketing\', \'created_at\': \'Dibuat Pada\'
        })
        df_display[\'Status\'] = df_display[\'Status\'].map(STATUS_MAPPING)
        df_display[\'Dibuat Pada\'] = df_display[\'Dibuat Pada\'].apply(lambda x: convert_to_wib_and_format(x, format_str=\'%d %b %Y, %H:%M\'))
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    options = {p[\'id\']: f"{p[\'company_name\']} - {p[\'contact_name\'] or \'N/A\'}" for p in prospects}
    options[0] = "<< Pilih ID untuk Detail / Edit >>"
    selected_prospect_id = st.selectbox("Pilih prospek untuk melihat detail:", options.keys(), format_func=lambda x: options[x], index=0)

    if selected_prospect_id == 0:
        st.subheader("Form Tambah Prospek Baru")
        show_prospect_form(None)
    else:
        prospect = db.get_prospect_by_id(selected_prospect_id)
        if prospect:
            show_prospect_form(prospect)


def show_prospect_form(prospect):
    form_title = "Detail & Edit Prospek" if prospect else "Form Prospek Baru"
    button_label = "Simpan Perubahan" if prospect else "Simpan Prospek Baru"
    profile = st.session_state.profile
    user = st.session_state.user

    with st.form(key="prospect_form"):
        st.subheader(form_title)
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Nama Perusahaan*", value=prospect.get(\'company_name\', \'\') if prospect else "")
            website = st.text_input("Website", value=prospect.get(\'website\', \'\') if prospect else "")
            industry = st.text_input("Industri", value=prospect.get(\'industry\', \'\') if prospect else "")
            founded_year = st.text_input("Tahun Berdiri", value=prospect.get(\'founded_year\', \'\') if prospect else "")
            company_size = st.text_input("Ukuran Perusahaan (Jumlah Karyawan)", value=prospect.get(\'company_size\', \'\') if prospect else "")
            revenue = st.text_input("Pendapatan Tahunan", value=prospect.get(\'revenue\', \'\') if prospect else "")
            location = st.text_input("Lokasi", value=prospect.get(\'location\', \'\') if prospect else "")
        with col2:
            contact_name = st.text_input("Nama Kontak", value=prospect.get(\'contact_name\', \'\') if prospect else "")
            contact_title = st.text_input("Jabatan Kontak", value=prospect.get(\'contact_title\', \'\') if prospect else "")
            contact_email = st.text_input("Email Kontak", value=prospect.get(\'contact_email\', \'\') if prospect else "")
            linkedin_url = st.text_input("LinkedIn URL", value=prospect.get(\'linkedin_url\', \'\') if prospect else "")
            phone = st.text_input("Telepon", value=prospect.get(\'phone\', \'\') if prospect else "")
            keywords = st.multiselect("Kata Kunci", options=["Technology", "Finance", "Healthcare", "Education", "Retail", "Manufacturing", "Services"], default=prospect.get(\'keywords\', []) if prospect else [])
            technology_used = st.multiselect("Teknologi Digunakan", options=["CRM", "ERP", "Cloud", "AI", "Marketing Automation"], default=prospect.get(\'technology_used\', []) if prospect else [])
        notes = st.text_area("Catatan", value=prospect.get(\'notes\', \'\') if prospect else "", height=100)
        col_next1, col_next2, col_next3 = st.columns(3)
        with col_next1:
            next_step = st.text_input("Langkah Selanjutnya", value=prospect.get(\'next_step\', \'\') if prospect else "")
        with col_next2:
            default_next_step_date = datetime.strptime(prospect[\'next_step_date\'], \'%Y-%m-%d\') if prospect and prospect.get(\'next_step_date\') else datetime.today()
            next_step_date = st.date_input("Tanggal Langkah Selanjutnya", value=default_next_step_date)
        with col_next3:
            status_prospect = st.selectbox("Status Prospek", options=list(STATUS_MAPPING.values()), index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(prospect[\'status\'], \'baru\')) if prospect else 0)
        
        decision_maker = st.checkbox("Decision Maker", value=prospect.get(\'decision_maker\', False) if prospect else False)
        email_status = st.selectbox("Status Email", ["valid", "invalid", "unknown"], index=["valid", "invalid", "unknown"].index(prospect.get(\'email_status\', \'valid\')) if prospect else 0)

        submitted = st.form_submit_button(button_label)
        if submitted:
            if not company_name:
                st.error("Nama Perusahaan wajib diisi!")
            else:
                status_key_prospect = REVERSE_STATUS_MAPPING[status_prospect]
                prospect_data = {
                    "company_name": company_name,
                    "website": website,
                    "industry": industry,
                    "founded_year": founded_year,
                    "company_size": company_size,
                    "revenue": revenue,
                    "location": location,
                    "contact_name": contact_name,
                    "contact_title": contact_title,
                    "contact_email": contact_email,
                    "linkedin_url": linkedin_url,
                    "phone": phone,
                    "keywords": keywords,
                    "technology_used": technology_used,
                    "notes": notes,
                    "next_step": next_step,
                    "next_step_date": next_step_date,
                    "status": status_key_prospect,
                    "decision_maker": decision_maker,
                    "email_status": email_status,
                    "marketer_id": user.id,
                    "marketer_username": profile.get(\'full_name\')
                }

                if prospect:
                    success, msg = db.edit_prospect_research(prospect[\'id\'], **prospect_data)
                else:
                    success, msg = db.add_prospect_research(**prospect_data)

                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    if prospect and profile.get(\'role\') == \'superadmin\':
        if st.button("Hapus Prospek Ini", type="primary"):
            # db.delete_prospect_research(prospect["id"])
            st.warning("Fitur hapus prospek sedang dalam pengembangan.")


def page_user_management():
    st.title("Manajemen Pengguna")
    profile = st.session_state.profile

    if profile.get(\'role\') != \'superadmin\':
        st.warning("Anda tidak memiliki akses ke halaman ini.")
        return

    st.subheader("Daftar Pengguna")
    users = db.get_all_profiles()
    if users:
        df = pd.DataFrame(users)
        st.dataframe(df[["full_name", "email", "role", "created_at"]], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Tambah Pengguna Baru")
        with st.form("add_user_form"):
            email = st.text_input("Email Pengguna Baru")
            password = st.text_input("Password Pengguna Baru", type="password")
            full_name = st.text_input("Nama Lengkap Pengguna Baru")
            role = st.selectbox("Role", ["marketer", "superadmin"])
            if st.form_submit_button("Tambah Pengguna"):
                if email and password and full_name and role:
                    user, error = db.sign_up(email, password, full_name, role)
                    if user:
                        st.success(f"Pengguna {full_name} ({email}) berhasil ditambahkan.")
                        st.rerun()
                    else:
                        st.error(f"Gagal menambahkan pengguna: {error}")
                else:
                    st.error("Semua field wajib diisi.")
    else:
        st.info("Belum ada pengguna terdaftar.")


def page_settings():
    st.title("Pengaturan Aplikasi")
    profile = st.session_state.profile

    if profile.get(\'role\') != \'superadmin\':
        st.warning("Anda tidak memiliki akses ke halaman ini.")
        return

    config = db.get_app_config()
    st.subheader("Konfigurasi Umum")
    with st.form("app_config_form"):
        new_app_name = st.text_input("Nama Aplikasi", value=config.get("app_name", "EMI Marketing Tracker"))
        submitted = st.form_submit_button("Simpan Konfigurasi")
        if submitted:
            success, msg = db.update_app_config({"app_name": new_app_name})
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# --- Main App Logic ---
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
    elif page == "Riset Prospek":
        page_prospect_research()
    elif page == "Manajemen Pengguna":
        page_user_management()
    elif page == "Pengaturan":
        page_settings()


