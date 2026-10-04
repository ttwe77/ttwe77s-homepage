#!/usr/bin/env python3
# app.py — 个人状态 API（写 status.json 供 nginx 静态托管）
#
#   GET  /api/status   公开读
#   POST /api/status   全量覆盖（需要 API Key）
#   GET  /api/health   健康检查
#
# status.json 结构：
# {
#   "name": "ttwe77",
#   "status": "online",
#   "status_text": "在线",
#   "program_name": "WindowsTerminal",
#   "program_title": "命令提示符",
#   "since": "2026-10-02T23:17:00+08:00",
#   "server_updated": "2026-10-02T23:17:00+08:00"
# }
import contextlib
import copy
import datetime
import json
import os
import secrets
import tempfile
if os.name == "nt":
    import msvcrt
else:
    import fcntl

from flask import Flask, jsonify, request

# ----------------------- 配置 -----------------------
def _default_token_file():
    """token 文件默认放在 main.py 同目录下的 .api_token。"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".api_token")


CONFIG = {
    # status.json 的绝对路径，必须和 nginx root 一致
    "file": os.environ.get("STATUS_FILE", r"device-01.json"),
    # 可选：静态 API Key（为空则只用自动生成的 token）
    "api_key": os.environ.get("STATUS_API_KEY", ""),
    # token 文件位置（默认在 main.py 同目录）
    "token_file": os.environ.get("STATUS_TOKEN_FILE", _default_token_file()),
    "bind": os.environ.get("STATUS_BIND", "127.0.0.1"),
    "port": int(os.environ.get("STATUS_PORT", "5000")),
    # 允许前端跨域直连后端（同域部署时不需要）
    "cors": os.environ.get("STATUS_CORS", "0") == "1",
}

VALID_STATUS = {"online", "away", "busy", "offline"}

DEFAULT = {
    "name": "未命名",
    "status": "offline",
    "status_text": "离线",
    "program_name": "",
    "program_title": "",
    "since": None,
    "server_updated": None,
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024   # 请求体最大 64KB
app.json.ensure_ascii = False


# ----------------------- 工具 -----------------------
class ApiError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


def now_iso():
    """当前时间，带本地时区，精确到秒。"""
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value, field):
    """把字符串解析成 ISO 时间，兼容末尾的 Z。"""
    if not isinstance(value, str):
        raise ApiError(f"{field} 必须是 ISO 时间字符串，如 2026-10-02T12:00:00+08:00")
    s = value.strip().replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s).isoformat(timespec="seconds")
    except ValueError:
        raise ApiError(f"{field} 不是合法的 ISO 时间：{value}")


def clean_str(value, maxlen, field, allow_empty=True):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ApiError(f"{field} 必须是字符串")
    value = value.strip()
    if not allow_empty and not value:
        raise ApiError(f"{field} 不能为空")
    if len(value) > maxlen:
        raise ApiError(f"{field} 过长（最多 {maxlen} 字符）")
    return value


# ----------------------- token 生成 / 加载 -----------------------
def load_or_create_token():
    """
    读取 token 文件；不存在则自动生成并落盘。
    - 文件位置：CONFIG["token_file"]，默认 main.py 同目录 .api_token
    - 原子写：先写 .token-xxx.tmp 再 os.replace，避免并发读到半截
    - Linux/macOS 权限 0600，仅当前用户可读写
    """
    path = os.path.abspath(CONFIG["token_file"])
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    # 1) 已存在 → 直接读取
    try:
        with open(path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if token:
            return token
    except FileNotFoundError:
        pass

    # 2) 生成新 token 并原子落盘
    token = secrets.token_urlsafe(32)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".token-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(token + "\n")
            f.flush()
            os.fsync(f.fileno())
        with contextlib.suppress(OSError):
            os.chmod(tmp, 0o600)      # 仅当前用户可读写
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return token


API_TOKEN = load_or_create_token()


# ----------------------- 原子读写 + 进程锁 -----------------------
@contextlib.contextmanager
def locked():
    """跨进程文件锁，保证 read-modify-write 不会互相覆盖。"""
    lock_path = CONFIG["file"] + ".lock"
    d = os.path.dirname(os.path.abspath(lock_path))
    if d:
        os.makedirs(d, exist_ok=True)
    f = open(lock_path, "a+")
    try:
        if os.name == "nt":
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def read_status():
    try:
        with open(CONFIG["file"], "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return copy.deepcopy(DEFAULT)


def write_status(data):
    """先写临时文件再 os.replace，避免 nginx 读到半截 JSON。"""
    path = os.path.abspath(CONFIG["file"])
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".status-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)          # 让 nginx 能读
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def commit(data):
    """统一打上服务端时间戳后落盘。"""
    data["server_updated"] = now_iso()
    write_status(data)
    return data


# ----------------------- 鉴权 / CORS -----------------------
def _supplied_token():
    """从 Header 或 Query 中提取调用方提交的 token。

    支持三种传递方式（优先级从上到下）：
      1. Header: X-API-Key: <token>
      2. Header: Authorization: Bearer <token>
      3. Query : ?key=<token>
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        auth = auth[7:].strip()
    else:
        auth = ""
    return (
        request.headers.get("X-API-Key")
        or auth
        or request.args.get("key")
        or ""
    )


def require_key():
    """写操作鉴权。

    匹配规则：请求携带的 token 与环境变量 STATUS_API_KEY
    或自动生成的 .api_token 任意一个匹配即通过。
    使用 secrets.compare_digest 做常量时间比较，避免时序侧信道。
    """
    supplied = _supplied_token()
    if not supplied:
        raise ApiError("你干嘛，哎害哟~", 401)

    candidates = [t for t in (CONFIG["api_key"], API_TOKEN) if t]
    if not any(secrets.compare_digest(supplied, t) for t in candidates):
        raise ApiError("你干嘛，哎害哟~", 401)


@app.after_request
def add_headers(resp):
    if CONFIG["cors"]:
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def preflight(_any):
    return ("", 204)


@app.errorhandler(ApiError)
def on_api_error(e):
    return jsonify(ok=False, error=e.message), e.code


@app.errorhandler(404)
def on_404(e):
    return jsonify(ok=False, error="接口不存在"), 404


@app.errorhandler(413)
def on_413(e):
    return jsonify(ok=False, error="请求体过大"), 413


def get_json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("请求体必须是 JSON 对象，且 Content-Type: application/json")
    return body


# ----------------------- 接口 -----------------------
@app.get("/api/status")
def get_status():
    """读接口：公开（数据本身就是给前端展示的）。"""
    return jsonify(ok=True, status=read_status())


@app.post("/api/status")
def replace_status():
    """全量覆盖：请求体就是最终状态，未提供的字段回落到默认值。需要 token。

    请求体示例：
    {
      "name": "ttwe77",
      "status": "online",
      "status_text": "在线",
      "program_name": "WindowsTerminal",
      "program_title": "命令提示符",
      "since": "2026-10-02T23:17:00+08:00"
    }
    """
    require_key()
    body = get_json_body()

    data = copy.deepcopy(DEFAULT)

    if "name" in body:
        data["name"] = clean_str(body["name"], 32, "name", allow_empty=False)
    if "status" in body:
        s = clean_str(body["status"], 16, "status").lower()
        if s not in VALID_STATUS:
            raise ApiError("status 只能是 " + " / ".join(sorted(VALID_STATUS)))
        data["status"] = s
    if "status_text" in body:
        data["status_text"] = clean_str(body["status_text"], 32, "status_text")
    if "program_name" in body:
        data["program_name"] = clean_str(body["program_name"], 64, "program_name")
    if "program_title" in body:
        data["program_title"] = clean_str(body["program_title"], 64, "program_title")
    
    # since 不传则取当前时间
    data["since"] = parse_iso(body["since"], "since") if body.get("since") else now_iso()

    with locked():
        commit(data)
    return jsonify(ok=True, status=data)


@app.get("/api/health")
def health():
    return jsonify(ok=True, time=now_iso())


if __name__ == "__main__":
    print(f"[status-api] 写入文件: {CONFIG['file']}")
    print(f"[status-api] 监听: {CONFIG['bind']}:{CONFIG['port']}")
    print(f"[status-api] Token 文件: {os.path.abspath(CONFIG['token_file'])}")
    print(f"[status-api] Token 预览: {API_TOKEN[:8]}…（完整值请查看 token 文件）")
    app.run(host=CONFIG["bind"], port=CONFIG["port"], debug=False)