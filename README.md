# Rekod PAJSK Murid — Streamlit + Supabase

Versi awan daripada fail `REKOD_PAJSK_MURID.html`. Rekod metadata disimpan dalam jadual Supabase dan surat/lampiran disimpan dalam bucket Supabase Storage yang **private**. Data tidak bergantung pada storan browser seseorang.

## Fungsi

- Log masuk menggunakan dua peranan berasaskan kata laluan: `ADMIN_PASSWORD` (tambah, semak status, padam) dan `VIEW_PASSWORD` (paparan sahaja).
- Rekod baharu bermula pada status `Menunggu semakan`; status disahkan hanya oleh pengguna admin.
- Carian, tapis status, ringkasan kiraan dan eksport metadata CSV.
- Lampiran PDF/JPG/PNG maksimum 10 MB, disimpan dalam bucket private. Pautan dokumen ditandatangani untuk tempoh 15 minit.
- Rahsia Supabase tidak dimasukkan dalam kod atau Git.

## 1. Sediakan Supabase

1. Cipta projek di [Supabase](https://supabase.com/).
2. Buka **SQL Editor → New query**.
3. Salin dan jalankan semua kandungan `supabase_setup.sql`.
4. Dalam **Project Settings → API Keys** (atau halaman API Keys bagi projek anda), salin Project URL dan kunci `service_role`/secret yang mempunyai keistimewaan backend. Nama/label kunci mungkin berbeza mengikut paparan Supabase.
5. Jangan masukkan kunci itu dalam kod frontend, HTML, GitHub atau mesej awam. App ini memerlukannya hanya pada bahagian server Streamlit.

## 2. Muat naik ke GitHub melalui pelayar

1. Log masuk ke [GitHub](https://github.com/).
2. Tekan **New repository** dan namakan contoh `rekod-pajsk-murid`.
3. Pilih **Private** kerana sistem mengandungi maklumat murid dan dokumen surat.
4. Cipta repository, kemudian pilih **Add file → Upload files**.
5. Muat naik `streamlit_app.py`, `requirements.txt`, `supabase_setup.sql`, `.gitignore` dan `README.md`. Muat naik juga folder `.streamlit` tidak diperlukan untuk deploy; jangan muat naik fail rahsia.
6. Tekan **Commit changes**.

## 3. Terbitkan di Streamlit Community Cloud

1. Buka [Streamlit Community Cloud](https://share.streamlit.io/) dan log masuk menggunakan akaun GitHub.
2. Pilih **Create app**.
3. Pilih repository `rekod-pajsk-murid`, branch `main`, dan main file path `streamlit_app.py`.
4. Sebelum deploy atau melalui **Advanced settings → Secrets**, masukkan rahsia berikut dan gantikan nilai contoh:

```toml
SUPABASE_URL = "https://PROJECT-REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "GANTIKAN_DENGAN_KUNCI_SERVER_SUPABASE"
ADMIN_PASSWORD = "GANTIKAN_DENGAN_KATA_LALUAN_ADMIN_UNIK_PANJANG"
VIEW_PASSWORD = "GANTIKAN_DENGAN_KATA_LALUAN_PAPARAN_YANG_BERBEZA"
```

Gunakan kata laluan panjang dan unik. Jangan guna contoh di atas sebagai kata laluan sebenar.
5. Klik **Deploy**. Jika app belum dapat menyambung, buka app logs dan semak mesej ralat.

## 4. Cara guna

- Kongsi `VIEW_PASSWORD` hanya dengan pengguna yang patut melihat data. Mereka tidak dapat tambah, sahkan atau padam melalui app.
- Kongsi `ADMIN_PASSWORD` hanya dengan guru/pentadbir yang dibenarkan.
- Muat naik rekod dengan lampiran surat. Rekod baru masuk sebagai `Menunggu semakan`.
- Guru/admin buka rekod dan tukar status kepada `Disahkan sekolah` atau `Perlu pembetulan` selepas semakan.
- Uji menggunakan kedua-dua peranan sebelum mula memasukkan data sebenar.

## Perkara keselamatan penting

Ini ialah versi permulaan dengan kata laluan bersama. Ia tidak memberi identiti unik setiap guru dan bukan pengganti sistem log masuk individu. Untuk data murid yang sensitif, hadkan akses Streamlit kepada staf yang dibenarkan, jangan sebarkan kata laluan admin, dan rancang naik taraf kepada akaun individu serta audit log. `SUPABASE_SERVICE_ROLE_KEY` membolehkan akses backend berkeistimewaan tinggi; simpan hanya dalam Secrets Streamlit.

## Uji secara setempat (pilihan)

Pasang Python, kemudian dalam folder projek:

```bash
pip install -r requirements.txt
```

Cipta `.streamlit/secrets.toml` pada komputer sendiri menggunakan TOML contoh di atas. Fail itu dikecualikan oleh `.gitignore` dan jangan muat naik ke GitHub. Jalankan:

```bash
streamlit run streamlit_app.py
```

Fail asal HTML disertakan di `reference/REKOD_PAJSK_MURID.html` untuk rujukan. Fail asal ini masih menyimpan data dalam IndexedDB pada browser; untuk penyimpanan bersama, jalankan `streamlit_app.py` yang disediakan.
