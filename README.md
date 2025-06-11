# EMI Marketing Tracker 💼📊

Aplikasi web modern untuk pencatatan dan manajemen aktivitas tim pemasaran internal **EKUITAS MEDIA INVESTAMA (EMI)**. Dibangun untuk efisiensi, kolaborasi, dan analisis data yang *realtime*.

<div align="left">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
</div>


---

## 🎯 Deskripsi

**EMI Marketing Tracker** adalah solusi digital untuk menggantikan pencatatan manual. Aplikasi ini memungkinkan tim marketing untuk mencatat setiap interaksi dengan prospek, mulai dari panggilan telepon hingga presentasi, serta melacak progres follow-up secara terstruktur. Superadmin dan manajer dapat memantau seluruh aktivitas tim melalui dashboard analitik yang komprehensif, memberikan wawasan berharga untuk pengambilan keputusan strategis.

Aplikasi ini dibangun menggunakan **Streamlit** untuk antarmuka yang cepat dan interaktif, dengan **Supabase** sebagai backend database, memastikan data selalu sinkron, aman, dan dapat diakses dari mana saja.

---

## ✅ Fitur Utama

-   **Input Aktivitas & Follow-up:** Form yang intuitif untuk mencatat setiap aktivitas pemasaran dan progres follow-up dengan mudah.
-   **Dashboard Analitik:** Visualisasi data dalam bentuk grafik dan metrik kunci untuk semua level pengguna (Superadmin, Manager, Marketing).
    -   Distribusi status prospek (Baru, Proses, Berhasil, Gagal).
    -   Analisis jenis aktivitas dan lokasi prospek.
    -   Ringkasan aktivitas terbaru dan jadwal follow-up mendatang.
-   **Manajemen Aktivitas Terpusat:** Tampilan tabel dengan navigasi halaman (paginasi) untuk memantau semua riwayat aktivitas.
-   **Sistem Role & Autentikasi:** Hak akses yang berbeda untuk Superadmin dan Marketing, memastikan keamanan dan relevansi data.
-   **Backend Realtime:** Didukung oleh Supabase, setiap perubahan data langsung tersimpan dan dapat dilihat tanpa proses sinkronisasi manual.
-   **Tampilan Responsif:** Dapat diakses dengan nyaman melalui browser desktop maupun perangkat mobile.

---

## 🔧 Teknologi yang Digunakan

| Komponen           | Teknologi                                                              |
| ------------------ | ---------------------------------------------------------------------- |
| **Framework Web**  | [Streamlit](https://streamlit.io)                                      |
| **Bahasa**         | Python 3                                                               |
| **Database**       | [Supabase](https://supabase.com) (PostgreSQL as a Service)             |
| **UI & Visualisasi** | Streamlit Components, Plotly Express                                   |
| **Deployment**     | [Streamlit Community Cloud](https://streamlit.io/cloud)                |

---

## ⚙️ Cara Menjalankan & Deploy

### Prasyarat

1.  Akun [Supabase](https://supabase.com) (Tingkatan gratis sudah lebih dari cukup).
2.  Akun [Streamlit Community Cloud](https://streamlit.io/cloud).
3.  Python 3.8+ ter-install di komputer.

### Setup Lokal

1.  **Clone repositori ini:**
    ```bash
    git clone https://github.com/NAMA_ANDA/NAMA_REPO_ANDA.git
    cd NAMA_REPO_ANDA
    ```

2.  **Install dependensi:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Kredensial Supabase:**
    -   Buat proyek baru di Supabase dan buat tabel sesuai panduan.
    -   Buat file `.streamlit/secrets.toml` di dalam folder proyek.
    -   Isi file tersebut dengan kredensial Anda:
        ```toml
        [supabase]
        url = "URL_PROYEK_SUPABASE_ANDA"
        key = "KUNCI_ANON_PUBLIC_ANDA"
        ```

4.  **Jalankan aplikasi:**
    ```bash
    streamlit run app_supabase.py
    ```

### Deploy ke Streamlit Cloud

1.  Push semua kode Anda ke repositori GitHub.
2.  Di Streamlit Cloud, klik "New app" dan pilih repositori Anda.
3.  Pastikan "Main file path" adalah `app_supabase.py`.
4.  Buka tab "Advanced settings..." dan masuk ke bagian "Secrets".
5.  Salin-tempel seluruh isi dari file `.streamlit/secrets.toml` lokal Anda ke dalam editor Secrets.
6.  Klik **Deploy!**

---

## 👥 Kontribusi

Proyek ini dikelola secara internal. Namun, ide dan masukan untuk perbaikan selalu diterima. Silakan buat "Issue" jika Anda menemukan bug atau memiliki saran.

Dibuat dengan ❤️ untuk efisiensi tim EMI.