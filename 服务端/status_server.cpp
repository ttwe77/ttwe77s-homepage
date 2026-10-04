// status_server.cpp
// -----------------------------------------------------------------------------
// 编译（启用 HTTPS）：
//   g++ -std=c++17 -O2 -pthread -DCPPHTTPLIB_OPENSSL_SUPPORT -o status_server status_server.cpp -I . -lssl -lcrypto
//
// 编译（仅 HTTP，无需 OpenSSL）：
//   g++ -std=c++17 -O2 -pthread -o status_server status_server.cpp -I .
//
// 依赖（header-only，放到 include 路径或与源码同目录）：
//   httplib.h    : https://github.com/yhirose/cpp-httplib/releases
//   json.hpp     : https://github.com/nlohmann/json/releases
//   OpenSSL      : 仅 HTTPS 需要 (libssl-dev / openssl-devel)
//
// 配置文件（INI 格式，默认路径 = 可执行文件同目录 / status_server.ini）：
//   使用 -c / --config <path> 可指定其它位置。
//   若文件不存在，程序会生成模板并退出，请编辑后重新运行。
// -----------------------------------------------------------------------------

#ifdef CPPHTTPLIB_OPENSSL_SUPPORT
#include <openssl/opensslv.h>
#endif

#include <libs/httplib.h>
#include <libs/json.hpp>

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

using json = nlohmann::json;
namespace fs = std::filesystem;

// ============================ 基础字符串工具 ============================
static std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

static std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return (char)std::tolower(c); });
    return s;
}

static size_t utf8_len(const std::string& s) {
    size_t n = 0;
    for (unsigned char c : s) if ((c & 0xC0) != 0x80) ++n;
    return n;
}

// ============================ INI 解析器 ============================
class IniFile {
public:
    // 返回 false 表示文件不存在/无法打开；语法错误抛出异常
    bool load(const std::string& path) {
        std::ifstream f(path);
        if (!f) return false;

        std::string line, section;
        int lineno = 0;
        while (std::getline(f, line)) {
            ++lineno;
            // 去掉 BOM
            if (lineno == 1 && line.size() >= 3 &&
                (unsigned char)line[0] == 0xEF &&
                (unsigned char)line[1] == 0xBB &&
                (unsigned char)line[2] == 0xBF) {
                line.erase(0, 3);
            }
            std::string s = trim(line);
            if (s.empty() || s[0] == '#' || s[0] == ';') continue;

            if (s.front() == '[') {
                auto rb = s.find(']');
                if (rb == std::string::npos)
                    throw std::runtime_error("配置文件第 " + std::to_string(lineno) +
                                             " 行：节名缺少 ']'");
                section = trim(s.substr(1, rb - 1));
                continue;
            }

            auto eq = s.find('=');
            if (eq == std::string::npos)
                throw std::runtime_error("配置文件第 " + std::to_string(lineno) +
                                         " 行：缺少 '='");
            std::string key = trim(s.substr(0, eq));
            std::string val = trim(s.substr(eq + 1));

            // 去掉行尾注释（如果值没有被引号包住）
            if (!(val.size() >= 2 &&
                  ((val.front() == '"'  && val.back() == '"') ||
                   (val.front() == '\'' && val.back() == '\'')))) {
                auto cut = val.find_first_of("#;");
                if (cut != std::string::npos) {
                    val = trim(val.substr(0, cut));
                }
            }
            // 剥掉外层引号
            if (val.size() >= 2 &&
                ((val.front() == '"'  && val.back() == '"') ||
                 (val.front() == '\'' && val.back() == '\''))) {
                val = val.substr(1, val.size() - 2);
            }
            if (key.empty())
                throw std::runtime_error("配置文件第 " + std::to_string(lineno) +
                                         " 行：键名为空");
            data_[section][key] = val;
        }
        return true;
    }

    std::string get(const std::string& sec, const std::string& key,
                    const std::string& def = "") const {
        auto sit = data_.find(sec);
        if (sit == data_.end()) return def;
        auto kit = sit->second.find(key);
        if (kit == sit->second.end()) return def;
        return kit->second;
    }

    int get_int(const std::string& sec, const std::string& key, int def) const {
        std::string v = get(sec, key, "");
        if (v.empty()) return def;
        try { return std::stoi(v); }
        catch (...) {
            throw std::runtime_error("配置项 " + sec + "." + key +
                                     " 必须是整数，当前值：" + v);
        }
    }

    bool get_bool(const std::string& sec, const std::string& key, bool def) const {
        std::string v = to_lower(get(sec, key, ""));
        if (v.empty()) return def;
        if (v == "1" || v == "true"  || v == "yes" || v == "on")  return true;
        if (v == "0" || v == "false" || v == "no"  || v == "off") return false;
        throw std::runtime_error("配置项 " + sec + "." + key +
                                 " 必须是 true/false，当前值：" + v);
    }

private:
    std::map<std::string, std::map<std::string, std::string>> data_;
};

// ============================ 配置 ============================
struct Config {
    std::string file;         // status.json 绝对路径
    std::string api_key;      // 可选静态 API Key
    std::string token_file;   // token 文件位置
    std::string bind;         // 监听地址
    int         port = 5000;  // 监听端口
    bool        cors = false; // 是否启用 CORS

    // HTTPS
    bool        https_enabled = false;
    std::string https_cert;
    std::string https_key;
};

static std::string executable_dir() {
    char buf[4096];
    ssize_t n = ::readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (n <= 0) return ".";
    buf[n] = '\0';
    return fs::path(buf).parent_path().string();
}

static std::string default_config_path() {
    return (fs::path(executable_dir()) / "status_server.ini").string();
}

static Config load_config(const std::string& ini_path) {
    IniFile ini;
    if (!ini.load(ini_path)) {
        throw std::runtime_error("无法读取配置文件: " + ini_path);
    }

    Config c;
    c.bind       = ini.get("server",  "bind", "127.0.0.1");
    c.port       = ini.get_int("server", "port", 5000);
    c.cors       = ini.get_bool("server", "cors", false);

    c.file       = ini.get("storage", "status_file", "");
    c.token_file = ini.get("storage", "token_file", "");
    if (c.token_file.empty())
        c.token_file = (fs::path(executable_dir()) / ".api_token").string();

    c.api_key    = ini.get("auth",    "api_key", "");

    c.https_enabled = ini.get_bool("https", "enabled", false);
    c.https_cert    = ini.get("https", "cert_file", "");
    c.https_key     = ini.get("https", "key_file",  "");

    return c;
}

static void validate_config(const Config& c) {
    if (c.bind.empty())
        throw std::runtime_error("配置项 server.bind 不能为空");
    if (c.port <= 0 || c.port > 65535)
        throw std::runtime_error("配置项 server.port 必须在 1..65535 之间");
    if (c.file.empty())
        throw std::runtime_error("配置项 storage.status_file 不能为空");

    if (c.https_enabled) {
        if (c.https_cert.empty())
            throw std::runtime_error("启用 HTTPS 时必须配置 https.cert_file");
        if (c.https_key.empty())
            throw std::runtime_error("启用 HTTPS 时必须配置 https.key_file");
        if (!fs::exists(c.https_cert))
            throw std::runtime_error("HTTPS 证书文件不存在: " + c.https_cert);
        if (!fs::exists(c.https_key))
            throw std::runtime_error("HTTPS 私钥文件不存在: " + c.https_key);
    }
}

static void write_config_template(const std::string& path) {
    fs::path p(path);
    if (!p.parent_path().empty()) {
        std::error_code ec;
        fs::create_directories(p.parent_path(), ec);
    }

    std::ofstream f(path, std::ios::trunc);
    if (!f) {
        throw std::runtime_error("无法创建配置文件: " + path);
    }
    f << R"(# status_server 配置文件
# 修改后重新运行程序。
# 字段说明见下方注释；如需 HTTPS，把 [https] enabled 设为 true。

[server]
# 监听地址（0.0.0.0 表示所有网卡）
bind = 127.0.0.1
# 监听端口
port = 5000
# 是否启用 CORS（true / false）
cors = false

[https]
# 是否启用 HTTPS（true / false）
enabled = false
# 证书文件路径（PEM 格式，包含证书链）
cert_file =
# 私钥文件路径（PEM 格式）
key_file =

[storage]
# status.json 的绝对路径（必须与 nginx root 一致）
status_file = 
# API Token 文件位置（首次运行会自动生成）
token_file = 

[auth]
# 可选的静态 API Key，留空则只使用 token_file 中的 token
api_key =
)";
    f.close();
}

// ============================ 常量 ============================
static const std::vector<std::string> VALID_STATUS = {
    "online", "away", "busy", "offline"
};

static json make_default() {
    return json{
        {"name",           "未命名"},
        {"status",         "offline"},
        {"status_text",    "离线"},
        {"program_name",   ""},
        {"program_title",  ""},
        {"since",          nullptr},
        {"server_updated", nullptr}
    };
}

// ============================ 错误 ============================
class ApiError : public std::runtime_error {
public:
    int code;
    ApiError(const std::string& msg, int c = 400)
        : std::runtime_error(msg), code(c) {}
};

// ============================ 时间 ============================
static std::string now_iso() {
    std::time_t t = std::time(nullptr);
    std::tm tm{};
    localtime_r(&t, &tm);
    char buf[64];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S%z", &tm);
    std::string s(buf);
    if (s.size() >= 5) s.insert(s.size() - 2, ":");
    return s;
}

static bool valid_iso(const std::string& s) {
    static const std::regex re(
        R"(^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?$)");
    return std::regex_match(s, re);
}

static std::string normalize_iso(const std::string& s) {
    if (!s.empty() && (s.back() == 'Z' || s.back() == 'z')) {
        return s.substr(0, s.size() - 1) + "+00:00";
    }
    return s;
}

// ============================ 字符串校验 ============================
static std::string clean_str(const json& value, size_t maxlen,
                             const std::string& field, bool allow_empty = true) {
    if (value.is_null()) {
        if (!allow_empty) throw ApiError(field + " 不能为空");
        return "";
    }
    if (!value.is_string())
        throw ApiError(field + " 必须是字符串");
    std::string s = trim(value.get<std::string>());
    if (!allow_empty && s.empty())
        throw ApiError(field + " 不能为空");
    if (utf8_len(s) > maxlen)
        throw ApiError(field + " 过长（最多 " + std::to_string(maxlen) + " 字符）");
    return s;
}

// ============================ Token ============================
static std::string base64url(const unsigned char* data, size_t len) {
    static const char tbl[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    std::string out;
    out.reserve((len * 4 + 2) / 3);
    for (size_t i = 0; i < len; i += 3) {
        uint32_t v = (uint32_t)data[i] << 16;
        size_t rem = len - i;
        if (rem > 1) v |= (uint32_t)data[i + 1] << 8;
        if (rem > 2) v |= (uint32_t)data[i + 2];
        out.push_back(tbl[(v >> 18) & 0x3F]);
        out.push_back(tbl[(v >> 12) & 0x3F]);
        if (rem > 1) out.push_back(tbl[(v >> 6) & 0x3F]);
        if (rem > 2) out.push_back(tbl[v & 0x3F]);
    }
    return out;
}

static std::string gen_token() {
    unsigned char buf[32];
    std::ifstream f("/dev/urandom", std::ios::binary);
    if (!f) throw std::runtime_error("无法打开 /dev/urandom");
    f.read(reinterpret_cast<char*>(buf), sizeof(buf));
    if (f.gcount() != (std::streamsize)sizeof(buf))
        throw std::runtime_error("读取 /dev/urandom 失败");
    return base64url(buf, sizeof(buf));
}

// ============================ 原子写文件 ============================
static void atomic_write(const std::string& path, const std::string& content,
                         mode_t mode) {
    fs::path p(path);
    fs::path dir = p.parent_path();
    if (!dir.empty()) {
        std::error_code ec;
        fs::create_directories(dir, ec);
    }
    std::string d = dir.empty() ? "." : dir.string();

    std::string tmpl = d + "/.tmp-XXXXXX";
    std::vector<char> buf(tmpl.begin(), tmpl.end());
    buf.push_back('\0');

    int fd = ::mkstemp(buf.data());
    if (fd < 0)
        throw std::runtime_error("mkstemp 失败: " +
                                 std::string(std::strerror(errno)));
    std::string tmp_path(buf.data());

    try {
        size_t w = 0;
        while (w < content.size()) {
            ssize_t n = ::write(fd, content.data() + w, content.size() - w);
            if (n < 0) {
                if (errno == EINTR) continue;
                throw std::runtime_error("写入失败: " +
                                         std::string(std::strerror(errno)));
            }
            w += (size_t)n;
        }
        ::fchmod(fd, mode);
        ::fsync(fd);
        ::close(fd);
        fd = -1;
        if (::rename(tmp_path.c_str(), path.c_str()) != 0)
            throw std::runtime_error("rename 失败: " +
                                     std::string(std::strerror(errno)));
    } catch (...) {
        if (fd >= 0) ::close(fd);
        ::unlink(tmp_path.c_str());
        throw;
    }
}

// ============================ 文件锁 ============================
class FileLock {
public:
    explicit FileLock(const std::string& path) {
        fd_ = ::open(path.c_str(), O_RDWR | O_CREAT, 0644);
        if (fd_ < 0) throw std::runtime_error("无法打开锁文件: " + path);
        if (flock(fd_, LOCK_EX) != 0) {
            ::close(fd_);
            fd_ = -1;
            throw std::runtime_error("flock 失败: " + path);
        }
    }
    ~FileLock() {
        if (fd_ >= 0) { flock(fd_, LOCK_UN); ::close(fd_); }
    }
    FileLock(const FileLock&)            = delete;
    FileLock& operator=(const FileLock&) = delete;
private:
    int fd_ = -1;
};

// ============================ 读写 status ============================
static json read_status(const std::string& path) {
    try {
        std::ifstream f(path);
        if (!f) return make_default();
        json j;
        f >> j;
        if (!j.is_object()) return make_default();
        return j;
    } catch (...) {
        return make_default();
    }
}

static std::string load_or_create_token(const std::string& path) {
    fs::path p(path);
    fs::path dir = p.parent_path();
    if (!dir.empty()) {
        std::error_code ec;
        fs::create_directories(dir, ec);
    }
    {
        std::ifstream in(path);
        if (in) {
            std::string tok;
            std::getline(in, tok);
            tok = trim(tok);
            if (!tok.empty()) return tok;
        }
    }
    std::string tok = gen_token();
    atomic_write(path, tok + "\n", 0600);
    return tok;
}

// ============================ 鉴权 ============================
static bool constant_time_eq(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return false;
    unsigned char r = 0;
    for (size_t i = 0; i < a.size(); ++i)
        r |= (unsigned char)a[i] ^ (unsigned char)b[i];
    return r == 0;
}

static std::string get_supplied_token(const httplib::Request& req) {
    if (req.has_header("X-API-Key")) {
        std::string v = req.get_header_value("X-API-Key");
        if (!v.empty()) return v;
    }
    if (req.has_header("Authorization")) {
        std::string v = req.get_header_value("Authorization");
        if (v.size() > 7 && to_lower(v.substr(0, 7)) == "bearer ")
            return v.substr(7);
    }
    if (req.has_param("key")) {
        std::string v = req.get_param_value("key");
        if (!v.empty()) return v;
    }
    return "";
}

static void require_key(const httplib::Request& req, const Config& cfg,
                        const std::string& api_token) {
    std::string supplied = get_supplied_token(req);
    if (supplied.empty()) throw ApiError("你干嘛，哎害哟~", 401);

    bool ok = false;
    if (!cfg.api_key.empty() && constant_time_eq(supplied, cfg.api_key)) ok = true;
    if (!ok && !api_token.empty() && constant_time_eq(supplied, api_token)) ok = true;
    if (!ok) throw ApiError("你干嘛，哎害哟~", 401);
}

// ============================ 响应工具 ============================
static void send_json(httplib::Response& res, const json& j, int status = 200) {
    res.status = status;
    res.set_content(j.dump(), "application/json; charset=utf-8");
}

static void send_error(httplib::Response& res, const std::string& msg, int status) {
    json j = {{"ok", false}, {"error", msg}};
    send_json(res, j, status);
}

// ============================ POST 处理 ============================
static void handle_post_status(const httplib::Request& req,
                               httplib::Response& res,
                               const Config& cfg,
                               const std::string& api_token) {
    try {
        require_key(req, cfg, api_token);

        json body;
        try {
            body = json::parse(req.body);
        } catch (...) {
            throw ApiError("请求体必须是 JSON 对象，且 Content-Type: application/json");
        }
        if (!body.is_object())
            throw ApiError("请求体必须是 JSON 对象，且 Content-Type: application/json");

        json data = make_default();

        if (body.contains("name"))
            data["name"] = clean_str(body["name"], 32, "name", false);

        if (body.contains("status")) {
            std::string s = to_lower(clean_str(body["status"], 16, "status"));
            bool ok = false;
            for (const auto& v : VALID_STATUS) if (v == s) { ok = true; break; }
            if (!ok)
                throw ApiError("status 只能是 away / busy / offline / online");
            data["status"] = s;
        }
        if (body.contains("status_text"))
            data["status_text"] = clean_str(body["status_text"], 32, "status_text");
        if (body.contains("program_name"))
            data["program_name"] = clean_str(body["program_name"], 64, "program_name");
        if (body.contains("program_title"))
            data["program_title"] = clean_str(body["program_title"], 64, "program_title");

        data["since"] = now_iso();
        if (body.contains("since")) {
            const auto& v = body["since"];
            if (v.is_string()) {
                std::string s = v.get<std::string>();
                if (!s.empty()) {
                    if (!valid_iso(s))
                        throw ApiError("since 不是合法的 ISO 时间：" + s);
                    data["since"] = normalize_iso(s);
                }
            } else if (!v.is_null()) {
                bool falsy = (v.is_number() && v.get<double>() == 0.0) ||
                             (v.is_boolean() && !v.get<bool>());
                if (!falsy)
                    throw ApiError("since 必须是 ISO 时间字符串，如 2026-10-02T12:00:00+08:00");
            }
        }

        {
            FileLock lock(cfg.file + ".lock");
            data["server_updated"] = now_iso();
            atomic_write(cfg.file, data.dump(2) + "\n", 0644);
        }

        json resp = {{"ok", true}, {"status", data}};
        send_json(res, resp, 200);
    } catch (const ApiError& e) {
        send_error(res, e.what(), e.code);
    } catch (const std::exception& e) {
        send_error(res, std::string("服务器错误：") + e.what(), 500);
    }
}

// ============================ 命令行 ============================
static void print_usage(const char* prog) {
    std::cout <<
        "用法: " << prog << " [选项]\n"
        "\n"
        "选项:\n"
        "  -c, --config <path>   指定 INI 配置文件路径\n"
        "                        默认: <可执行文件目录>/status_server.ini\n"
        "      --init            仅生成配置模板（若不存在）后退出\n"
        "  -h, --help            显示本帮助\n";
}

// ============================ main ============================
int main(int argc, char** argv) {
    std::string config_path;
    bool init_only = false;

    try {
        for (int i = 1; i < argc; ++i) {
            std::string a = argv[i];
            if ((a == "-c" || a == "--config") && i + 1 < argc) {
                config_path = argv[++i];
            } else if (a == "--init") {
                init_only = true;
            } else if (a == "-h" || a == "--help") {
                print_usage(argv[0]);
                return 0;
            } else {
                std::cerr << "[status-server] 未知参数: " << a << "\n";
                print_usage(argv[0]);
                return 2;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[status-server] 参数解析失败: " << e.what() << "\n";
        return 2;
    }

    if (config_path.empty()) config_path = default_config_path();

    // ---- 配置文件缺失 => 生成模板 + 退出，要求用户配置 ----
    if (!fs::exists(config_path)) {
        try {
            write_config_template(config_path);
        } catch (const std::exception& e) {
            std::cerr << "[status-api] 生成配置模板失败: " << e.what() << "\n";
            return 1;
        }
        std::cerr << "[status-api] 未找到配置文件，已生成模板：\n"
                  << "             " << config_path << "\n"
                  << "[status-api] 请编辑该文件（尤其是 [storage] 和 [server] 段）后重新运行。\n";
        return 1;
    }

    if (init_only) {
        std::cout << "[status-server] 配置文件已存在: " << config_path << "\n";
        return 0;
    }

    // ---- 加载 + 校验配置 ----
    Config cfg;
    try {
        cfg = load_config(config_path);
        validate_config(cfg);
    } catch (const std::exception& e) {
        std::cerr << "[status-server] 配置错误: " << e.what() << "\n"
                  << "[status-server] 请编辑配置文件后重新运行: " << config_path << "\n";
        return 1;
    }

    // ---- 启动 ----
    try {
        std::string api_token = load_or_create_token(cfg.token_file);

        std::cout << "[status-server] 配置文件: " << config_path << "\n";
        std::cout << "[status-server] 写入文件: " << cfg.file << "\n";
        std::cout << "[status-server] 协议: "
                  << (cfg.https_enabled ? "HTTPS" : "HTTP") << "\n";
        std::cout << "[status-server] 监听: " << cfg.bind << ":" << cfg.port << "\n";
        std::cout << "[status-server] Token 文件: " << cfg.token_file << "\n";
        std::cout << "[status-server] Token 预览: "
                  << api_token.substr(0, std::min<size_t>(8, api_token.size()))
                  << "…（完整值请查看 token 文件）\n";
        std::cout.flush();

        // ---- 创建 Server（HTTP 或 HTTPS）----
        std::unique_ptr<httplib::Server> svr;
        if (cfg.https_enabled) {
#ifdef CPPHTTPLIB_OPENSSL_SUPPORT
            auto ssl = std::make_unique<httplib::SSLServer>(
                cfg.https_cert.c_str(), cfg.https_key.c_str());
            if (!ssl->is_valid()) {
                std::cerr << "[status-server] SSL 初始化失败，请检查证书/私钥文件：\n"
                          << "              cert: " << cfg.https_cert << "\n"
                          << "              key : " << cfg.https_key  << "\n";
                return 1;
            }
            svr = std::move(ssl);
            std::cout << "[status-server] TLS 证书: " << cfg.https_cert << "\n";
#else
            std::cerr << "[status-server] 当前可执行文件未包含 OpenSSL 支持，无法启用 HTTPS。\n"
                      << "[status-server] 请使用 -DCPPHTTPLIB_OPENSSL_SUPPORT -lssl -lcrypto 重新编译，\n"
                      << "[status-server] 或把 [https] enabled 改为 false。\n";
            return 1;
#endif
        } else {
            svr = std::make_unique<httplib::Server>();
        }

        svr->set_payload_max_length(64 * 1024);   // 请求体上限 64KB

        // -------- CORS --------
        if (cfg.cors) {
            svr->set_default_headers({
                {"Access-Control-Allow-Origin",  "*"},
                {"Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization"},
                {"Access-Control-Allow-Methods", "GET, POST, OPTIONS"}
            });
        }

        // -------- 错误处理 --------
        svr->set_error_handler([](const httplib::Request&, httplib::Response& res) {
            if (res.status == 404) {
                res.set_content(R"({"ok":false,"error":"接口不存在"})",
                                "application/json; charset=utf-8");
            } else if (res.status == 413) {
                res.set_content(R"({"ok":false,"error":"请求体过大"})",
                                "application/json; charset=utf-8");
            }
        });

        // -------- 预检 --------
        svr->Options(R"(/api/.*)", [](const httplib::Request&, httplib::Response& res) {
            res.status = 204;
        });

        // -------- GET /api/status --------
        svr->Get("/api/status", [&cfg](const httplib::Request&, httplib::Response& res) {
            json j = {{"ok", true}, {"status", read_status(cfg.file)}};
            send_json(res, j);
        });

        // -------- POST /api/status --------
        svr->Post("/api/status",
                  [&cfg, &api_token](const httplib::Request& req, httplib::Response& res) {
                      handle_post_status(req, res, cfg, api_token);
                  });

        // -------- GET /api/health --------
        svr->Get("/api/health", [](const httplib::Request&, httplib::Response& res) {
            json j = {{"ok", true}, {"time", now_iso()}};
            send_json(res, j);
        });

        if (!svr->listen(cfg.bind.c_str(), cfg.port)) {
            std::cerr << "[status-server] 监听失败：" << cfg.bind << ":" << cfg.port << "\n";
            return 1;
        }
        } catch (const std::exception& e) {
        std::cerr << "[status-server] 启动失败: " << e.what() << "\n";
        return 1;
    }
    return 0;
}