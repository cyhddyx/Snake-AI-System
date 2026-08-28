import argparse
import json
import mimetypes
import shutil
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parent
STORAGE_DIR = ROOT_DIR / "storage"
SOURCE_DIR = ROOT_DIR / "images"
ALLOWED_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
}


def ensure_directories() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def is_allowed_image_file(file_path: Path) -> bool:
    return file_path.is_file() and file_path.suffix.lower() in ALLOWED_SUFFIXES


def copy_image_to_storage(source_path: Path) -> str:
    if not source_path.exists():
        raise FileNotFoundError(f"文件不存在: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"路径不是文件: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"不支持的图片格式: {suffix or '无扩展名'}")

    filename = f"{uuid.uuid4().hex}{suffix}"
    target_path = STORAGE_DIR / filename
    shutil.copy2(source_path, target_path)
    return filename


def guess_content_type(file_path: Path) -> str:
    content_type, _ = mimetypes.guess_type(file_path.name)
    return content_type or "application/octet-stream"


def resolve_file_under(base_dir: Path, relative_path: str) -> Path:
    base_root = base_dir.resolve()
    candidate = (base_root / relative_path).resolve()
    if candidate != base_root and base_root not in candidate.parents:
        raise ValueError("非法文件路径")
    return candidate


def iter_source_images() -> list[Path]:
    if not SOURCE_DIR.exists():
        return []
    return sorted(
        file_path
        for file_path in SOURCE_DIR.rglob("*")
        if is_allowed_image_file(file_path)
    )


class ImageUrlHandler(BaseHTTPRequestHandler):
    server_version = "ImageUrlServer/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def _json_response(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("请求体不是合法 JSON") from exc

    def _read_multipart_upload(self) -> tuple[bytes, str]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("请求必须是 multipart/form-data")

        boundary_marker = "boundary="
        if boundary_marker not in content_type:
            raise ValueError("multipart/form-data 缺少 boundary")

        boundary = content_type.split(boundary_marker, 1)[1].strip().strip('"')
        if not boundary:
            raise ValueError("multipart/form-data boundary 无效")

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            raise ValueError("上传文件为空")

        boundary_bytes = f"--{boundary}".encode("utf-8")
        parts = raw_body.split(boundary_bytes)
        for part in parts:
            part = part.lstrip(b"\r\n")
            if not part or part in {b"--", b"--\r\n"}:
                continue

            header_block, separator, body = part.partition(b"\r\n\r\n")
            if not separator:
                continue

            headers = header_block.decode("utf-8", errors="ignore").split("\r\n")
            disposition = next(
                (line for line in headers if line.lower().startswith("content-disposition:")),
                "",
            )
            if 'name="file"' not in disposition or 'filename="' not in disposition:
                continue

            filename = disposition.split('filename="', 1)[1].split('"', 1)[0].strip()
            if not filename:
                raise ValueError("上传文件缺少文件名")

            file_bytes = body.rstrip(b"\r\n")
            if not file_bytes:
                raise ValueError("上传文件为空")
            return file_bytes, Path(filename).name

        raise ValueError("请上传文件字段 file")

    def _build_base_url(self) -> str:
        host_header = self.headers.get("Host")
        if host_header:
            return f"http://{host_header}"

        server_host, server_port = self.server.server_address[:2]
        if server_host == "0.0.0.0":
            server_host = "127.0.0.1"
        return f"http://{server_host}:{server_port}"

    def _serve_file(self, base_dir: Path, relative_path: str) -> None:
        try:
            candidate = resolve_file_under(base_dir, relative_path)
        except ValueError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if not candidate.exists() or not candidate.is_file():
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "图片不存在"})
            return
        if not is_allowed_image_file(candidate):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "不支持的图片格式"})
            return

        content = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guess_content_type(candidate))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_image_route(self, relative_path: str) -> None:
        try:
            storage_candidate = resolve_file_under(STORAGE_DIR, relative_path)
            source_candidate = resolve_file_under(SOURCE_DIR, relative_path)
        except ValueError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if storage_candidate.exists() and is_allowed_image_file(storage_candidate):
            self._serve_file(STORAGE_DIR, relative_path)
            return

        if source_candidate.exists() and is_allowed_image_file(source_candidate):
            self._serve_file(SOURCE_DIR, relative_path)
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "图片不存在"})

    def _list_source_images(self) -> None:
        base_url = self._build_base_url()
        images = [
            {
                "relative_path": file_path.relative_to(SOURCE_DIR).as_posix(),
                "url": f"{base_url}/images/{quote(file_path.relative_to(SOURCE_DIR).as_posix(), safe='/')}",
            }
            for file_path in iter_source_images()
        ]
        self._json_response(
            HTTPStatus.OK,
            {
                "count": len(images),
                "directory": str(SOURCE_DIR.resolve()),
                "items": images,
            },
        )

    def _save_uploaded_bytes(self, file_bytes: bytes, original_name: str) -> str:
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"不支持的图片格式: {suffix or '无扩展名'}")

        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = STORAGE_DIR / filename
        target_path.write_bytes(file_bytes)
        return filename

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._json_response(HTTPStatus.OK, {"status": "ok"})
            return

        if path == "/api/source-images/list":
            self._list_source_images()
            return

        if path.startswith("/images/"):
            filename = unquote(path.removeprefix("/images/"))
            if not filename:
                self._json_response(HTTPStatus.BAD_REQUEST, {"error": "缺少图片文件名"})
                return
            self._serve_image_route(filename)
            return

        if path.startswith("/source-images/"):
            relative_path = unquote(path.removeprefix("/source-images/"))
            if not relative_path:
                self._json_response(HTTPStatus.BAD_REQUEST, {"error": "缺少图片相对路径"})
                return
            self._serve_file(SOURCE_DIR, relative_path)
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/images/import", "/api/images/upload"}:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "接口不存在"})
            return

        try:
            if parsed.path == "/api/images/import":
                body = self._read_json_body()
                raw_path = body.get("path", "").strip()
                if not raw_path:
                    raise ValueError("请传入本地图片路径 path")

                source_path = Path(raw_path).expanduser().resolve(strict=False)
                filename = copy_image_to_storage(source_path)
            else:
                file_bytes, original_name = self._read_multipart_upload()
                filename = self._save_uploaded_bytes(file_bytes, original_name)
        except (FileNotFoundError, ValueError) as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:
            self._json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"处理失败: {exc}"},
            )
            return

        base_url = self._build_base_url()
        stored_path = str((STORAGE_DIR / filename).resolve())
        self._json_response(
            HTTPStatus.CREATED,
            {
                "filename": filename,
                "stored_path": stored_path,
                "url": f"{base_url}/images/{filename}",
            },
        )

    def log_message(self, format: str, *args) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将本地图片转换为可访问 URL 的简单后端服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    parser.add_argument("--port", type=int, default=8003, help="监听端口，默认 8003")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()

    server = ThreadingHTTPServer((args.host, args.port), ImageUrlHandler)
    print(f"Image URL server started at http://{args.host}:{args.port}")
    print(f"Storage directory: {STORAGE_DIR}")
    print(f"Source directory: {SOURCE_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
