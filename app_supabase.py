# --- START OF FILE app_supabase.py (Versi Paling Stabil dan Lengkap) ---

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import db_supabase as db
import pytz
import requests
from urllib.parse import urlencode
import streamlit.components.v1 as components

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="EMI Marketing Tracker", page_icon="💼", layout="wide")

# --- Mapping & Konstanta ---
STATUS_MAPPING = {'baru': 'Baru', 'dalam_proses': 'Dalam Proses', 'berhasil': 'Berhasil', 'gagal': 'Gagal'}
REVERSE_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}
ACTIVITY_TYPES = ["Presentasi", "Demo Produk", "Follow-up Call", "Email", "Meeting", "Lainnya"]

# --- Helper Fungsi Waktu & Tanggal ---
def convert_to_wib_and_format(iso_string, format_str='%A, %d %b %Y, %H:%M'):
    if not iso_string: return "N/A"
    try:
        dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        wib_tz = pytz.timezone("Asia/Jakarta")
        return dt_utc.astimezone(wib_tz).strftime(format_str)
    except Exception: return iso_string

def date_to_str(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (date, datetime)) else dt

def str_to_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


# --- Helper Template Email (Final & Dinamis) ---
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
        email_body = f"<p>Perkenalkan, saya <strong>{sender_name}</strong>, Founder & CEO dari <strong>Solusi AI Indonesia</strong>.</p><p>Saya melihat <strong>{company_name}</strong> sebagai salah satu pemain kunci di industri {industry}. Di era digital yang sangat kompetitif ini, adopsi teknologi cerdas bukan lagi pilihan, melainkan sebuah keharusan untuk tetap relevan dan unggul.</p><p>Apakah Anda terbuka untuk sebuah diskusi singkat minggu depan?</p>"
    elif sender_role == 'manager':
        sender_title = "AI Solutions Manager, Solusi AI Indonesia"
        email_body = f"<p>Perkenalkan, saya <strong>{sender_name}</strong>, AI Solutions Manager dari <strong>Solusi AI Indonesia</strong>.</p><p>CEO kami, Iwan Cahyo, menugaskan saya untuk menjangkau perusahaan-perusahaan potensial seperti <strong>{company_name}</strong>.</p><p>Saya ingin mengundang Anda untuk sesi konsultasi 30 menit tanpa komitmen untuk memetakan potensi solusi AI yang paling efektif untuk tim Anda.</p>"
    else:
        sender_title = "Business Development, Solusi AI Indonesia"
        email_body = f"<p>Saya <strong>{sender_name}</strong> dari tim Business Development di <strong>Solusi AI Indonesia</strong>.</p><p>Apakah tim Anda di <strong>{company_name}</strong> menghabiskan banyak waktu menjawab pertanyaan pelanggan yang berulang?</p><p>Saya bisa siapkan demo singkat 15 menit untuk menunjukkan cara kerjanya. Apakah hari Selasa atau Kamis sore pekan ini cocok untuk Anda?</p>"
    
    return f"""<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><h2 style="color: #1f77b4;">Penawaran AI untuk {company_name}</h2><p>Yth. Bapak/Ibu <strong>{contact_name}</strong>,</p>{email_body}<p>Terima kasih atas waktu dan perhatian Anda.</p><br><p>Hormat saya,</p><p style="margin-bottom: 0;"><strong>{sender_name}</strong></p><p style="margin-top: 0; margin-bottom: 0;"><em>{sender_title}</em></p><p style="margin-top: 0; margin-bottom: 0;"><a href="https://solusiai.id">solusiai.id</a></p>{f'<p style="margin-top: 0;"><a href="{sender_linkedin}">Profil LinkedIn</a></p>' if sender_linkedin else ""}</div>""".strip()


# --- Halaman & Fungsi Utama ---

def show_login_page():
    # ... (Kode tidak berubah)
    pass

def show_sidebar():
    # ... (Kode tidak berubah)
    pass

def get_data_based_on_role():
    # ... (Kode tidak berubah)
    pass

def page_dashboard():
    # ... (Kode tidak berubah)
    pass

def page_activities_management():
    # ... (Kode tidak berubah)
    pass

def show_activity_form(activity):
    # ... (Kode tidak berubah)
    pass

def show_followup_section(activity):
    # ... (Kode tidak berubah)
    pass

def page_prospect_research():
    st.title("Riset Prospek 🔍💼")
    _, prospects, _ = get_data_based_on_role()
    profile = st.session_state.profile

    st.subheader("Cari Prospek")
    search_query = st.text_input("Ketik nama perusahaan, kontak, industri, atau lokasi...")
    filtered_prospects = db.search_prospect_research(search_query, user_id=profile['id'], role=profile.get('role')) if search_query else prospects

    st.divider()
    st.subheader("Daftar Prospek")
    if not filtered_prospects:
        st.info("Belum ada data prospek.")
    else:
        df = pd.DataFrame(filtered_prospects)
        st.dataframe(df[['company_name', 'contact_name', 'industry', 'status']].rename(columns={'company_name': 'Perusahaan', 'contact_name': 'Kontak', 'industry': 'Industri', 'status': 'Status'}), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Pilih Prospek untuk Diedit atau Tambah Baru")
    options = {p['id']: f"{p.get('company_name', 'N/A')} - {p.get('contact_name', 'N/A')}" for p in filtered_prospects}
    options[0] = "<< Tambah Prospek Baru >>"
    selected_id = st.selectbox("Pilih prospek:", options.keys(), format_func=lambda x: options[x], index=0)

    if selected_id == 0:
        with st.form("prospect_form"):
            # ... (Form tambah prospek tidak berubah)
            pass
    else:
        prospect = db.get_prospect_by_id(selected_id)
        if prospect:
            with st.form("edit_prospect_form"):
                # ... (Form edit prospek tidak berubah)
                pass

            st.divider()
            st.subheader("Template Email Profesional")

            html_template = generate_html_email_template(prospect, user_profile=profile)
            edited_html = st.text_area("Edit Template Email", value=html_template, height=300)

            # --- PENDEKATAN PALING SEDERHANA & STABIL ---
            # Tidak ada session state, tidak ada rerun aneh
            if st.button("Preview Email"):
                with st.container(border=True):
                    components.html(edited_html, height=400, scrolling=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Simpan Template ke Prospek"):
                    success, msg = db.save_email_template_to_prospect(prospect_id=selected_id, template_html=edited_html)
                    st.success(msg) if success else st.error(msg)
            with col2:
                if st.button("Kirim Email via Zoho"):
                    with st.spinner("Mengirim..."):
                        success, msg = db.send_email_via_zoho({"to": prospect.get("contact_email"), "subject": f"Penawaran AI untuk {prospect.get('company_name')}", "content": edited_html, "from": st.secrets["zoho"]["from_email"]})
                        st.success(msg) if success else st.error(msg)

def page_user_management():
    # ... (Kode tidak berubah)
    pass

def page_settings():
    # ... (Kode tidak berubah)
    pass

def get_authorization_url():
    # ... (Kode tidak berubah)
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