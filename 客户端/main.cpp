// status-client.cpp — 个人状态 API 客户端
//
// 编译（MinGW-w64）：
//   g++ -std=c++17 -O2 -o main.exe main.cpp -lwinhttp -lshell32
//
// 用法：
//   status-client.exe                      # 按 client.ini 推送状态
//   status-client.exe --status busy        # 临时覆盖状态
//   status-client.exe --get                # 查询当前状态
//   status-client.exe --health             # 健康检查
//   status-client.exe -c D:\x\my.ini       # 指定配置文件
//
// 退出码：0 成功 / 1 请求或接口失败 / 2 参数错误

#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#endif
#ifndef WINVER
#define WINVER 0x0600
#endif

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <shellapi.h>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

// ============================ 编码工具 ============================

static std::string wide_to_utf8(const std::wstring& w) {
    if (w.empty()) return std::string();
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(),
                                nullptr, 0, nullptr, nullptr);
    if (n <= 0) return std::string();
    std::string s((size_t)n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(),
                        &s[0], n, nullptr, nullptr);
    return s;
}

static std::wstring utf8_to_wide(const std::string& s) {
    if (s.empty()) return std::wstring();
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    if (n <= 0) return std::wstring();
    std::wstring w((size_t)n, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), &w[0], n);
    return w;
}

// UTF-8 -> 当前 ANSI 代码页（用于 std::fstream 打开本地路径）
static std::string utf8_to_ansi(const std::string& s) {
    if (s.empty()) return std::string();
    std::wstring w = utf8_to_wide(s);
    if (w.empty()) return s;
    int n = WideCharToMultiByte(CP_ACP, 0, w.c_str(), (int)w.size(),
                                nullptr, 0, nullptr, nullptr);
    if (n <= 0) return s;
    std::string out((size_t)n, '\0');
    WideCharToMultiByte(CP_ACP, 0, w.c_str(), (int)w.size(),
                        &out[0], n, nullptr, nullptr);
    return out;
}

static void append_utf8(std::string& out, unsigned cp) {
    if (cp < 0x80) {
        out += (char)cp;
    } else if (cp < 0x800) {
        out += (char)(0xC0 | (cp >> 6));
        out += (char)(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        out += (char)(0xE0 | (cp >> 12));
        out += (char)(0x80 | ((cp >> 6) & 0x3F));
        out += (char)(0x80 | (cp & 0x3F));
    } else {
        out += (char)(0xF0 | (cp >> 18));
        out += (char)(0x80 | ((cp >> 12) & 0x3F));
        out += (char)(0x80 | ((cp >> 6) & 0x3F));
        out += (char)(0x80 | (cp & 0x3F));
    }
}

// ============================ 小工具 ============================

static std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && (unsigned char)s[a] <= ' ') ++a;
    while (b > a && (unsigned char)s[b - 1] <= ' ') --b;
    return s.substr(a, b - a);
}

static std::string to_lower(std::string s) {
    for (char& c : s) c = (char)std::tolower((unsigned char)c);
    return s;
}

static std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 8);
    for (unsigned char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += (char)c;
                }
        }
    }
    return out;
}

static std::string json_string(const std::string& s) {
    return "\"" + json_escape(s) + "\"";
}

// 从 JSON 里抠出某个 key 的字符串值（跳过对象/数组值）
static bool json_extract(const std::string& s, const std::string& key, std::string& out) {
    const std::string pat = "\"" + key + "\"";
    size_t pos = 0;
    while ((pos = s.find(pat, pos)) != std::string::npos) {
        size_t p = pos + pat.size();
        while (p < s.size() && (unsigned char)s[p] <= ' ') ++p;
        if (p < s.size() && s[p] == ':') {
            ++p;
            while (p < s.size() && (unsigned char)s[p] <= ' ') ++p;
            if (p < s.size() && s[p] == '"') {
                ++p;
                std::string v;
                bool closed = false;
                while (p < s.size()) {
                    char c = s[p];
                    if (c == '\\' && p + 1 < s.size()) {
                        char n = s[p + 1];
                        switch (n) {
                            case 'n':  v += '\n'; break;
                            case 't':  v += '\t'; break;
                            case 'r':  v += '\r'; break;
                            case 'b':  v += '\b'; break;
                            case 'f':  v += '\f'; break;
                            case '"':  v += '"';  break;
                            case '\\': v += '\\'; break;
                            case '/':  v += '/';  break;
                            case 'u': {
                                if (p + 5 < s.size()) {
                                    unsigned cp = 0;
                                    for (int i = 0; i < 4; ++i) {
                                        char h = s[p + 2 + i];
                                        cp <<= 4;
                                        if (h >= '0' && h <= '9')      cp |= (unsigned)(h - '0');
                                        else if (h >= 'a' && h <= 'f') cp |= (unsigned)(h - 'a' + 10);
                                        else if (h >= 'A' && h <= 'F') cp |= (unsigned)(h - 'A' + 10);
                                    }
                                    append_utf8(v, cp);
                                    p += 4;
                                }
                                break;
                            }
                            default: v += n; break;
                        }
                        p += 2;
                    } else if (c == '"') {
                        ++p;
                        closed = true;
                        break;
                    } else {
                        v += c;
                        ++p;
                    }
                }
                if (closed) { out = v; return true; }
            }
        }
        pos += pat.size();
    }
    return false;
}

// ============================ INI 解析 ============================

class Ini {
public:
    // 返回 false 表示文件打不开；解析过程中的小问题会被忽略
    bool load(const std::string& path, std::string& err) {
        std::ifstream f(utf8_to_ansi(path), std::ios::binary);
        if (!f) {
            err = "无法打开配置文件: " + path;
            return false;
        }
        std::stringstream ss;
        ss << f.rdbuf();
        std::string content = ss.str();

        // 去掉 UTF-8 BOM
        if (content.size() >= 3 &&
            (unsigned char)content[0] == 0xEF &&
            (unsigned char)content[1] == 0xBB &&
            (unsigned char)content[2] == 0xBF) {
            content.erase(0, 3);
        }

        std::string section;
        std::istringstream is(content);
        std::string line;
        int lineno = 0;
        while (std::getline(is, line)) {
            ++lineno;
            if (!line.empty() && line.back() == '\r') line.pop_back();
            std::string t = trim(line);
            if (t.empty() || t[0] == ';' || t[0] == '#') continue;

            if (t[0] == '[') {
                size_t e = t.find(']');
                if (e == std::string::npos) continue;
                section = to_lower(trim(t.substr(1, e - 1)));
                continue;
            }

            size_t eq = t.find('=');
            if (eq == std::string::npos) continue;

            std::string key = to_lower(trim(t.substr(0, eq)));
            std::string val = trim(t.substr(eq + 1));

            // 去掉值的行内注释（前面必须有空白，避免误伤 URL/Token）
            for (size_t i = 0; i + 1 < val.size(); ++i) {
                if ((val[i] == ';' || val[i] == '#') &&
                    (unsigned char)val[i - 1] <= ' ') {
                    val = trim(val.substr(0, i));
                    break;
                }
            }

            if (!key.empty()) data_[section][key] = val;
        }
        return true;
    }

    std::string get(const std::string& sec, const std::string& key,
                    const std::string& def = std::string()) const {
        auto s = data_.find(to_lower(sec));
        if (s == data_.end()) return def;
        auto k = s->second.find(to_lower(key));
        if (k == s->second.end()) return def;
        return k->second;
    }

    int get_int(const std::string& sec, const std::string& key, int def) const {
        std::string v = get(sec, key);
        if (v.empty()) return def;
        try { return std::stoi(v); } catch (...) { return def; }
    }

    bool get_bool(const std::string& sec, const std::string& key, bool def) const {
        std::string v = to_lower(trim(get(sec, key)));
        if (v.empty()) return def;
        return v == "1" || v == "true" || v == "yes" || v == "on";
    }

private:
    std::map<std::string, std::map<std::string, std::string>> data_;
};

// ============================ HTTP (WinHTTP) ============================

struct HttpResult {
    bool        ok = false;
    DWORD       status = 0;
    std::string body;
    std::string error;
};

class WinHttpHandle {
public:
    WinHttpHandle() = default;
    explicit WinHttpHandle(HINTERNET h) : h_(h) {}
    ~WinHttpHandle() { if (h_) WinHttpCloseHandle(h_); }
    WinHttpHandle(const WinHttpHandle&) = delete;
    WinHttpHandle& operator=(const WinHttpHandle&) = delete;

    operator HINTERNET() const { return h_; }
    explicit operator bool() const { return h_ != nullptr; }

private:
    HINTERNET h_ = nullptr;
};

static HttpResult http_request(const std::wstring& method,
                               const std::wstring& url,
                               const std::string& body,
                               const std::vector<std::wstring>& headers,
                               int timeout_ms) {
    HttpResult res;

    URL_COMPONENTS uc;
    ZeroMemory(&uc, sizeof(uc));
    uc.dwStructSize = sizeof(uc);

    wchar_t host[256]  = {0};
    wchar_t path[4096] = {0};
    wchar_t extra[4096] = {0};

    uc.lpszHostName     = host;  uc.dwHostNameLength  = (DWORD)(sizeof(host) / sizeof(host[0]));
    uc.lpszUrlPath      = path;  uc.dwUrlPathLength   = (DWORD)(sizeof(path) / sizeof(path[0]));
    uc.lpszExtraInfo    = extra; uc.dwExtraInfoLength = (DWORD)(sizeof(extra) / sizeof(extra[0]));

    if (!WinHttpCrackUrl(url.c_str(), (DWORD)url.size(), 0, &uc)) {
        res.error = "URL 解析失败 (err=" + std::to_string(GetLastError()) + "): " + wide_to_utf8(url);
        return res;
    }

    std::wstring fullPath(path, uc.dwUrlPathLength);
    fullPath.append(extra, uc.dwExtraInfoLength);
    if (fullPath.empty()) fullPath = L"/";

    WinHttpHandle hSession(WinHttpOpen(L"StatusClient/1.0",
                                       WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                       WINHTTP_NO_PROXY_NAME,
                                       WINHTTP_NO_PROXY_BYPASS, 0));
    if (!hSession) {
        res.error = "WinHttpOpen 失败 (err=" + std::to_string(GetLastError()) + ")";
        return res;
    }

    int t = timeout_ms > 0 ? timeout_ms : 5000;
    WinHttpSetTimeouts(hSession, t, t, t, t);

    WinHttpHandle hConnect(WinHttpConnect(hSession, host, (INTERNET_PORT)uc.nPort, 0));
    if (!hConnect) {
        res.error = "无法连接到 " + wide_to_utf8(host) + ":" + std::to_string(uc.nPort) +
                    " (err=" + std::to_string(GetLastError()) + ")";
        return res;
    }

    DWORD flags = (uc.nScheme == INTERNET_SCHEME_HTTPS) ? WINHTTP_FLAG_SECURE : 0;
    WinHttpHandle hRequest(WinHttpOpenRequest(hConnect, method.c_str(), fullPath.c_str(),
                                              nullptr, WINHTTP_NO_REFERER,
                                              WINHTTP_DEFAULT_ACCEPT_TYPES, flags));
    if (!hRequest) {
        res.error = "WinHttpOpenRequest 失败 (err=" + std::to_string(GetLastError()) + ")";
        return res;
    }

    for (const std::wstring& h : headers) {
        WinHttpAddRequestHeaders(hRequest, h.c_str(), (DWORD)-1L,
                                 WINHTTP_ADDREQ_FLAG_ADD | WINHTTP_ADDREQ_FLAG_REPLACE);
    }

    BOOL sent = WinHttpSendRequest(
        hRequest,
        WINHTTP_NO_ADDITIONAL_HEADERS, 0,
        body.empty() ? WINHTTP_NO_REQUEST_DATA : (LPVOID)body.data(),
        (DWORD)body.size(), (DWORD)body.size(), 0);

    if (!sent) {
        res.error = "发送请求失败 (err=" + std::to_string(GetLastError()) + ")";
        return res;
    }

    if (!WinHttpReceiveResponse(hRequest, nullptr)) {
        res.error = "接收响应失败 (err=" + std::to_string(GetLastError()) + ")";
        return res;
    }

    DWORD code = 0, len = sizeof(code);
    WinHttpQueryHeaders(hRequest,
                        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                        WINHTTP_HEADER_NAME_BY_INDEX, &code, &len,
                        WINHTTP_NO_HEADER_INDEX);
    res.status = code;

    std::string respBody;
    for (;;) {
        DWORD avail = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &avail)) break;
        if (avail == 0) break;
        std::vector<char> buf(avail);
        DWORD read = 0;
        if (!WinHttpReadData(hRequest, buf.data(), avail, &read)) break;
        if (read == 0) break;
        respBody.append(buf.data(), read);
    }

    res.body = std::move(respBody);
    res.ok = true;
    return res;
}

// ============================ Windows 环境探测 ============================

static std::string get_foreground_process_name() {
    HWND hwnd = GetForegroundWindow();
    if (!hwnd) return std::string();

    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (!pid) return std::string();

    HANDLE h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!h) return std::string();

    wchar_t buf[MAX_PATH * 4] = {0};
    DWORD sz = (DWORD)(sizeof(buf) / sizeof(buf[0]));
    std::string result;

    if (QueryFullProcessImageNameW(h, 0, buf, &sz)) {
        std::wstring full(buf, sz);
        size_t pos = full.find_last_of(L"\\/");
        std::wstring base = (pos == std::wstring::npos) ? full : full.substr(pos + 1);
        if (base.size() > 4) {
            std::wstring ext = base.substr(base.size() - 4);
            for (wchar_t& c : ext) c = (wchar_t)towlower(c);
            if (ext == L".exe") base = base.substr(0, base.size() - 4);
        }
        result = wide_to_utf8(base);
    }
    CloseHandle(h);
    return result;
}

static DWORD get_idle_seconds() {
    LASTINPUTINFO lii;
    ZeroMemory(&lii, sizeof(lii));
    lii.cbSize = sizeof(lii);
    if (!GetLastInputInfo(&lii)) return 0;
    DWORD now = GetTickCount();
    return (now - lii.dwTime) / 1000;
}

static std::string local_iso8601() {
    SYSTEMTIME st;
    GetLocalTime(&st);

    TIME_ZONE_INFORMATION tz;
    ZeroMemory(&tz, sizeof(tz));
    DWORD r = GetTimeZoneInformation(&tz);
    int offset_min = -(int)tz.Bias;
    if (r == TIME_ZONE_ID_DAYLIGHT)      offset_min -= (int)tz.DaylightBias;
    else if (r == TIME_ZONE_ID_STANDARD) offset_min -= (int)tz.StandardBias;

    char sign = offset_min >= 0 ? '+' : '-';
    int ao = offset_min < 0 ? -offset_min : offset_min;

    char buf[64];
    std::snprintf(buf, sizeof(buf),
                  "%04d-%02d-%02dT%02d:%02d:%02d%c%02d:%02d",
                  st.wYear, st.wMonth, st.wDay,
                  st.wHour, st.wMinute, st.wSecond,
                  sign, ao / 60, ao % 60);
    return std::string(buf);
}

// ============================ 配置结构 ============================

struct Config {
    std::string url        = "http://127.0.0.1:5000/api/status";
    std::string healthUrl;      // 留空则自动推导
    std::string apiKey;
    std::string tokenFile;      // 留空则用 exe 同目录 .api_token
    int         timeoutMs  = 5000;

    std::string name;
    std::string status     = "online";
    std::string statusText;
    std::string programName;
    std::string since;

    bool detectProgram = false;
    bool detectStatus  = false;
    int  idleMinutes   = 10;
};

static std::string default_status_text(const std::string& s) {
    if (s == "online")  return "在线";
    if (s == "away")    return "离开";
    if (s == "busy")    return "忙碌";
    if (s == "offline") return "离线";
    return std::string();
}

static std::string derive_health_url(const std::string& url) {
    size_t q = url.find('?');
    std::string base  = (q == std::string::npos) ? url : url.substr(0, q);
    std::string query = (q == std::string::npos) ? std::string() : url.substr(q);

    size_t slash = base.rfind('/');
    if (slash == std::string::npos) return base + "/api/health" + query;

    std::string path = base.substr(slash);
    if (path == "/api/status")
        return base.substr(0, slash) + "/api/health" + query;
    return base + "/health" + query;
}

static bool read_token_file(const std::string& path, std::string& out) {
    std::ifstream f(utf8_to_ansi(path), std::ios::binary);
    if (!f) return false;
    std::string s;
    std::getline(f, s);
    s = trim(s);
    if (s.empty()) return false;
    out = s;
    return true;
}

// ============================ 自动生成 INI 模板 ============================

static bool write_default_ini(const std::string& path, std::string& err) {
    std::ofstream f(utf8_to_ansi(path), std::ios::binary | std::ios::trunc);
    if (!f) {
        err = "无法创建配置文件: " + path;
        return false;
    }

    // UTF-8 BOM，让记事本正确识别中文编码
    f.write("\xEF\xBB\xBF", 3);

    f <<
        "; ============================================================\n"
        "; status-client 配置文件\n"
        "; 首次运行由程序自动生成，请按需修改后保存\n"
        "; 编码: UTF-8（带 BOM）\n"
        "; ============================================================\n"
        "\n"
        "[server]\n"
        "; 状态接口地址（必填）\n"
        "url = http://127.0.0.1:5000/api/status\n"
        "\n"
        "; 健康检查地址，留空则根据 url 自动推导\n"
        "health_url =\n"
        "\n"
        "; API Key（必填）；留空则尝试读取同目录 .api_token\n"
        "api_key =\n"
        "\n"
        "; API Key 文件路径；留空使用 exe 同目录 .api_token\n"
        "token_file =\n"
        "\n"
        "; 请求超时（毫秒）\n"
        "timeout_ms = 5000\n"
        "\n"
        "[status]\n"
        "; 你的名称（必填，用于服务端识别身份）\n"
        "name =\n"
        "\n"
        "; 状态: online / away / busy / offline\n"
        "status = online\n"
        "\n"
        "; 状态文案；留空则按状态自动填「在线 / 离开 / 忙碌 / 离线」\n"
        "status_text =\n"
        "\n"
        "; 当前程序名；可选，会被 --program 或自动探测覆盖\n"
        "program_name =\n"
        "\n"
        "; 状态开始时间（ISO8601，或写 now 表示当前时刻）；可留空\n"
        "since =\n"
        "\n"
        "[auto]\n"
        "; 是否自动探测前台程序名并写入 program_name\n"
        "detect_program = false\n"
        "\n"
        "; 是否根据键鼠空闲时长自动切换 away / online\n"
        "detect_status = false\n"
        "\n"
        "; 判定离开的空闲分钟数\n"
        "idle_minutes = 10\n";

    f.flush();
    return (bool)f;
}

static void print_ini_guide(const std::string& path) {
    std::cout <<
        "============================================================\n"
        "  首次运行：已生成配置文件模板\n"
        "============================================================\n"
        "\n"
        "  路径: " << path << "\n"
        "\n"
        "  请用记事本打开，至少填写以下三项：\n"
        "\n"
        "    [server] url      — 状态接口地址\n"
        "    [server] api_key  — API Key（或用同目录 .api_token）\n"
        "    [status] name     — 你的名称\n"
        "\n"
        "  填写后重新运行 status-client.exe 即可。\n"
        "\n"
        "  如果不想用配置文件，也可以临时用命令行参数：\n"
        "    status-client.exe --url <地址> --key <token> --name <名称>\n"
        "\n"
        "============================================================\n";
}

// ============================ 命令行 ============================

static void print_usage() {
    std::cout <<
        "个人状态 API 客户端\n"
        "\n"
        "用法: status-client.exe [选项]\n"
        "\n"
        "  -c, --config <文件>   指定 INI 配置文件（默认 exe 同目录 client.ini）\n"
        "      --url <地址>      覆盖接口地址\n"
        "      --key <token>     覆盖 API Key\n"
        "      --timeout <毫秒>  覆盖超时\n"
        "\n"
        "      --name <名称>     覆盖 name\n"
        "      --status <状态>   online / away / busy / offline\n"
        "      --text <文案>     覆盖 status_text\n"
        "      --program <程序>  覆盖 program_name\n"
        "      --since <时间>    覆盖 since（ISO8601，或 now）\n"
        "\n"
        "      --get             查询当前状态\n"
        "      --health          健康检查\n"
        "  -v, --verbose         输出完整响应\n"
        "  -q, --quiet           只输出错误\n"
        "  -h, --help            显示帮助\n";
}

// ============================ 主流程 ============================

int main() {
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);

    // --- 取命令行（宽字符，避免中文路径乱码） ---
    std::vector<std::string> args;
    {
        int argc = 0;
        LPWSTR* argvw = CommandLineToArgvW(GetCommandLineW(), &argc);
        if (argvw) {
            for (int i = 0; i < argc; ++i) args.push_back(wide_to_utf8(argvw[i]));
            LocalFree(argvw);
        }
    }

    std::string cfgPath;
    bool cfgExplicit = false;

    enum class Mode { Push, Get, Health };
    Mode mode = Mode::Push;

    std::map<std::string, std::string> overrides;
    bool verbose = false;
    bool quiet   = false;
    int  timeoutOverride = -1;

    try {
        for (size_t i = 1; i < args.size(); ++i) {
            const std::string& a = args[i];
            auto need = [&](const char* name) -> std::string {
                if (i + 1 >= args.size())
                    throw std::runtime_error(std::string("缺少参数值: ") + name);
                return args[++i];
            };

            if (a == "-c" || a == "--config")            { cfgPath = need("--config"); cfgExplicit = true; }
            else if (a == "--url")                       overrides["url"] = need("--url");
            else if (a == "--key")                       overrides["api_key"] = need("--key");
            else if (a == "--timeout")                   timeoutOverride = std::atoi(need("--timeout").c_str());
            else if (a == "--name")                      overrides["name"] = need("--name");
            else if (a == "--status")                    overrides["status"] = need("--status");
            else if (a == "--text" || a == "--status-text") overrides["status_text"] = need("--text");
            else if (a == "--program")                   overrides["program_name"] = need("--program");
            else if (a == "--since")                     overrides["since"] = need("--since");
            else if (a == "--get")                       mode = Mode::Get;
            else if (a == "--health")                    mode = Mode::Health;
            else if (a == "-v" || a == "--verbose")      verbose = true;
            else if (a == "-q" || a == "--quiet")        quiet = true;
            else if (a == "-h" || a == "--help")         { print_usage(); return 0; }
            else {
                std::cerr << "未知参数: " << a << "\n\n";
                print_usage();
                return 2;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 2;
    }

    // --- exe 所在目录 ---
    std::wstring exePathW(32768, L'\0');
    DWORD n = GetModuleFileNameW(nullptr, &exePathW[0], (DWORD)exePathW.size());
    exePathW.resize(n);
    std::string exePath = wide_to_utf8(exePathW);
    size_t slashPos = exePath.find_last_of("\\/");
    std::string exeDir = (slashPos == std::string::npos) ? "." : exePath.substr(0, slashPos);

        if (cfgPath.empty()) cfgPath = exeDir + "\\client.ini";

    // --- 检查配置文件是否存在；不存在则生成模板并提示用户填写 ---
    {
        std::wstring cfgPathW = utf8_to_wide(cfgPath);
        DWORD attrs = GetFileAttributesW(cfgPathW.c_str());
        bool exists = (attrs != INVALID_FILE_ATTRIBUTES) &&
                      !(attrs & FILE_ATTRIBUTE_DIRECTORY);

        if (!exists) {
            std::string werr;
            if (write_default_ini(cfgPath, werr)) {
                print_ini_guide(cfgPath);
                return 0;   // 等用户填好后重跑
            } else {
                std::cerr << "[错误] " << werr << "\n";
                std::cerr << "[提示] 将使用内置默认值继续运行\n";
            }
        }
    }

    // --- 读 INI ---
    Ini ini;
    std::string iniErr;
    bool iniOk = ini.load(cfgPath, iniErr);
    if (!iniOk) {
        if (cfgExplicit) {
            std::cerr << "[错误] " << iniErr << "\n";
            return 2;
        }
        if (!quiet) std::cerr << "[提示] 未找到 " << cfgPath << "，使用内置默认值\n";
    }

    // --- 组装配置 ---
    Config cfg;
    cfg.url        = ini.get("server", "url", cfg.url);
    cfg.healthUrl  = ini.get("server", "health_url");
    cfg.apiKey     = ini.get("server", "api_key");
    cfg.tokenFile  = ini.get("server", "token_file");
    cfg.timeoutMs  = ini.get_int("server", "timeout_ms", cfg.timeoutMs);

    cfg.name        = ini.get("status", "name");
    cfg.status      = ini.get("status", "status", "online");
    cfg.statusText  = ini.get("status", "status_text");
    cfg.programName = ini.get("status", "program_name");
    cfg.since       = ini.get("status", "since");

    cfg.detectProgram = ini.get_bool("auto", "detect_program", false);
    cfg.detectStatus  = ini.get_bool("auto", "detect_status", false);
    cfg.idleMinutes   = ini.get_int("auto", "idle_minutes", 10);

    // 命令行覆盖
    auto applyOverride = [&](const char* key, std::string& target) {
        auto it = overrides.find(key);
        if (it != overrides.end()) target = it->second;
    };
    applyOverride("url", cfg.url);
    applyOverride("api_key", cfg.apiKey);
    applyOverride("name", cfg.name);
    applyOverride("status", cfg.status);
    applyOverride("status_text", cfg.statusText);
    applyOverride("program_name", cfg.programName);
    applyOverride("since", cfg.since);
    if (timeoutOverride > 0) cfg.timeoutMs = timeoutOverride;

    // --- API Key 兜底：读 .api_token ---
    if (cfg.apiKey.empty()) {
        std::string tf = cfg.tokenFile;
        if (tf.empty()) tf = exeDir + "\\.api_token";
        std::string tok;
        if (read_token_file(tf, tok)) cfg.apiKey = tok;
    }

    // --- 自动探测 ---
    if (mode == Mode::Push) {
        if (cfg.detectProgram) {
            std::string p = get_foreground_process_name();
            if (!p.empty()) cfg.programName = p;
        }
        if (cfg.detectStatus) {
            DWORD idleSec = get_idle_seconds();
            if ((int)(idleSec / 60) >= cfg.idleMinutes) {
                cfg.status = "away";
                if (cfg.statusText.empty() || cfg.statusText == "在线")
                    cfg.statusText = "离开";
            } else if (cfg.status.empty() || cfg.status == "away") {
                cfg.status = "online";
                if (cfg.statusText.empty() || cfg.statusText == "离开")
                    cfg.statusText = "在线";
            }
        }
    }

    // --- 文案补全 ---
    if (!cfg.statusText.empty() && cfg.statusText.size() > 32) {
        // 交给服务端校验也行，这里简单截断提示
        if (!quiet) std::cerr << "[提示] status_text 超过 32 字符，服务端可能拒绝\n";
    }
    if (cfg.statusText.empty()) cfg.statusText = default_status_text(cfg.status);

    // --- 组装请求 ---
    std::wstring method;
    std::wstring url;
    std::string  body;
    std::vector<std::wstring> headers;

    if (mode == Mode::Push) {
        std::string st = to_lower(trim(cfg.status));
        if (st != "online" && st != "away" && st != "busy" && st != "offline") {
            std::cerr << "[错误] status 只能是 online / away / busy / offline，当前: "
                      << cfg.status << "\n";
            return 2;
        }
        cfg.status = st;

        if (cfg.name.empty() && !quiet) {
            std::cerr << "[提示] name 为空，将沿用服务端已有值\n";
        }

        std::ostringstream js;
        js << "{";
        bool first = true;
        auto addField = [&](const char* k, const std::string& v) {
            if (v.empty()) return;
            if (!first) js << ",";
            first = false;
            js << json_string(k) << ":" << json_string(v);
        };
        addField("name", cfg.name);
        addField("status", cfg.status);
        addField("status_text", cfg.statusText);
        addField("program_name", cfg.programName);
        if (!cfg.since.empty()) {
            addField("since", cfg.since == "now" ? local_iso8601() : cfg.since);
        }
        js << "}";
        body = js.str();

        method = L"POST";
        url    = utf8_to_wide(cfg.url);

        headers.push_back(L"Content-Type: application/json; charset=utf-8");
        headers.push_back(L"Accept: application/json");
        headers.push_back(L"User-Agent: status-client/1.0");
        if (!cfg.apiKey.empty())
            headers.push_back(L"X-API-Key: " + utf8_to_wide(cfg.apiKey));
    } else {
        method = L"GET";
        if (mode == Mode::Health) {
            std::string h = cfg.healthUrl.empty() ? derive_health_url(cfg.url) : cfg.healthUrl;
            url = utf8_to_wide(h);
        } else {
            url = utf8_to_wide(cfg.url);
        }
        headers.push_back(L"Accept: application/json");
        headers.push_back(L"User-Agent: status-client/1.0");
    }

    if (verbose && !quiet) {
        std::cout << "[请求] " << (mode == Mode::Push ? "POST" : "GET") << " "
                  << wide_to_utf8(url) << "\n";
        if (!body.empty()) std::cout << "[请求体] " << body << "\n";
    }

    // --- 发送 ---
    HttpResult r = http_request(method, url, body, headers, cfg.timeoutMs);

    if (!r.ok) {
        std::cerr << "[错误] " << r.error << "\n";
        return 1;
    }

    bool httpOk = (r.status >= 200 && r.status < 300);

    if (mode == Mode::Push) {
        if (httpOk) {
            if (!quiet) {
                std::cout << "[OK] 状态已更新 (HTTP " << r.status << ")\n";
                std::string st, tx;
                if (json_extract(r.body, "status", st))
                    std::cout << "     状态: " << st;
                if (json_extract(r.body, "status_text", tx))
                    std::cout << " (" << tx << ")";
                std::cout << "\n";
                std::string nm, pg, up;
                if (json_extract(r.body, "name", nm) && !nm.empty())
                    std::cout << "     名称: " << nm << "\n";
                if (json_extract(r.body, "program_name", pg) && !pg.empty())
                    std::cout << "     程序: " << pg << "\n";
                if (json_extract(r.body, "server_updated", up) && !up.empty())
                    std::cout << "     更新: " << up << "\n";
            }
            if (verbose) std::cout << r.body << "\n";
            return 0;
        }
        std::cerr << "[失败] HTTP " << r.status << "\n";
        std::string errMsg;
        if (json_extract(r.body, "error", errMsg)) std::cerr << "       " << errMsg << "\n";
        else std::cerr << "       " << r.body << "\n";
        return 1;
    }

    if (mode == Mode::Health) {
        if (httpOk) {
            if (!quiet) std::cout << "[OK] 服务健康\n";
            if (verbose || !quiet) std::cout << r.body << "\n";
            return 0;
        }
        std::cerr << "[失败] HTTP " << r.status << ": " << r.body << "\n";
        return 1;
    }

    // --- Get ---
    if (!httpOk) {
        std::cerr << "[失败] HTTP " << r.status << ": " << r.body << "\n";
        return 1;
    }

    {
        std::string nm, st, tx, pg, sc, up;
        json_extract(r.body, "name", nm);
        json_extract(r.body, "status", st);
        json_extract(r.body, "status_text", tx);
        json_extract(r.body, "program_name", pg);
        json_extract(r.body, "since", sc);
        json_extract(r.body, "server_updated", up);

        if (quiet) return 0;

        std::cout << "名称       : " << (nm.empty() ? "(未设置)" : nm) << "\n";
        std::cout << "状态       : " << (st.empty() ? "?" : st);
        if (!tx.empty()) std::cout << "  (" << tx << ")";
        std::cout << "\n";
        std::cout << "当前程序   : " << (pg.empty() ? "(无)" : pg) << "\n";
        std::cout << "状态开始于 : " << (sc.empty() ? "?" : sc) << "\n";
        std::cout << "服务端更新 : " << (up.empty() ? "?" : up) << "\n";

        if (verbose) std::cout << "\n" << r.body << "\n";
    }
    return 0;
}