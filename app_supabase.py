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

# --- Mapping Status ---
STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Helper Fungsi Waktu & Tanggal ---
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    """Konversi waktu UTC ke WIB"""
    if not iso_string:
        return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string)
        wib_tz = pytz.timezone("Asia/Jakarta")
        dt_wib = dt_utc.astimezone(wib_tz)
        return dt_wib.strftime(format_str)
    except Exception:
        return iso_string


def date_to_str(dt):
    """Ubah date ke string 'YYYY-MM-DD'"""
    return dt.strftime("%Y-%m-%d") if isinstance(dt, date) else dt


def str_to_date(s):
    """Ubah string ke date object"""
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


# --- Helper Template Email ---
def generate_html_email_template(prospect, role=None, industry=None, follow_up_number=None):
    contact_name = prospect.get("contact_name", "Bapak/Ibu")
    company_name = prospect.get("company_name", "Perusahaan")
    location = prospect.get("location", "Lokasi")
    next_step = prospect.get("next_step", "baru")

    # --- Default Template ---
    default_template = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #1f77b4;">Penawaran Solusi AI Voice untuk {company_name}</h2>
    
    <p>Halo <strong>{contact_name}</strong>,</p>

    <p>Kami melihat bahwa perusahaan Anda, <strong>{company_name}</strong>, sedang dalam tahap <em>{next_step}</em>. Kami menawarkan solusi berbasis <strong>AI Voice</strong> yang bisa meningkatkan efisiensi operasional dan engagement pelanggan.</p>

    <p>Jika tertarik, silakan hubungi kami via {prospect.get('phone', st.session_state.profile.get('email'))}.</p>

    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>

    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>"""

    # --- Template berbasis role ---
    if role:
        role = role.lower()
        if "ceo" in role or "founder" in role:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #1f77b4;">Solusi Strategis untuk {company_name} (CEO)</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Saya melihat bahwa perusahaan Anda, <strong>{company_name}</strong>, saat ini sedang dalam tahap <em>{next_step}</em>. Sebagai pemimpin bisnis, apakah Anda tertarik dengan penawaran yang bisa meningkatkan efisiensi operasional dan pengalaman pelanggan secara signifikan?</p>
    <p><strong>Kami menyediakan teknologi AI Voice</strong> yang memungkinkan bisnis seperti {company_name} melakukan:</p>
    <ul>
        <li>Panggilan otomatis dengan suara natural</li>
        <li>Interaksi pelanggan 24/7 via telepon</li>
        <li>Integrasi cepat dengan CRM atau sistem internal</li>
        <li>Analisis percakapan pelanggan untuk optimasi layanan</li>
    </ul>
    <p>Apakah Anda tertarik untuk diskusi singkat? Saya siap jelaskan bagaimana solusi ini bisa bekerja untuk bisnis Anda.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "Tim EMI")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

        elif "cfo" in role or "finance" in role:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #ff7f0e;">Efisiensi Biaya untuk {company_name} (CFO)</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Berdasarkan data bisnis Anda di <strong>{company_name}</strong>, kami menemukan bahwa ada potensi besar untuk meningkatkan efisiensi biaya operasional dengan menggunakan teknologi suara AI.</p>
    <p><strong>AI Voice EMI</strong> membantu perusahaan seperti {company_name} dalam:</p>
    <ul>
        <li>Mengotomatisasi panggilan follow-up & reminder tanpa agen telemarketing</li>
        <li>Meningkatkan konversi kampanye pemasaran via voice messaging</li>
        <li>Mengurangi kebutuhan tenaga manusia untuk komunikasi awal dengan prospek</li>
        <li>Integrasi langsung dengan sistem CRM untuk analisis cost-to-acquisition</li>
    </ul>
    <p>Dengan solusi ini, Anda bisa mengurangi biaya operasional hingga <strong>40%</strong> tanpa mengorbankan engagement pelanggan.</p>
    <p>Jika tertarik, saya siap bantu Anda lihat simulasi efisiensi biaya yang bisa dicapai melalui demo singkat.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

        elif "it" in role or "tech" in role or "engineer" in role:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #17becf;">Teknologi Informasi untuk {company_name}</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Berdasarkan riset kami, <strong>{company_name}</strong> menggunakan teknologi {', '.join(prospect.get("technology_used", ["Tidak ada"]))}. Kami menawarkan integrasi sistem berbasis AI Voice yang bisa langsung digunakan oleh tim IT Anda.</p>
    <p>Jika tertarik, silakan balas email ini atau kontak saya via {prospect.get('phone', '')}.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

    # --- Template berbasis industri ---
    if industry:
        industry = industry.lower()
        if "teknologi" in industry or "tech" in industry:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #17becf;">Teknologi Informasi untuk {company_name}</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Kami percaya bahwa solusi IT & AI Voice kami sangat cocok untuk perusahaan Anda di industri teknologi informasi.</p>
    <p>Jika tertarik, silakan balas email ini atau kontak saya via {prospect.get('phone', '')}.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

        elif "kesehatan" in industry or "hospital" in industry or "clinic" in industry:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #2ca02c;">Solusi Digital untuk Rumah Sakit/Klinik</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Kami menemukan bahwa <strong>{company_name}</strong> berada di industri kesehatan. Kami punya solusi digital berbasis AI Voice untuk meningkatkan efisiensi operasional rumah sakit/klinik Anda.</p>
    <p>Silakan balas email ini untuk diskusi lebih lanjut.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

        elif "skincare" in industry or "beauty" in industry or "cosmetic" in industry:
            return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #e377c2;">Solusi Digital untuk Bisnis Skincare</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Berdasarkan riset kami, <strong>{company_name}</strong> berada di industri skincare. Kami punya solusi <strong>AI Voice</strong> untuk meningkatkan efisiensi operasional dan personalisasi interaksi pelanggan.</p>
    <p>Dengan teknologi ini, Anda bisa:</p>
    <ul>
        <li>Otomatiskan reminder treatment pelanggan</li>
        <li>Tingkatkan engagement dengan voice campaign personal</li>
        <li>Minimalkan biaya customer service</li>
        <li>Lacak respons pelanggan secara real-time</li>
    </ul>
    <p>Silakan balas email ini untuk diskusi lebih lanjut.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "Tim EMI")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

    # --- Template berbasis frekuensi follow-up ---
    if follow_up_number == 1:
        return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #1f77b4;">Follow-up 1 - Halo {contact_name}, Ini Penawaran dari EMI</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Saya menemukan data perusahaan Anda saat riset di industri {industry}. Kami percaya bahwa solusi AI Voice kami sangat cocok untuk bisnis seperti {company_name}.</p>
    <p>Apakah Anda tertarik untuk diskusi singkat?</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "Tim EMI")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

    elif follow_up_number == 2:
        return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #17becf;">Follow-up 2 - Update Tambahan untuk {company_name}</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Sebelumnya, kita sudah sempat komunikasi mengenai solusi digital untuk {company_name}. Sekarang, saya ingin memberikan info tambahan tentang bagaimana <strong>AI Voice</strong> bisa membantu tim Anda:</p>
    <ul>
        <li>Personalisasi pesan berdasarkan riwayat interaksi</li>
        <li>Skalakan ratusan panggilan harian</li>
        <li>Transkrip percakapan untuk analisis tim sales</li>
        <li>Integrasikan dengan sistem billing/CRM Anda</li>
    </ul>
    <p>Jika ada pertanyaan atau butuh info lebih lanjut, jangan ragu untuk balas email ini.</p>
    <br>
    <p><strong>{st.session_state.profile.get("full_name", "EMI Marketing Team")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

    elif follow_up_number >= 3:
        return f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
    <h2 style="color: #d62728;">Follow-up 3 - Penawaran Terakhir</h2>
    <p>Halo <strong>{contact_name}</strong>,</p>
    <p>Kami belum mendapat respons terkait penawaran sebelumnya. Apakah masih tertarik dengan solusi AI Voice untuk {company_name}? Kami bisa bantu Anda meningkatkan efisiensi dan skalabilitas bisnis Anda.</p>
    <p>Silakan balas email ini atau kontak saya via {prospect.get('phone', st.session_state.profile.get('email'))}.</p>
    <br>
    <p><strong>{st.session_manipulate.profile.get("full_name", "Tim EMI")}</strong><br>
    <em>{st.session_state.profile.get("role", "")}</em></p>
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 0.9em; color: #555;">Dikirim via EMI Marketing Tracker</p>
</div>""".strip()

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
        if profile.get('role') == 'superadmin':
            pages.extend(["Manajemen Pengguna", "Pengaturan"])

        page = st.radio("Pilih Halaman:", pages)
        st.divider()

        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        return page


# --- Dashboard ---
def page_dashboard():
    st.title(f"Dashboard {st.session_state.profile.get('role', '').capitalize()}")
    user = st.session_state.user
    profile = st.session_state.profile

    activities = db.get_all_marketing_activities() if profile.get('role') == 'superadmin' else db.get_marketing_activities_by_user_id(user.id)

    if not activities:
        st.info("Belum ada data aktivitas untuk ditampilkan.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aktivitas", len(df))
    col2.metric("Total Prospek Unik", df['prospect_name'].nunique())
    if profile.get('role') == 'superadmin':
        col3.metric("Jumlah Tim Marketing", df['marketer_id'].nunique())

    st.subheader("Analisis Aktivitas Pemasaran")

    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['status'].map(STATUS_MAPPING).value_counts()
        fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index,
                     title="Distribusi Status Prospek", color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        type_counts = df['activity_type'].value_counts()
        fig2 = px.bar(type_counts, x=type_counts.index, y=type_counts.values,
                      title="Distribusi Jenis Aktivitas", labels={'x': 'Jenis Aktivitas', 'y': 'Jumlah'},
                      color_continuous_scale=px.colors.sequential.Viridis)
        st.plotly_chart(fig2, use_container_width=True)

    if profile.get('role') == 'superadmin':
        col3, col4 = st.columns(2)
        with col3:
            location_counts = df['prospect_location'].str.strip().str.title().value_counts().nlargest(10)
            fig3 = px.bar(location_counts, x=location_counts.index, y=location_counts.values,
                          title="Top 10 Lokasi Prospek", labels={'x': 'Kota/Lokasi', 'y': 'Jumlah Prospek'},
                          color_continuous_scale=px.colors.sequential.Viridis, height=300)
            st.plotly_chart(fig3, use_container_width=True)

        with col4:
            marketer_counts = df['marketer_username'].value_counts()
            fig4 = px.bar(marketer_counts, x=marketer_counts.index, y=marketer_counts.values,
                          title="Aktivitas per Marketing", labels={'x': 'Nama Marketing', 'y': 'Jumlah Aktivitas'},
                          color_continuous_scale=px.colors.sequential.Viridis, height=300)
            st.plotly_chart(fig4, use_container_width=True)

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

    st.divider()
    st.subheader("Jadwal Follow-up (7 Hari Mendatang)")
    all_followups = [fu for act in activities for fu in db.get_followups_by_activity_id(act['id'])]

    if not all_followups:
        st.info("Tidak ada jadwal follow-up yang ditemukan.")
    else:
        for fu in all_followups:
            fu['prospect_name'] = next((act['prospect_name'] for act in activities if act['id'] == fu['activity_id']), 'N/A')
        followups_df = pd.DataFrame(all_followups)
        followups_df['next_followup_date'] = pd.to_datetime(followups_df['next_followup_date'], utc=True)
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

    # --- Sinkron dari Apollo.io (Superadmin Only) ---
    st.divider()
    st.subheader("Sinkron dari Apollo.io")
    if profile.get('role') == 'superadmin':
        apollo_query = st.text_input("Masukkan query pencarian (misal: industry:Technology AND location:Jakarta)")
        if st.button("Tarik Data dari Apollo.io"):
            with st.spinner("Menarik data dari Apollo.io..."):
                raw_prospects = db.sync_prospect_from_apollo(apollo_query)
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
    else:
        st.warning("Fitur ini hanya tersedia untuk superadmin.")


# --- Manajemen Aktivitas Pemasaran ---
def page_activities_management():
    st.title("Manajemen Aktivitas Pemasaran")
    profile = st.session_state.profile
    user = st.session_state.user
    activities = db.get_all_marketing_activities() if profile.get('role') == 'superadmin' else db.get_marketing_activities_by_user_id(user.id)

    if not activities:
        st.info("Belum ada data aktivitas. Silakan tambahkan aktivitas baru di bawah.")
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(activities)

    st.subheader("Semua Catatan Aktivitas")
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1
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
            st.session_state.page_num -= 1
            st.rerun()
    with col_nav2:
        st.write(f"<div style='text-align: center;'>Halaman <b>{st.session_state.page_num}</b> dari <b>{total_pages}</b></div>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("NEXT ➡️", disabled=(st.session_state.page_num >= total_pages)):
            st.session_state.page_num += 1
            st.rerun()

    st.divider()
    options = {act['id']: f"{act['prospect_name']} - {act.get('contact_person', 'N/A')}" for act in activities}
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
            prospect_name = st.text_input("Nama Prospek*", value=activity.get('prospect_name', '') if activity else "")
            contact_person = st.text_input("Nama Kontak Person", value=activity.get('contact_person', '') if activity else "")
            contact_position = st.text_input("Jabatan Kontak Person", value=activity.get('contact_position', '') if activity else "")
            contact_phone = st.text_input("Telepon Kontak", value=activity.get('contact_phone', '') if activity else "")
        with col2:
            prospect_location = st.text_input("Lokasi Prospek", value=activity.get('prospect_location', '') if activity else "")
            contact_email = st.text_input("Email Kontak", value=activity.get('contact_email', '') if activity else "")
            default_date = str_to_date(activity['activity_date']) if activity and activity.get('activity_date') else date.today()
            activity_date = st.date_input("Tanggal Aktivitas", value=default_date)

        activity_type = st.selectbox("Jenis Aktivitas", options=ACTIVITY_TYPES,
                                     index=ACTIVITY_TYPES.index(activity['activity_type']) if activity and activity.get('activity_type') in ACTIVITY_TYPES else 0)
        status_display = st.selectbox("Status", options=list(STATUS_MAPPING.values()),
                                      index=list(STATUS_MAPPING.values()).index(STATUS_MAPPING.get(activity['status'], 'baru')) if activity else 0)
        description = st.text_area("Deskripsi", value=activity.get('description', '') if activity else "", height=150)
        submitted = st.form_submit_button(button_label)
        if submitted:
            if not prospect_name:
                st.error("Nama Prospek wajib diisi!")
            else:
                status_key = REVERSE_STATUS_MAPPING[status_display]
                if activity:
                    success, msg = db.edit_marketing_activity(
                        activity['id'],
                        prospect_name,
                        prospect_location,
                        contact_person,
                        contact_position,
                        contact_phone,
                        contact_email,
                        date_to_str(activity_date),
                        activity_type,
                        description,
                        status_key
                    )
                else:
                    success, msg, new_id = db.add_marketing_activity(
                        user.id,
                        profile.get('full_name'),
                        prospect_name,
                        prospect_location,
                        contact_person,
                        contact_position,
                        contact_phone,
                        contact_email,
                        date_to_str(activity_date),
                        activity_type,
                        description,
                        status_key
                    )

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

    with st.form("new_followup_form"):
        st.write("**Tambah Follow-up Baru**")
        notes = st.text_area("Catatan Follow-up Baru:")
        next_action = st.text_input("Rencana Tindak Lanjut Berikutnya")
        next_followup_date = st.date_input("Jadwal Follow-up Berikutnya", value=None, help="Kosongkan jika tidak ada jadwal.")
        interest_level = st.select_slider("Tingkat Ketertarikan Prospek", options=["Rendah", "Sedang", "Tinggi"])
        current_status = STATUS_MAPPING.get(st.session_state.get('status', 'baru'), 'Baru')
        new_status_display = st.selectbox("Update Status Prospek Menjadi:", options=list(STATUS_MAPPING.values()),
                                          index=list(STATUS_MAPPING.values()).index(current_status))
        if st.form_submit_button("Simpan Follow-up"):
            if not notes:
                st.warning("Catatan tidak boleh kosong.")
            else:
                new_status_key = REVERSE_STATUS_MAPPING[new_status_display]
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


# --- Riset Prospek ---
def page_prospect_research():
    st.title("Riset Prospek 🔍💼")
    user = st.session_state.user
    profile = st.session_state.profile

    if profile.get('role') == 'superadmin':
        prospects = db.get_all_prospect_research()
    else:
        prospects = db.get_prospect_research_by_marketer(user.id)

    st.subheader("Cari Prospek")
    search_query = st.text_input("Ketik nama perusahaan, kontak, industri, atau lokasi...")
    if search_query:
        filtered_prospects = db.search_prospect_research(search_query)
        st.info(f"Menemukan {len(filtered_prospects)} hasil pencarian untuk '{search_query}'")
    else:
        filtered_prospects = prospects

    st.divider()
    st.subheader("Daftar Prospek")
    if not filtered_prospects:
        st.info("Belum ada data prospek.")
        return

    df = pd.DataFrame(filtered_prospects)
    display_cols = ['company_name', 'contact_name', 'industry', 'status']
    if 'status' not in df.columns:
        st.error("Kolom 'status' tidak ditemukan di data prospek. Pastikan tabel Supabase memiliki kolom 'status'.")
        return

    df_display = df[display_cols].rename(columns={'company_name': 'Perusahaan', 'contact_name': 'Kontak', 'industry': 'Industri', 'status': 'Status'})
    df_display['Status'] = df_display['Status'].map(STATUS_MAPPING).fillna("Tidak Diketahui")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Pilih Prospek untuk Diedit")
    options = {p['id']: f"{p['company_name']} - {p.get('contact_name', 'N/A')}" for p in filtered_prospects}
    options[0] = "<< Pilih ID untuk Detail / Edit >>"
    selected_id = st.selectbox("Pilih prospek:", options.keys(), format_func=lambda x: options[x], index=0)

    if selected_id == 0:
        with st.form("prospect_form"):
            st.subheader("Form Tambah Prospek Baru")
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Nama Perusahaan*")
                website = st.text_input("Website")
                industry = st.text_input("Industri")
                founded_year = st.number_input("Tahun Berdiri", min_value=1900, max_value=datetime.now().year, step=1)
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
            next_step_date = st.date_input("Tanggal Follow-up")
            status = st.selectbox("Status Prospek", ["baru", "dalam_proses", "berhasil", "gagal"])
            source = st.text_input("Sumber Prospek", value="manual")

            if st.form_submit_button("Simpan Prospek"):
                if not company_name or not contact_name:
                    st.error("Nama perusahaan dan nama kontak wajib diisi!")
                else:
                    keyword_list = [k.strip() for k in keywords.split(",")] if keywords else []
                    tech_list = [t.strip() for t in technology_used.split(",")] if technology_used else []

                    success, msg = db.add_prospect_research(
                        company_name=company_name,
                        website=website,
                        industry=industry,
                        founded_year=founded_year,
                        company_size=company_size,
                        revenue=revenue,
                        location=location,
                        contact_name=contact_name,
                        contact_title=contact_title,
                        contact_email=contact_email,
                        linkedin_url=linkedin_url,
                        phone=phone,
                        keywords=keyword_list,
                        technology_used=tech_list,
                        notes=notes,
                        next_step=next_step,
                        next_step_date=date_to_str(next_step_date),
                        status=status,
                        source=source,
                        decision_maker=False,
                        email_status="valid",
                        marketer_id=user.id,
                        marketer_username=profile.get("full_name")
                    )

                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    else:
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
                next_step_db = prospect.get('next_step_date')
                next_step_ui = str_to_date(next_step_db) if next_step_db else None
                next_step_date = st.date_input("Tanggal Follow-up", value=next_step_ui)
                status = st.selectbox("Status Prospek", ["baru", "dalam_proses", "berhasil", "gagal"],
                                     index=["baru", "dalam_proses", "berhasil", "gagal"].index(prospect.get('status', 'baru')))
                source = st.text_input("Sumber Prospek", value=prospect.get('source', 'manual'))

                submitted = st.form_submit_button("Simpan Perubahan")
                if submitted:
                    if not company_name or not contact_name:
                        st.error("Nama perusahaan dan nama kontak wajib diisi!")
                    else:
                        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else []
                        tech_list = [t.strip() for t in technology_used.split(",")] if technology_used else []
                        next_step_date_str = date_to_str(next_step_date)

                        success, msg = db.edit_prospect_research(
                            prospect_id=selected_id,
                            company_name=company_name,
                            website=website,
                            industry=industry,
                            founded_year=founded_year,
                            company_size=company_size,
                            revenue=revenue,
                            location=location,
                            contact_name=contact_name,
                            contact_title=contact_title,
                            contact_email=contact_email,
                            linkedin_url=linkedin_url,
                            phone=phone,
                            keywords=keyword_list,
                            technology_used=tech_list,
                            notes=notes,
                            next_step=next_step,
                            next_step_date=next_step_date_str,
                            status=status,
                            source=source,
                            decision_maker=False,
                            email_status="valid"
                        )

                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if st.button("Hapus Prospek Ini", type="primary"):
                success, msg = db.delete_prospect_by_id(selected_id)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            # --- Template Email Otomatis ---
            st.divider()
            st.subheader("Template Email Profesional")

            # Hitung jumlah follow-up yang sudah dikirim
            followups = db.get_followups_by_activity_id(prospect['id'])
            followup_count = len(followups)

            # Generate template berbasis role, industri, dan frekuensi follow-up
            contact_title = prospect.get("contact_title", "").lower() if prospect.get("contact_title") else ""
            prospect_industry = prospect.get("industry", "").lower() if prospect.get("industry") else ""

            html_template = generate_html_email_template(prospect, role=contact_title, industry=prospect_industry, follow_up_number=followup_count + 1)

            edited_html = st.text_area("Edit Template Email", value=html_template, height=400)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Preview Email"):
                    st.markdown(edited_html, unsafe_allow_html=True)
            with col2:
                if st.button("Simpan Template ke Prospek"):
                    success, msg = db.save_email_template_to_prospect(prospect_id=selected_id, template_html=edited_html)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            if st.button("Kirim Email via Zoho"):
                with st.spinner("Sedang mengirim..."):
                    # Auto-refresh token jika expired
                    if not st.secrets["zoho"].get("access_token"):
                        success, msg = db.refresh_zoho_token()
                        if not success:
                            st.error(msg)
                            return

                    success, msg = db.send_email_via_zoho({
                        "to": prospect.get("contact_email"),
                        "subject": f"Follow-up {followup_count + 1}: {company_name}",
                        "content": edited_html,
                        "from": st.secrets["zoho"]["from_email"]
                    })
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)


# --- Manajemen Pengguna (Superadmin Only) ---
def page_user_management():
    st.title("Manajemen Pengguna")
    tab1, tab2 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru"])

    with tab1:
        profiles = db.get_all_profiles()
        if profiles:
            df = pd.DataFrame(profiles).rename(columns={'id': 'User ID', 'full_name': 'Nama Lengkap', 'role': 'Role', 'email': 'Email'})
            st.dataframe(df[['User ID', 'Nama Lengkap', 'Email', 'Role']], use_container_width=True)
        else:
            st.info("Belum ada pengguna terdaftar.")

    with tab2:
        st.subheader("Form Tambah Pengguna Baru")
        full_name = st.text_input("Nama Lengkap")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["marketing", "superadmin"])
        if st.button("Daftarkan Pengguna Baru"):
            if not all([full_name, email, password]):
                st.error("Semua field wajib diisi!")
            else:
                user, error = db.sign_up(email, password, full_name, role)
                if user:
                    st.success(f"Pengguna {full_name} berhasil didaftarkan.")
                    st.rerun()
                else:
                    st.error(f"Gagal mendaftarkan: {error}")


# --- Pengaturan Aplikasi ---
def page_settings():
    st.title("Pengaturan Aplikasi")
    config = db.get_app_config()
    with st.form("config_form"):
        app_name = st.text_input("Nama Aplikasi", value=config.get('app_name', ''))
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

    # --- Bagian Autentikasi Zoho Mail ---
    st.divider()
    st.subheader("Zoho Mail Setup")
    zoho_secrets = st.secrets.get("zoho", {})
    with st.form("zoho_auth_form"):
        st.write("### Langkah 1: Ambil Code dari Zoho")
        auth_url = get_authorization_url()
        st.markdown(f"[Klik di sini untuk izinkan akses Zoho Mail]({auth_url})")
        code = st.text_input("Masukkan code dari Zoho:")

        if st.form_submit_button("Generate Access Token"):
            if not code:
                st.warning("Silakan masukkan code dari Zoho")
            else:
                success, msg = db.exchange_code_for_tokens(code)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def get_authorization_url():
    params = {
        "response_type": "code",
        "client_id": st.secrets["zoho"]["client_id"],
        "scope": "ZohoMail.send,ZohoMail.read",
        "redirect_uri": st.secrets["zoho"].get("redirect_uri", "https://emimtsupabase.streamlit.app/oauth/callback") 
    }
    base_url = "https://accounts.zoho.com/oauth/v2/auth?"
    return base_url + urlencode(params)


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
        elif page == "Riset Prospek":
            page_prospect_research()


if __name__ == "__main__":
    main()