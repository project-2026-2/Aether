"""
Amazon EFS Flask API
─────────────────────────────────────────
EFS 연동 설정:
  EFS_ROOT=/mnt/efs          AWS EFS 마운트 경로 (기본: ./efs_data)
  STORAGE_LIMIT=53687091200  저장 한도(bytes), 기본 50 GB

실행:
  python app.py                           # EFS 모드 (로컬 테스트)
  EFS_ROOT=/mnt/efs python app.py         # AWS EFS 연동 모드
"""

import os, io, json, mimetypes, tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

# ── 설정 ──────────────────────────────────────────────────────
EFS_ROOT         = Path(os.environ.get("EFS_ROOT", "efs_data"))  # AWS: /mnt/efs
STORAGE_LIMIT    = int(os.environ.get("STORAGE_LIMIT", str(50 * 1024 ** 3)))  # 50GB

app = Flask(
    __name__,
    template_folder="main",
    static_folder="main/style",
    static_url_path="/style",
)
CORS(app)

def ok(data=None):      return jsonify({"ok": True,  "data": data})
def err(msg, code=400): return jsonify({"ok": False, "error": msg}), code
def now_iso():          return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════
#  EFS 스토리지 백엔드
#  ─ efs_data/meta.json  : 파일 메타데이터 전체
#  ─ efs_data/files/     : 실제 파일 (파일 ID가 파일명)
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

    # ── 중복 파일명 해결 ──────────────────────────────────────
    def _resolve_name(self, name: str, folder_id=None, exclude_id=None) -> str:
        """같은 폴더 내 동일한 이름이 있으면 (1), (2) ... 를 붙여 반환"""
        meta = self._load()

        # 같은 부모 폴더의 파일명 집합 (trashed 제외, 자신 제외)
        siblings = {
            f["name"]
            for fid, f in meta.items()
            if not f.get("trashed")
            and fid != exclude_id
            and (f.get("parents") or [None])[0] == folder_id
        }

        if name not in siblings:
            return name

        # 확장자 분리
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

    # ── 파일 목록 ─────────────────────────────────────────────
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

    # ── 업로드 ────────────────────────────────────────────────
    def upload(self, file_obj, filename: str, folder_id=None) -> dict:
        fid  = str(uuid4())
        # 중복 파일명 처리
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

    # ── 다운로드 ──────────────────────────────────────────────
    def get_file(self, file_id):
        meta = self._load()
        if file_id not in meta: return None, None
        return self.files_dir / file_id, meta[file_id]

    # ── 수정 ──────────────────────────────────────────────────
    def update(self, file_id, body):
        meta = self._load()
        if file_id not in meta: return None
        f = meta[file_id]

        # 이름 변경 시 중복 검사
        if "name" in body:
            folder_id = (f.get("parents") or [None])[0]
            body["name"] = self._resolve_name(body["name"], folder_id, exclude_id=file_id)

        for k in ("name", "starred", "trashed"):
            if k in body: f[k] = body[k]
        if "newFolderId" in body: f["parents"] = [body["newFolderId"]]
        f["modifiedTime"] = now_iso()
        self._save(meta)
        return f

    # ── 영구 삭제 ─────────────────────────────────────────────
    def delete(self, file_id):
        meta = self._load(); meta.pop(file_id, None); self._save(meta)
        fp = self.files_dir / file_id
        if fp.exists(): fp.unlink()

    # ── 폴더 생성 ─────────────────────────────────────────────
    def create_folder(self, name, parent_id=None):
        fid = str(uuid4())
        # 중복 폴더명 처리
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

    # ── 휴지통 비우기 ─────────────────────────────────────────
    def empty_trash(self):
        meta = self._load()
        for fid in [k for k, v in meta.items() if v.get("trashed")]:
            meta.pop(fid); fp = self.files_dir / fid
            if fp.exists(): fp.unlink()
        self._save(meta)

    # ── 저장 용량 ─────────────────────────────────────────
    def storage_info(self):
        meta  = self._load()
        used  = sum(int(f.get("size", 0)) for f in meta.values() if not f.get("trashed"))
        trash = sum(int(f.get("size", 0)) for f in meta.values() if f.get("trashed"))
        return {"used": used, "total": STORAGE_LIMIT, "usageInTrash": trash,
                "displayName": "hayul", "email": ""}

    # ── 공유 권한 ─────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════
#  라우트
# ══════════════════════════════════════════════════════════════
@app.route("/")
def index(): return render_template("main.html")


@app.route("/api/files")
def list_files():
    try:
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
        file = request.files.get("file"); fid = request.form.get("folderId")
        if not file: return err("파일이 없습니다")
        return ok(efs.upload(file, file.filename, fid))
    except Exception as e: return err(str(e))


@app.route("/api/download/<fid>")
def download_file(fid):
    try:
        fp, rec = efs.get_file(fid)
        if not fp or not fp.exists(): return err("파일을 찾을 수 없습니다", 404)
        return send_file(fp, as_attachment=True, download_name=rec["name"],
                         mimetype=rec.get("mimeType", "application/octet-stream"))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>", methods=["PATCH"])
def update_file(fid):
    try:
        body = request.json or {}
        f = efs.update(fid, body)
        return ok(f) if f else err("파일을 찾을 수 없습니다", 404)
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>", methods=["DELETE"])
def delete_file(fid):
    try:
        efs.delete(fid)
        return ok({"id": fid})
    except Exception as e: return err(str(e))


@app.route("/api/trash", methods=["DELETE"])
def empty_trash():
    try:
        efs.empty_trash()
        return ok({"message": "휴지통을 비웠습니다"})
    except Exception as e: return err(str(e))


@app.route("/api/folders", methods=["POST"])
def create_folder():
    try:
        data = request.json or {}
        name, pid = data.get("name", "새 폴더"), data.get("parentId")
        return ok(efs.create_folder(name, pid))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions")
def get_permissions(fid):
    try:
        return ok(efs.list_perms(fid))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions", methods=["POST"])
def add_permission(fid):
    try:
        data = request.json or {}
        return ok(efs.add_perm(fid, {"type": data.get("type","user"),
                                      "role": data.get("role","reader"),
                                      "emailAddress": data.get("email","")}))
    except Exception as e: return err(str(e))


@app.route("/api/files/<fid>/permissions/<pid>", methods=["DELETE"])
def remove_permission(fid, pid):
    try:
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

        if is_text and size < 512 * 1024:  # 512KB 이하만 텍스트 미리보기
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return ok({"type": "text", "content": content, "name": name, "size": size, "ext": ext})

        return ok({"type": "binary", "name": name, "size": size, "ext": ext})

    except Exception as e:
        return err(str(e))


@app.route("/api/storage")
def get_storage():
    try:
        return ok(efs.storage_info())
    except Exception as e: return err(str(e))


if __name__ == "__main__":
    print(f"\n  스토리지 모드: 🗂️  EFS (Amazon EFS / 로컬)")
    print(f"  EFS 경로     : {EFS_ROOT.resolve()}")
    print(f"  저장 한도    : {STORAGE_LIMIT / (1024**3):.1f} GB")
    print(f"  서버 주소    : http://localhost:5000\n")
    app.run(debug=True, port=5000)