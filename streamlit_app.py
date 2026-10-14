import hmac
import mimetypes
import uuid
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

APP_TITLE = "Rekod PAJSK Murid"
BUCKET = "pajsk-documents"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

st.set_page_config(page_title=APP_TITLE, page_icon="🏆", layout="wide")
st.title("🏆 REKOD PAJSK MURID")
st.caption("Rekod maklumat pertandingan, dokumen sokongan dan status semakan sekolah.")


def get_secret(key: str) -> str:
    value = st.secrets.get(key, "")
    return str(value).strip() if value is not None else ""


def get_client():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        st.error(
            "Sambungan Supabase belum ditetapkan. Masukkan SUPABASE_URL dan "
            "SUPABASE_SERVICE_ROLE_KEY pada Streamlit → App settings → Secrets."
        )
        st.stop()
    return create_client(url, key)


def secure_equal(candidate: str, stored: str) -> bool:
    return bool(stored) and hmac.compare_digest(candidate.encode(), stored.encode())


def auth_gate():
    if st.session_state.get("access_role") in {"admin", "viewer"}:
        return

    st.subheader("Log masuk")
    st.info("Guru/pentadbir boleh mengurus rekod. Pengguna paparan hanya boleh melihat rekod.")
    with st.form("login_form"):
        password = st.text_input("Kata laluan akses", type="password")
        submitted = st.form_submit_button("Log masuk", type="primary")
    if submitted:
        admin_pw = get_secret("123")
        viewer_pw = get_secret("VIEW_PASSWORD")
        if secure_equal(password, admin_pw):
            st.session_state["access_role"] = "admin"
            st.rerun()
        elif secure_equal(password, viewer_pw):
            st.session_state["access_role"] = "viewer"
            st.rerun()
        else:
            st.error("Kata laluan tidak tepat.")
    st.stop()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def generate_code():
    return f"SURAT-{date.today().year}-{uuid.uuid4().hex[:8].upper()}"


def load_records(client):
    response = client.table("pajsk_records").select("*").order("created_at", desc=True).execute()
    return response.data or []


def record_file_url(client, path: str) -> str:
    result = client.storage.from_(BUCKET).create_signed_url(path, 900)
    if isinstance(result, dict):
        return result.get("signedURL") or result.get("signedUrl") or result.get("signed_url") or ""
    return ""


def check_file(uploaded_file):
    if uploaded_file is None:
        return None, "Sila lampirkan surat rasmi atau dokumen sokongan."
    raw = uploaded_file.getvalue()
    if len(raw) > MAX_FILE_SIZE:
        return None, "Fail melebihi had 10 MB."
    suffix = "." + uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if suffix not in ALLOWED_TYPES:
        return None, "Format dibenarkan: PDF, JPG/JPEG atau PNG sahaja."
    # Check common file signatures; extension alone is not sufficient validation.
    if suffix == ".pdf" and not raw.startswith(b"%PDF-"):
        return None, "Kandungan fail tidak kelihatan seperti PDF yang sah."
    if suffix in {".jpg", ".jpeg"} and not raw.startswith(b"\xff\xd8\xff"):
        return None, "Kandungan fail tidak kelihatan seperti JPEG yang sah."
    if suffix == ".png" and not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, "Kandungan fail tidak kelihatan seperti PNG yang sah."
    mime = ALLOWED_TYPES[suffix]
    return (raw, suffix, mime), None


def status_label(status):
    return {
        "pending": "Menunggu semakan",
        "verified": "Disahkan sekolah",
        "fix": "Perlu pembetulan",
    }.get(status, status or "Tidak diketahui")


def display_records(client, rows, admin: bool):
    if not rows:
        st.info("Belum ada rekod yang sepadan dengan carian.")
        return
    frame = pd.DataFrame([
        {
            "Nama murid": r.get("student_name", ""),
            "Pertandingan / program": r.get("program", ""),
            "Kategori": r.get("category", ""),
            "Peringkat": r.get("level", ""),
            "No. rujukan": r.get("reference_no", ""),
            "Status": status_label(r.get("status")),
            "Tarikh surat": r.get("letter_date", ""),
        }
        for r in rows
    ])
    st.dataframe(frame, use_container_width=True, hide_index=True)

    for r in rows:
        title = f"{r.get('student_name', 'Murid')} — {r.get('program', 'Program')} · {status_label(r.get('status'))}"
        with st.expander(title):
            left, right = st.columns(2)
            with left:
                st.write("**Kategori:**", r.get("category") or "—")
                st.write("**Peringkat:**", r.get("level") or "—")
                st.write("**Tarikh pertandingan:**", r.get("event_date") or "—")
                st.write("**Penganjur:**", r.get("organizer") or "—")
                st.write("**Agensi / jabatan pengeluar:**", r.get("issuer") or "—")
            with right:
                st.write("**No. rujukan surat:**", r.get("reference_no") or "—")
                st.write("**Tarikh surat:**", r.get("letter_date") or "—")
                st.write("**Kod rekod:**", r.get("verification_code") or "—")
                st.write("**Nama fail:**", r.get("file_name") or "—")
                st.write("**Status:**", status_label(r.get("status")))
            if r.get("official_url"):
                st.markdown(f"[Buka pautan sumber rasmi]({r['official_url']})")
            if r.get("notes"):
                st.write("**Catatan:**", r["notes"])
            if r.get("verification_notes"):
                st.write("**Catatan semakan:**", r["verification_notes"])
            if r.get("verified_at"):
                st.write("**Disahkan pada:**", r["verified_at"])
                st.write("**Disahkan oleh:**", r.get("verified_by") or "—")

            try:
                url = record_file_url(client, r["file_path"])
                if url:
                    st.link_button("📄 Buka / muat turun surat (pautan sah 15 minit)", url)
                else:
                    st.warning("Pautan dokumen tidak dapat dijana.")
            except Exception as exc:
                st.error(f"Dokumen tidak dapat dibuka: {exc}")

            if admin:
                st.divider()
                st.markdown("**Tindakan guru / pentadbir**")
                edit_col, delete_col = st.columns([2, 1])
                with edit_col:
                    desired_status = st.selectbox(
                        "Status semakan", ["pending", "verified", "fix"],
                        index=["pending", "verified", "fix"].index(r.get("status", "pending")),
                        format_func=status_label,
                        key=f"status_{r['id']}",
                    )
                    verification_notes = st.text_input(
                        "Catatan semakan", value=r.get("verification_notes") or "",
                        key=f"notes_{r['id']}",
                    )
                    if st.button("Simpan status semakan", key=f"save_status_{r['id']}"):
                        payload = {
                            "status": desired_status,
                            "verification_notes": verification_notes.strip(),
                            "verified_at": now_iso() if desired_status == "verified" else None,
                            "verified_by": "Guru / Pentadbir" if desired_status == "verified" else None,
                        }
                        client.table("pajsk_records").update(payload).eq("id", r["id"]).execute()
                        st.success("Status semakan dikemas kini.")
                        st.rerun()
                with delete_col:
                    st.warning("Pemadaman tidak boleh dibatalkan.")
                    if st.button("Padam rekod", key=f"delete_{r['id']}", type="secondary"):
                        st.session_state["pending_delete"] = r["id"]
                if st.session_state.get("pending_delete") == r["id"]:
                    st.error("Sahkan pemadaman rekod dan fail surat.")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("Ya, padam", key=f"confirm_delete_{r['id']}", type="primary"):
                            client.table("pajsk_records").delete().eq("id", r["id"]).execute()
                            try:
                                client.storage.from_(BUCKET).remove([r["file_path"]])
                            except Exception:
                                st.warning("Rekod dipadam tetapi fail dalam Storage perlu disemak secara manual.")
                            st.session_state.pop("pending_delete", None)
                            st.success("Rekod dipadam.")
                            st.rerun()
                    with c_no:
                        if st.button("Batal", key=f"cancel_delete_{r['id']}"):
                            st.session_state.pop("pending_delete", None)
                            st.rerun()


def add_record(client):
    st.subheader("Tambah rekod pertandingan")
    st.caption("Semua rekod baharu bermula dengan status Menunggu semakan. Hanya guru/pentadbir boleh mengesahkan surat.")
    with st.form("add_record_form", clear_on_submit=True):
        student_name = st.text_input("Nama murid *")
        category = st.selectbox("Kategori *", ["", "Kelab & Persatuan", "Unit Beruniform", "Sukan & Permainan", "Aktiviti Tambahan", "Program / Pertandingan"])
        level = st.selectbox("Peringkat *", ["", "Sekolah", "Daerah / MSSD", "Negeri / MSSK", "Kebangsaan", "Antarabangsa"])
        program = st.text_input("Nama pertandingan / program *")
        event_date = st.date_input("Tarikh pertandingan", value=None)
        organizer = st.text_input("Penganjur *")
        issuer = st.text_input("Agensi / jabatan pengeluar *")
        reference_no = st.text_input("No. rujukan surat *")
        letter_date = st.date_input("Tarikh surat *", value=date.today())
        official_url = st.text_input("Pautan sumber rasmi (pilihan)", placeholder="https://...")
        notes = st.text_area("Catatan")
        uploaded = st.file_uploader("Surat rasmi / lampiran * (PDF, JPG, PNG; maksimum 10 MB)", type=["pdf", "jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Simpan rekod", type="primary")

    if not submitted:
        return
    required = {
        "Nama murid": student_name,
        "Kategori": category,
        "Peringkat": level,
        "Pertandingan": program,
        "Penganjur": organizer,
        "Agensi / jabatan": issuer,
        "No. rujukan": reference_no,
    }
    missing = [name for name, value in required.items() if not str(value).strip()]
    if missing:
        st.error("Sila lengkapkan: " + ", ".join(missing))
        return
    if official_url.strip() and not official_url.strip().startswith(("https://", "http://")):
        st.error("Pautan sumber rasmi mesti bermula dengan http:// atau https://")
        return
    checked, error = check_file(uploaded)
    if error:
        st.error(error)
        return

    raw, suffix, mime = checked
    file_path = f"{date.today().year}/{uuid.uuid4().hex}{suffix}"
    code = generate_code()
    try:
        client.storage.from_(BUCKET).upload(
            path=file_path,
            file=raw,
            file_options={"content-type": mime, "upsert": "false"},
        )
        payload = {
            "verification_code": code,
            "student_name": student_name.strip(),
            "category": category,
            "program": program.strip(),
            "level": level,
            "event_date": event_date.isoformat() if event_date else None,
            "organizer": organizer.strip(),
            "issuer": issuer.strip(),
            "reference_no": reference_no.strip(),
            "letter_date": letter_date.isoformat(),
            "official_url": official_url.strip() or None,
            "notes": notes.strip() or None,
            "file_name": uploaded.name,
            "file_path": file_path,
            "file_type": mime,
            "file_size": len(raw),
            "status": "pending",
            "uploaded_by": "Guru / Pentadbir",
        }
        client.table("pajsk_records").insert(payload).execute()
        st.success(f"Rekod berjaya disimpan. Kod rujukan: {code}")
        st.rerun()
    except Exception as exc:
        try:
            client.storage.from_(BUCKET).remove([file_path])
        except Exception:
            pass
        st.error(f"Gagal menyimpan rekod. Semak sambungan, SQL dan Storage Supabase. Butiran: {exc}")


def main():
    auth_gate()
    role = st.session_state["access_role"]
    client = get_client()
    with st.sidebar:
        st.success("Akses guru / pentadbir" if role == "admin" else "Mod paparan sahaja")
        st.caption("Peranan semasa: " + ("ADMIN" if role == "admin" else "VIEWER"))
        if st.button("Log keluar"):
            st.session_state.pop("access_role", None)
            st.rerun()
        st.divider()
        st.caption("Dokumen disimpan dalam Supabase Storage peribadi. Pautan dokumen tamat selepas 15 minit.")

    try:
        records = load_records(client)
    except Exception as exc:
        st.error(f"Tidak dapat membaca jadual Supabase. Pastikan SQL setup berjaya dijalankan. Butiran: {exc}")
        st.stop()

    total = len(records)
    pending = sum(1 for r in records if r.get("status") == "pending")
    verified = sum(1 for r in records if r.get("status") == "verified")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah bukti", total)
    c2.metric("Menunggu semakan", pending)
    c3.metric("Disahkan sekolah", verified)

    tabs = st.tabs(["📋 Senarai rekod", "➕ Tambah rekod"] if role == "admin" else ["📋 Paparan rekod"])
    with tabs[0]:
        q = st.text_input("Cari nama murid / pertandingan / nombor rujukan", key="record_search").strip().lower()
        status = st.selectbox("Tapis status", ["Semua", "Menunggu semakan", "Disahkan sekolah", "Perlu pembetulan"])
        status_key = {"Menunggu semakan": "pending", "Disahkan sekolah": "verified", "Perlu pembetulan": "fix"}.get(status)
        filtered = [r for r in records if (not q or q in " ".join(str(r.get(k) or "") for k in ["student_name", "program", "reference_no", "issuer", "organizer", "verification_code"]).lower()) and (not status_key or r.get("status") == status_key)]
        display_records(client, filtered, role == "admin")
        if role == "admin" and records:
            rows_export = [{k: v for k, v in r.items() if k != "file_path"} for r in records]
            st.download_button("Muat turun metadata CSV", pd.DataFrame(rows_export).to_csv(index=False).encode("utf-8-sig"), "rekod-pajsk.csv", "text/csv")
    if role == "admin":
        with tabs[1]:
            add_record(client)


if __name__ == "__main__":
    main()
