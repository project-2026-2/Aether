import os
import io
import json
import requests
import mimetypes
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_cors import CORS
from db_manager import add_user, check_user, add_google_user, create_reset_token, reset_password
from oauth_manager import init_oauth
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800
)

CORS(app)

oauth_client = init_oauth(app)

# ── EFS 설정 ──────────────────────────────────────────────────────
EFS_ROOT         = Path(os.environ.get("EFS_ROOT", "efs_data"))
STORAGE_LIMIT    = int(os.environ.get("STORAGE_LIMIT", str(50 * 1024 ** 3)))

def ok(data=None):      return jsonify({"ok": True,  "data": data})
def err(msg, code=400): return jsonify({"ok": False, "error": msg}), code
def now_iso():          return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════
#  EFS 스토리지 백엔드
# ══════════════════════════════════════════════════════════════
class EFSStorage:

    def __init__(self, root: Path):
        self.root      = root
        self.files_dir = root / "files"
        self.meta_path = root / "meta.json"
        root.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(exist_ok=True)

    def _load(self) -> dict:
        if not self.meta_path.exists():
            return {}
        with open(self.meta_path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, meta: dict):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _resolve_name(self, name: str, folder_id=None, exclude_id=None) -> str:
        """같은 폴더 내 동일한 이름이 있으면 (1), (2) ... 를 붙여 반환"""
        meta = self._load()
        siblings = {
            f["name"]
            for fid, f in meta.items()
            if not f.get("trashed")
            and fid != exclude_id
            and (f.get("parents") or [None])[0] == folder_id
        }

        if name not in siblings:
            return name

        if "." in name:
            stem, ext = name.rsplit(".", 1)
            ext = "." + ext
        else:
            stem, ext = name, ""

        counter = 1
        while True:
            candidate = f"{stem}({counter}){ext}"
            if candidate not in siblings:
                return candidate
            counter += 1

    def list_files(self, folder_id=None, trashed=False, starred=False,
                   keyword="", order_by="modifiedTime desc", page_size=50) -> list:
        files = [f for f in self._load().values()
                 if f.get("trashed", False) == trashed]

        if folder_id:
            files = [f for f in files if folder_id in f.get("parents", [])]
        else:
            files = [f for f in files if not f.get("parents")]

        if starred: files = [f for f in files if f.get("starred")]
        if keyword: files = [f for f in files if keyword.lower() in f["name"].lower()]

        rev = "desc" in order_by
        key = "modifiedTime" if "modifiedTime" in order_by else "name"
        files.sort(key=lambda f: f.get(key, ""), reverse=rev)
        return files[:page_size]

    def upload(self, file_obj, filename: str, folder_id=None) -> dict:
        fid  = str(uuid4())
        filename = self._resolve_name(filename, folder_id)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        dest = self.files_dir / fid
        file_obj.save(str(dest))
        record = {
            "id": fid, "name": filename, "mimeType": mime,
            "size": str(dest.stat().st_size),
            "starred": False, "shared": False, "trashed": False,
            "modifiedTime": now_iso(),
            "parents":  [folder_id] if folder_id else [],
            "webViewLink": f"/api/download/{fid}",
            "permissions": [],
        }
        meta = self._load(); meta[fid] = record; self._save(meta)
        return record

    def get_file(self, file_id):
        meta = self._load()
        if file_id not in meta: return None, None
        return self.files_dir / file_id, meta[file_id]

    def update(self, file_id, body):
        meta = self._load()
        if file_id not in meta: return None
        f = meta[file_id]

        if "name" in body:
            folder_id = (f.get("parents") or [None])[0]
            body["name"] = self._resolve_name(body["name"], folder_id, exclude_id=file_id)

        for k in ("name", "starred", "trashed"):
            if k in body: f[k] = body[k]
        if "newFolderId" in body: f["parents"] = [body["newFolderId"]]
        f["modifiedTime"] = now_iso()
        self._save(meta)
        return f

    def delete(self, file_id):
        meta = self._load(); meta.pop(file_id, None); self._save(meta)
        fp = self.files_dir / file_id
        if fp.exists(): fp.unlink()

    def create_folder(self, name, parent_id=None):
        fid = str(uuid4())
        name = self._resolve_name(name, parent_id)
        record = {
            "id": fid, "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "size": "0", "starred": False, "shared": False, "trashed": False,
            "modifiedTime": now_iso(),
            "parents": [parent_id] if parent_id else [],
            "webViewLink": None, "permissions": [],
        }
        meta = self._load(); meta[fid] = record; self._save(meta)
        return record

    def empty_trash(self):
        meta = self._load()
        for fid in [k for k, v in meta.items() if v.get("trashed")]:
            meta.pop(fid); fp = self.files_dir / fid
            if fp.exists(): fp.unlink()
        self._save(meta)

    def storage_info(self):
        meta  = self._load()
        used  = sum(int(f.get("size", 0)) for f in meta.values() if not f.get("trashed"))
        trash = sum(int(f.get("size", 0)) for f in meta.values() if f.get("trashed"))
        return {"used": used, "total": STORAGE_LIMIT, "usageInTrash": trash,
                "displayName": "hayul", "email": ""}

    def list_perms(self, fid):
        return self._load().get(fid, {}).get("permissions", [])

    def add_perm(self, fid, perm):
        meta = self._load(); f = meta.get(fid)
        if not f: return {}
        perm["id"] = str(uuid4())
        f.setdefault("permissions", []).append(perm)
        if perm.get("type") == "anyone": f["shared"] = True
        self._save(meta); return perm

    def remove_perm(self, fid, perm_id):
        meta = self._load(); f = meta.get(fid)
        if f:
            f["permissions"] = [p for p in f.get("permissions", []) if p["id"] != perm_id]
            self._save(meta)


efs = EFSStorage(EFS_ROOT)

# ── BE static 파일 서빙 ────────────────────────────────────
@app.route("/be-static/<path:filename>")
def serve_be_static(filename):
    """BE/main/style 폴더의 파일 서빙 (CSS, JS 등)"""
    from flask import send_from_directory, abort
    be_style_path = Path(__file__).parent / 'BE' / 'main' / 'style'
    
    # 파일이 존재하는지 확인
    file_path = be_style_path / filename
    if file_path.exists() and file_path.is_file():
        return send_from_directory(be_style_path, filename)
    
    # 파일을 찾을 수 없으면 404 에러 반환
    abort(404)


@app.route('/', methods=['GET', 'POST'])
def test_search():
    user = session.get('user')
    # 로그인 상태면 루트 접근 시 바로 메인 페이지를 렌더링합니다.
    if user:
        return render_template('main.html', user=user)
    # 미로그인 상태면 인덱스(랜딩) 페이지를 보여줍니다.
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email')

        if password != password_confirm:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('register.html')

        if add_user(username, password, email):
            flash('회원가입 성공!')
            return redirect(url_for('login'))
        else:
            flash('이미 존재하는 아이디 또는 이메일입니다.')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = check_user(username, password)

        if user:
            session.clear()
            session['user'] = user['username']
            session['login_type'] = user.get('login_type', 'local')
            flash('login_success')
            # 로그인 후에는 루트('/')로 이동시키면 루트에서 로그인 상태에 따라
            # main.html을 렌더링하도록 처리해놓았습니다.
            return redirect(url_for('test_search'))
        flash('정보가 올바르지 않습니다.')
    return render_template('login.html')


@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return oauth_client.google.authorize_redirect(redirect_uri)


@app.route('/auth/google')
def google_auth():
    try:
        token = oauth_client.google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            user = add_google_user(user_info['name'], user_info['email'])
            if user:
                session.clear()
                session['user'] = user['username']
                session.modified = True
                flash('login_success')
                # 구글 로그인 성공 후에도 루트로 리디렉트
                return redirect(url_for('test_search'))

    except Exception as e:
        print(f"Auth Error: {e}")
        flash("로그인 실패")
    return redirect(url_for('login'))


@app.route('/main')
def main_dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('main.html', user=user)


@app.route('/logout')
def logout():
    session.clear()
    flash('logged_out_success')
    return redirect(url_for('test_search'))


def send_reset_email(to_email, token):
    reset_url = f"http://localhost:5050/reset/{token}"

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": "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",
            "Content-Type": "application/json"
        },
        json={
            "sender": {"name": "Aether", "email": "hayul9888@gmail.com"},
            "to": [{"email": to_email}],
            "subject": "비밀번호 재설정",
            "textContent": f"아래 링크를 클릭하여 비밀번호를 재설정하세요:\n\n{reset_url}"
        }
    )
    print(response.status_code, response.text)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        token = create_reset_token(email)
        if token:
            send_reset_email(email, token)
        flash('이메일이 존재하면 재설정 링크를 전송했습니다.')
        return redirect(url_for('forgot'))
    return render_template('forgot.html')


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    if request.method == 'POST':
        new_pw = request.form.get('password')
        confirm_pw = request.form.get('password_confirm')
        if new_pw != confirm_pw:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('reset.html', token=token)
        if reset_password(token, new_pw):
            flash('비밀번호가 변경되었습니다!')
            return redirect(url_for('login'))
        flash('링크가 만료되었습니다.')
        return redirect(url_for('forgot'))
    return render_template('reset.html', token=token)


# ══════════════════════════════════════════════════════════════
#  파일 관리 API (통합)
# ══════════════════════════════════════════════════════════════

@app.route("/api/files")
def list_files():
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        folder_id = request.args.get("folderId")
        trashed   = request.args.get("trashed", "false") == "true"
        starred   = request.args.get("starred", "false") == "true"
        keyword   = request.args.get("q", "")
        page_size = int(request.args.get("pageSize", 50))
        order_by  = request.args.get("orderBy", "modifiedTime desc")

        return ok(efs.list_files(folder_id=folder_id, trashed=trashed,
                                 starred=starred, keyword=keyword,
                                 order_by=order_by, page_size=page_size))
    except Exception as e: return err(str(e))


@app.route("/api/upload", methods=["POST"])
def upload_file():
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        file = request.files.get("file")
        fid = request.form.get("folderId")
        if not file: return err("파일이 없습니다")
        return ok(efs.upload(file, file.filename, fid))
    except Exception as e: return err(str(e))


@app.route("/api/download/<fid>")
def download_file(fid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        fp, rec = efs.get_file(fid)
        if not fp or not fp.exists(): return err("파일을 찾을 수 없습니다", 404)
        return send_file(fp, as_attachment=True, download_name=rec["name"],
                         mimetype=rec.get("mimeType", "application/octet-stream"))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>", methods=["PATCH"])
def update_file(fid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        body = request.json or {}
        f = efs.update(fid, body)
        return ok(f) if f else err("파일을 찾을 수 없습니다", 404)
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>", methods=["DELETE"])
def delete_file(fid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        efs.delete(fid)
        return ok({"id": fid})
    except Exception as e: return err(str(e))


@app.route("/api/trash", methods=["DELETE"])
def empty_trash():
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        efs.empty_trash()
        return ok({"message": "휴지통을 비웠습니다"})
    except Exception as e: return err(str(e))


@app.route("/api/folders", methods=["POST"])
def create_folder():
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        data = request.json or {}
        name, pid = data.get("name", "새 폴더"), data.get("parentId")
        return ok(efs.create_folder(name, pid))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions")
def get_permissions(fid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        return ok(efs.list_perms(fid))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions", methods=["POST"])
def add_permission(fid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        data = request.json or {}
        return ok(efs.add_perm(fid, {"type": data.get("type","user"),
                                      "role": data.get("role","reader"),
                                      "emailAddress": data.get("email","")}))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions/<pid>", methods=["DELETE"])
def remove_permission(fid, pid):
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        efs.remove_perm(fid, pid)
        return ok({"permissionId": pid})
    except Exception as e: return err(str(e))


@app.route("/api/preview/<fid>")
def preview_file(fid):
    """텍스트 계열 파일 내용을 반환"""
    TEXT_MIME = {
        'text/', 'application/json', 'application/javascript',
        'application/xml', 'application/x-python', 'application/x-sh',
    }
    TEXT_EXT = {
        'txt', 'md', 'py', 'js', 'ts', 'html', 'css', 'json', 'xml', 'csv',
        'sh', 'bat', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'log', 'sql',
        'c', 'cpp', 'h', 'java', 'kt', 'rs', 'go', 'rb', 'php', 'swift',
    }
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        fp, rec = efs.get_file(fid)
        if not fp or not fp.exists():
            return err("파일을 찾을 수 없습니다", 404)
        name = rec.get("name", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        mime = rec.get("mimeType", "")
        is_text = ext in TEXT_EXT or any(mime.startswith(m) for m in TEXT_MIME)
        is_img = ext in {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"}
        size = fp.stat().st_size

        if is_img:
            import base64
            with open(fp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img_mime = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg",
                        "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp",
                        "bmp": "image/bmp", "ico": "image/x-icon"}.get(ext, "image/png")
            return ok({"type": "image", "dataUrl": f"data:{img_mime};base64,{b64}", "name": name, "size": size})

        if is_text and size < 512 * 1024:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return ok({"type": "text", "content": content, "name": name, "size": size, "ext": ext})

        return ok({"type": "binary", "name": name, "size": size, "ext": ext})

    except Exception as e:
        return err(str(e))


@app.route("/api/storage")
def get_storage():
    try:
        user = session.get('user')
        if not user:
            return err("로그인 필요", 401)

        return ok(efs.storage_info())
    except Exception as e: return err(str(e))


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"  🚀 Aether - 통합 서버 시작")
    print(f"{'='*60}")
    print(f"  📍 로그인: http://localhost:5050/login")
    print(f"  📁 파일관리: http://localhost:5050/main")
    print(f"  🗂️  EFS 경로: {EFS_ROOT.resolve()}")
    print(f"  💾 저장 한도: {STORAGE_LIMIT / (1024**3):.1f} GB")
    print(f"  🔧 DEBUG: True")
    print(f"{'='*60}\n")
    app.run("0.0.0.0", debug=True, port=5050)