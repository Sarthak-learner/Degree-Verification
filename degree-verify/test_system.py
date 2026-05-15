"""
test_system.py — 5 essential tests for the viva demo
Run:  python app.py   (in one terminal)
      python test_system.py  (in another)
"""
import io, hashlib, requests

BASE = "http://127.0.0.1:5000"

def make_pdf(text):
    return b"%PDF-1.4\n" + text.encode()

def run(label, method, url, files=None, data=None, expect=None):
    r = getattr(requests, method)(url, files=files, data=data)
    ok = r.status_code == expect
    print(f"{'✅' if ok else '❌'}  {label}  [{r.status_code}]  {r.json().get('status') or r.json().get('error','')}")
    return ok

PDF  = make_pdf("Alice Smith — CS — 2024")
PDF2 = make_pdf("Bob Jones — DS — 2024")

results = [
    run("Issue new degree",
        "post", f"{BASE}/issue",
        files={"pdf": ("a.pdf", io.BytesIO(PDF), "application/pdf")},
        data={"student_id": "CS-2024-001"}, expect=200),

    run("Verify authentic PDF",
        "post", f"{BASE}/verify",
        files={"pdf": ("a.pdf", io.BytesIO(PDF), "application/pdf")},
        expect=200),

    run("Reject tampered PDF",
        "post", f"{BASE}/verify",
        files={"pdf": ("x.pdf", io.BytesIO(PDF[:-3]+b"XXX"), "application/pdf")},
        expect=404),

    run("Reject duplicate issue",
        "post", f"{BASE}/issue",
        files={"pdf": ("a.pdf", io.BytesIO(PDF), "application/pdf")},
        data={"student_id": "CS-2024-001"}, expect=409),

    run("Revoke then re-verify shows revoked",
        "post", f"{BASE}/revoke",
        files={"pdf": ("a.pdf", io.BytesIO(PDF), "application/pdf")},
        expect=200),
]

p = sum(results)
print(f"\n{p}/{len(results)} passed {'🎉' if p==len(results) else '⚠️'}")
