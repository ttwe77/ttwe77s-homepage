// client.cpp — 个人状态 API 客户端（托盘版）
//
// 编译（MinGW-w64）：
//   g++ -std=c++17 -O2 -o client.exe client.cpp -lwinhttp -lshell32 -luser32 -lgdi32
//
// 用法：
//   client.exe                      # 按 client.ini 推送状态，并常驻托盘
//   client.exe --status busy        # 临时覆盖状态并托盘常驻
//   client.exe --get                # 查询当前状态（控制台）
//   client.exe --health             # 健康检查（控制台）
//   client.exe --once               # 只推送一次后退出
//   client.exe -c D:\x\my.ini       # 指定配置文件
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
#include <regex>
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

// ============================ 优雅退出 ============================

static volatile LONG g_stop = 0;
static HWND g_tray_hwnd = nullptr;

static BOOL WINAPI console_ctrl_handler(DWORD type) {
    switch (type) {
        case CTRL_C_EVENT:
        case CTRL_BREAK_EVENT:
        case CTRL_CLOSE_EVENT:
        case CTRL_LOGOFF_EVENT:
        case CTRL_SHUTDOWN_EVENT:
            InterlockedExchange(&g_stop, 1);
            if (g_tray_hwnd) {
                PostMessageW(g_tray_hwnd, WM_CLOSE, 0, 0);
            }
            return TRUE;
        default:
            return FALSE;
    }
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

            std::string key_raw = trim(t.substr(0, eq));
            std::string key     = to_lower(key_raw);
            std::string val     = trim(t.substr(eq + 1));

            // 去掉值的行内注释（前面必须有空白，避免误伤 URL/Token）
            for (size_t i = 0; i + 1 < val.size(); ++i) {
                if ((val[i] == ';' || val[i] == '#') &&
                    (unsigned char)val[i - 1] <= ' ') {
                    val = trim(val.substr(0, i));
                    break;
                }
            }

            // 以 re:/regex: 开头的键保留原始大小写（正则可能大小写敏感）
            if (key.rfind("re:", 0) == 0 || key.rfind("regex:", 0) == 0) {
                key = key_raw;
            }

            if (!key.empty()) {
                auto& sec_map = data_[section];
                if (sec_map.find(key) == sec_map.end()) {
                    order_[section].push_back(key);
                }
                sec_map[key] = val;
            }
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

    // 按 INI 出现顺序返回某个段的所有键值对
    std::vector<std::pair<std::string, std::string>>
    items(const std::string& sec) const {
        std::vector<std::pair<std::string, std::string>> out;
        auto s = data_.find(to_lower(sec));
        if (s == data_.end()) return out;
        auto o = order_.find(to_lower(sec));
        if (o != order_.end()) {
            for (const auto& k : o->second) {
                auto it = s->second.find(k);
                if (it != s->second.end()) out.push_back(*it);
            }
        } else {
            for (const auto& kv : s->second) out.push_back(kv);
        }
        return out;
    }

private:
    std::map<std::string, std::map<std::string, std::string>> data_;
    std::map<std::string, std::vector<std::string>> order_;
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

// ── 由 PID 取进程基名（去路径、去 .exe）────────────────────
static std::string get_process_basename(DWORD pid) {
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

// ── UWP 子窗口回溯 ────────────────────────────────────────
struct UwpChildCtx {
    DWORD parentPid = 0;
    DWORD realPid   = 0;
    HWND  realHwnd  = nullptr;
    bool  strict    = true;
};

static BOOL CALLBACK enum_uwp_child_proc(HWND child, LPARAM lp) {
    auto* ctx = reinterpret_cast<UwpChildCtx*>(lp);

    if (ctx->strict) {
        wchar_t cls[128] = {0};
        GetClassNameW(child, cls, 128);
        if (lstrcmpW(cls, L"Windows.UI.Core.CoreWindow") != 0)
            return TRUE;
    }

    DWORD pid = 0;
    GetWindowThreadProcessId(child, &pid);
    if (pid && pid != ctx->parentPid) {
        ctx->realPid  = pid;
        ctx->realHwnd = child;
        return FALSE;
    }
    return TRUE;
}

static DWORD resolve_uwp_real_pid(HWND fg, DWORD fgPid) {
    for (int pass = 0; pass < 2; ++pass) {
        UwpChildCtx ctx;
        ctx.parentPid = fgPid;
        ctx.strict    = (pass == 0);
        EnumChildWindows(fg, enum_uwp_child_proc,
                         reinterpret_cast<LPARAM>(&ctx));
        if (ctx.realPid) return ctx.realPid;
    }
    return 0;
}

// ── 前台进程名（含 UWP 适配）──────────────────────────────
static std::string get_foreground_process_name() {
    HWND hwnd = GetForegroundWindow();
    if (!hwnd) return std::string();

    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (!pid) return std::string();

    std::string name = get_process_basename(pid);

    if (to_lower(name) == "applicationframehost") {
        DWORD realPid = resolve_uwp_real_pid(hwnd, pid);
        if (realPid) {
            std::string real = get_process_basename(realPid);
            if (!real.empty()) return real;
        }
    }

    return name;
}

// 获取当前前台顶层窗口的标题（含 UWP 兜底）
static std::string get_foreground_window_title() {
    HWND hwnd = GetForegroundWindow();
    if (!hwnd) return std::string();

    auto read_title = [](HWND h) -> std::string {
        int len = GetWindowTextLengthW(h);
        if (len <= 0) return std::string();
        std::wstring buf((size_t)len + 1, L'\0');
        int n = GetWindowTextW(h, &buf[0], (int)buf.size());
        if (n <= 0) return std::string();
        buf.resize((size_t)n);
        return wide_to_utf8(buf);
    };

    std::string t = read_title(hwnd);
    if (!t.empty()) return t;

    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    std::string name = get_process_basename(pid);
    if (to_lower(name) == "applicationframehost") {
        DWORD realPid = resolve_uwp_real_pid(hwnd, pid);
        if (realPid) {
            struct TitleCtx { DWORD pid; std::string title; };
            TitleCtx ctx{ realPid, {} };
            EnumChildWindows(hwnd,
                [](HWND h, LPARAM lp) -> BOOL {
                    auto* c = reinterpret_cast<TitleCtx*>(lp);
                    DWORD p = 0;
                    GetWindowThreadProcessId(h, &p);
                    if (p != c->pid) return TRUE;
                    int len = GetWindowTextLengthW(h);
                    if (len <= 0) return TRUE;
                    std::wstring buf((size_t)len + 1, L'\0');
                    int n = GetWindowTextW(h, &buf[0], (int)buf.size());
                    if (n <= 0) return TRUE;
                    buf.resize((size_t)n);
                    c->title = wide_to_utf8(buf);
                    return FALSE;
                },
                reinterpret_cast<LPARAM>(&ctx));
            if (!ctx.title.empty()) return ctx.title;
        }
    }
    return std::string();
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
// ============================ ISO 8601 校验 ============================
//
// 服务端要求 since 必须是合法 ISO 8601 时间，否则返回 400。
// 这里做两层校验：正则格式 + 数值范围。
static bool is_valid_iso8601(const std::string& s) {
    if (s.empty()) return false;

    static const std::regex re(
        R"(^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$)"
    );
    std::smatch m;
    if (!std::regex_match(s, m, re)) return false;

    auto toi = [&](size_t i) { return std::stoi(m[i].str()); };
    int mo  = toi(2);
    int d   = toi(3);
    int h   = toi(4);
    int mi  = toi(5);
    int se  = toi(6);

    if (mo < 1 || mo > 12) return false;
    if (d  < 1 || d  > 31) return false;
    if (h  > 23 || mi > 59 || se > 60) return false;
    return true;
}

// ============================ 名单 / 规则 ============================

// 程序名规范化：转小写、去空白、去掉 .exe 后缀
static std::string normalize_program(const std::string& s) {
    std::string t = to_lower(trim(s));
    if (t.size() > 4 && t.substr(t.size() - 4) == ".exe")
        t = t.substr(0, t.size() - 4);
    return t;
}

// 名单条目：普通字符串（大小写不敏感、忽略 .exe）或正则（re:/regex: 前缀）
struct ListMatcher {
    bool        is_regex = false;
    std::string literal;
    std::regex  re;

    bool match(const std::string& name) const {
        if (is_regex) {
            try { return std::regex_search(name, re); }
            catch (...) { return false; }
        }
        return literal == normalize_program(name);
    }
};

// 解析形如 "chrome,firefox,re:^code$,re:^(devenv|rider64)$" 的列表
// 说明：
//   - 逗号 / 分号 / 竖线用于分隔「普通条目」
//   - 遇到 re: / regex: 前缀时，竖线被视为正则内容，不再充当分隔符
static std::vector<ListMatcher> parse_matchers(const std::string& s) {
    std::vector<ListMatcher> result;
    size_t i = 0;
    const size_t n = s.size();

    auto skip_seps = [&]() {
        while (i < n && ((unsigned char)s[i] <= ' ' ||
                         s[i] == ',' || s[i] == ';' || s[i] == '|'))
            ++i;
    };

    while (true) {
        skip_seps();
        if (i >= n) break;

        bool   is_regex   = false;
        size_t prefix_len = 0;
        if (i + 3 <= n && to_lower(s.substr(i, 3)) == "re:") {
            is_regex = true; prefix_len = 3;
        } else if (i + 6 <= n && to_lower(s.substr(i, 6)) == "regex:") {
            is_regex = true; prefix_len = 6;
        }
        i += prefix_len;

        std::string item;
        while (i < n) {
            char c = s[i];
            if (c == ',' || c == ';') break;
            if (!is_regex && c == '|') break;
            item += c;
            ++i;
        }

        item = trim(item);
        if (item.empty()) continue;

        ListMatcher m;
        m.is_regex = is_regex;
        if (is_regex) {
            try {
                m.re = std::regex(item, std::regex::ECMAScript | std::regex::icase);
            } catch (...) {
                continue;   // 忽略非法正则
            }
            result.push_back(std::move(m));
        } else {
            std::string t = normalize_program(item);
            if (t.empty()) continue;
            m.literal = t;
            result.push_back(std::move(m));
        }
    }
    return result;
}

static bool list_matches(const std::vector<ListMatcher>& list, const std::string& name) {
    for (const auto& m : list) if (m.match(name)) return true;
    return false;
}

// since_rules 规则动作：覆盖某个字段
struct RuleAction {
    std::string field;   // status / status_text / program_name / program_title / since / name
    std::string value;
};

// since_rules 规则：program_name 命中 → 覆盖任意一个或多个字段
struct SinceRule {
    bool        is_regex = false;
    std::string literal;
    std::regex  re;
    std::vector<RuleAction> actions;
};

static std::vector<SinceRule> parse_since_rules(const Ini& ini) {
    std::vector<SinceRule> rules;
    for (const auto& kv : ini.items("since_rules")) {
        const std::string& key_raw = kv.first;
        std::string val = trim(kv.second);
        if (key_raw.empty() || val.empty()) continue;

        std::string kl = to_lower(key_raw);
        size_t prefix_len = 0;
        if (kl.rfind("re:", 0) == 0)           prefix_len = 3;
        else if (kl.rfind("regex:", 0) == 0)   prefix_len = 6;

        SinceRule r;
        if (prefix_len) {
            r.is_regex = true;
            try {
                r.re = std::regex(key_raw.substr(prefix_len),
                                  std::regex::ECMAScript | std::regex::icase);
            } catch (...) {
                continue;   // 忽略非法正则
            }
        } else {
            std::string lit = normalize_program(key_raw);
            if (lit.empty()) continue;
            r.literal = lit;
        }

        // 语法：
        //   "since=摸鱼中"                    → 只改 since
        //   "status=busy; status_text=开会中" → 改多个字段
        //   "摸鱼中"（不含 '='）              → 向后兼容，等价 since=摸鱼中
        if (val.find('=') == std::string::npos) {
            r.actions.push_back({"since", val});
        } else {
            size_t start = 0;
            while (start < val.size()) {
                size_t semi = val.find(';', start);
                std::string part = (semi == std::string::npos)
                                   ? val.substr(start)
                                   : val.substr(start, semi - start);
                part = trim(part);
                if (!part.empty()) {
                    size_t eq = part.find('=');
                    if (eq != std::string::npos) {
                        std::string k = to_lower(trim(part.substr(0, eq)));
                        std::string v = trim(part.substr(eq + 1));
                        if (!k.empty()) r.actions.push_back({k, v});
                    }
                }
                if (semi == std::string::npos) break;
                start = semi + 1;
            }
        }

        if (r.actions.empty()) continue;
        rules.push_back(std::move(r));
    }
    return rules;
}

static bool since_rule_matches(const SinceRule& r, const std::string& name) {
    if (name.empty()) return false;
    if (r.is_regex) {
        try { return std::regex_search(name, r.re); }
        catch (...) { return false; }
    }
    return r.literal == normalize_program(name);
}

// 托盘预设：显示名 = 状态|文案
struct Preset {
    std::string label;
    std::string status;
    std::string text;
};

static std::vector<Preset> parse_presets(const Ini& ini) {
    std::vector<Preset> out;
    for (const auto& kv : ini.items("presets")) {
        std::string label = trim(kv.first);
        std::string val   = trim(kv.second);
        if (label.empty() || val.empty()) continue;

        Preset p;
        p.label = label;

        size_t pipe = val.find('|');
        if (pipe == std::string::npos) {
            p.status = to_lower(val);
        } else {
            p.status = to_lower(trim(val.substr(0, pipe)));
            p.text   = trim(val.substr(pipe + 1));
        }

        if (p.status != "online" && p.status != "away" &&
            p.status != "busy"   && p.status != "offline") {
            continue;
        }
        out.push_back(std::move(p));
    }
    return out;
}

// ============================ 配置结构 ============================

struct Config {
    std::string url        = "http://127.0.0.1:5000/api/status";
    std::string healthUrl;      // 留空则自动推导
    std::string apiKey;
    int         timeoutMs  = 5000;

    // 持续推送间隔（秒）。>0 时循环推送；<=0 时只推送一次
    int         intervalSeconds = 30;

    std::string name;
    std::string status     = "online";
    std::string statusText;
    std::string programName;
    std::string programTitle;   // 仅当命中白名单时填充
    std::string since;

    bool detectProgram = false;
    bool detectStatus  = false;
    int  idleMinutes   = 10;

    // 手动指定状态后，不再被 detect_status 覆盖
    bool statusManual = false;

    // 程序名过滤（字符串或正则）
    std::vector<ListMatcher> programWhitelist;
    std::vector<ListMatcher> programBlacklist;

    // since 自定义显示规则
    std::vector<SinceRule>   sinceRules;

    // 托盘预设
    std::vector<Preset>      presets;

    // 电源事件推送（留空表示不推送）
    std::string powerSuspendStatus;   // 进入睡眠/休眠前
    std::string powerResumeStatus;    // 恢复后（留空则推当前状态）
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

// 套用黑白名单规则：
//   黑名单命中 → program_name = "黑名单命中，不予显示"，program_title 置空
//   白名单命中 → 抓取当前前台窗口标题
//   其余       → program_title 置空
static void apply_program_filter(Config& cfg) {
    if (cfg.programName.empty()) {
        cfg.programTitle.clear();
        return;
    }

    if (list_matches(cfg.programBlacklist, cfg.programName)) {
        cfg.programName  = "黑名单命中，不予显示";
        cfg.programTitle.clear();
        return;
    }

    if (list_matches(cfg.programWhitelist, cfg.programName)) {
        cfg.programTitle = get_foreground_window_title();
    } else {
        cfg.programTitle.clear();
    }
}

// ============================ 单次推送 ============================
//
// 返回值：0 成功 / 1 请求或接口失败 / 2 参数错误（配置非法，不适合重试）
//
static std::string g_mem_program_name;
static std::string g_mem_since;

static int push_once(Config& cfg, bool quiet, bool verbose) {
    // --- 自动探测（每轮重新计算，这样持续推送时能反映最新状态）---
    if (cfg.detectProgram) {
        std::string p = get_foreground_process_name();
        if (!p.empty()) cfg.programName = p;
    }

    // --- 黑白名单过滤 + 标题获取 ---
    apply_program_filter(cfg);

    if (cfg.detectStatus && !cfg.statusManual) {
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

    // --- 状态校验 ---
    std::string st = to_lower(trim(cfg.status));
    if (st != "online" && st != "away" && st != "busy" && st != "offline") {
        std::cerr << "[错误] status 只能是 online / away / busy / offline，当前: "
                  << cfg.status << "\n";
        return 2;
    }
    cfg.status = st;

    // --- 文案补全 ---
    if (cfg.statusText.empty()) cfg.statusText = default_status_text(cfg.status);

    // ------------------------------------------------------------------
    // 注意：
    // since_rules 是“本轮上报的覆盖规则”，不能直接修改 cfg。
    // 如果直接把 cfg.status 改成 busy，那么下一轮 push_once() 会把
    // 上一轮规则产生的 busy 当成新的基础状态，切换到其它程序后也会
    // 一直保持 busy，直到其它逻辑碰巧再次覆盖它。
    //
    // 因此这里复制一份本轮上报配置 effective，规则只修改 effective。
    // cfg 始终保留自动检测/手动选择得到的“基础状态”。
    // ------------------------------------------------------------------
    Config effective = cfg;

    // --- program_name / since 内存逻辑 ---
    std::string effective_since;
    if (cfg.programName == g_mem_program_name && !g_mem_since.empty()) {
        effective_since = g_mem_since;
    } else {
        if (!cfg.since.empty() && cfg.since != "now") {
            // 用户显式指定 since 时做一次合法性校验
            if (is_valid_iso8601(cfg.since)) {
                effective_since = cfg.since;
            } else {
                if (!quiet) {
                    std::cerr << "[警告] since 不是合法的 ISO 8601 时间，"
                                 "已改用当前时间: " << cfg.since << "\n";
                    std::cerr << "       提示：修改 client.ini 或命令行 --since 参数；"
                                 "如需表示“现在”，请留空或写 now。\n";
                }
                effective_since = local_iso8601();
            }
        } else {
            effective_since = local_iso8601();
        }
        g_mem_program_name = cfg.programName;
        g_mem_since = effective_since;
    }

    // --- since_rules：program_name 命中即覆盖对应字段（命中即停）---
    for (const auto& r : cfg.sinceRules) {
        if (!since_rule_matches(r, cfg.programName)) continue;

        bool statusChanged = false;
        bool textSet       = false;
        for (const auto& a : r.actions) {
            if (a.field == "since") {
                // 只接受合法 ISO 8601；非法值（如“现在”“摸鱼中”）直接忽略，
                // 保留内存逻辑生成的时间，避免服务端 400。
                if (is_valid_iso8601(a.value)) {
                    effective_since = a.value;
                } else {
                    if (!quiet) {
                        std::cerr << "[警告] since_rules 中 " << r.literal
                                  << " 的 since 值不是合法 ISO 8601 时间，"
                                     "已忽略: " << a.value << "\n";
                        std::cerr << "       请改用 status_text 承载“摸鱼中”这类文案，"
                                     "或填写形如 2026-10-04T22:17:21+08:00 的时间。\n";
                    }
                }
            } else if (a.field == "status") {
                std::string ruleStatus = to_lower(trim(a.value));
                if (ruleStatus == "online" || ruleStatus == "away" ||
                    ruleStatus == "busy"   || ruleStatus == "offline") {
                    effective.status = ruleStatus;
                    statusChanged = true;
                }
            } else if (a.field == "status_text") {
                effective.statusText = a.value;
                textSet = true;
            } else if (a.field == "program_name") {
                effective.programName = a.value;
            } else if (a.field == "program_title") {
                effective.programTitle = a.value;
            } else if (a.field == "name") {
                effective.name = a.value;
            }
            // 未识别字段静默忽略
        }
        // 规则改了 status 却没给 status_text 时，自动补默认文案
        if (statusChanged && !textSet)
            effective.statusText = default_status_text(effective.status);

        break;   // 只应用第一条命中的规则
    }

    // --- 组装 JSON ---
    std::ostringstream js;
    js << "{";
    bool first = true;
    auto addField = [&](const char* k, const std::string& v) {
        if (v.empty()) return;
        if (!first) js << ",";
        first = false;
        js << json_string(k) << ":" << json_string(v);
    };
    addField("name",          effective.name);
    addField("status",        effective.status);
    addField("status_text",   effective.statusText);
    addField("program_name",  effective.programName);
    addField("program_title", effective.programTitle);
    if (!effective_since.empty()) {
        addField("since", effective_since);
    }
    js << "}";
    std::string body = js.str();

    std::wstring method = L"POST";
    std::wstring url    = utf8_to_wide(cfg.url);

    std::vector<std::wstring> headers;
    headers.push_back(L"Content-Type: application/json; charset=utf-8");
    headers.push_back(L"Accept: application/json");
    headers.push_back(L"User-Agent: status-client/1.0");
    if (!cfg.apiKey.empty())
        headers.push_back(L"X-API-Key: " + utf8_to_wide(cfg.apiKey));

    if (verbose && !quiet) {
        std::cout << "[请求] POST " << wide_to_utf8(url) << "\n";
        if (!body.empty()) std::cout << "[请求体] " << body << "\n";
    }

    // --- 发送 ---
    HttpResult r = http_request(method, url, body, headers, cfg.timeoutMs);

    if (!r.ok) {
        std::cerr << "[错误] " << r.error << "\n";
        return 1;
    }

    bool httpOk = (r.status >= 200 && r.status < 300);

    if (httpOk) {
        if (!quiet) {
            std::cout << "[OK] 状态已更新 (HTTP " << r.status << ")\n";
            std::string s, tx;
            if (json_extract(r.body, "status", s))
                std::cout << "     状态: " << s;
            if (json_extract(r.body, "status_text", tx))
                std::cout << " (" << tx << ")";
            std::cout << "\n";
            std::string nm, pg, pt, up;
            if (json_extract(r.body, "name", nm) && !nm.empty())
                std::cout << "     名称: " << nm << "\n";
            if (json_extract(r.body, "program_name", pg) && !pg.empty())
                std::cout << "     程序: " << pg << "\n";
            if (json_extract(r.body, "program_title", pt) && !pt.empty())
                std::cout << "     标题: " << pt << "\n";
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

// 用指定状态推送一次，推送完成后恢复原状态（用于电源事件）
static void push_with_status(Config& cfg, const std::string& st,
                             const std::string& tx, bool quiet, bool verbose) {
    std::string savedSt = cfg.status;
    std::string savedTx = cfg.statusText;
    bool        savedMn = cfg.statusManual;

    cfg.status     = st;
    cfg.statusText = tx.empty() ? default_status_text(st) : tx;
    cfg.statusManual = true;   // 避免被 detect_status 覆盖

    push_once(cfg, quiet, verbose);

    cfg.status       = savedSt;
    cfg.statusText   = savedTx;
    cfg.statusManual = savedMn;
}

// ============================ 托盘 ============================

static const wchar_t* kTrayWndClass = L"StatusClientTrayWnd";
static const UINT WM_TRAY_NOTIFY  = WM_APP + 1;
static const UINT WM_TRAY_WAKE    = WM_APP + 2;
static const UINT_PTR TIMER_PUSH  = 1;

enum {
    IDM_STATUS_ONLINE  = 1001,
    IDM_STATUS_AWAY    = 1002,
    IDM_STATUS_BUSY    = 1003,
    IDM_STATUS_OFFLINE = 1004,
    IDM_PUSH_NOW       = 1010,
    IDM_EXIT           = 1099,
    IDM_PRESET_BASE    = 2000
};

static Config* g_cfg = nullptr;
static bool g_quiet = false;
static bool g_verbose = false;
static NOTIFYICONDATAW g_nid = {};
static bool g_pushing = false;

static void update_tray_tip() {
    if (!g_cfg) return;

    std::wstring tip = L"StatusClient - " + utf8_to_wide(g_cfg->status);
    if (!g_cfg->statusText.empty())
        tip += L" (" + utf8_to_wide(g_cfg->statusText) + L")";

    lstrcpynW(g_nid.szTip, tip.c_str(), ARRAYSIZE(g_nid.szTip));
    g_nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    Shell_NotifyIconW(NIM_MODIFY, &g_nid);
}

static void show_tray_menu(HWND hwnd) {
    POINT pt;
    GetCursorPos(&pt);

    HMENU menu = CreatePopupMenu();
    if (!menu) return;

    // 「设置状态」子菜单：四种基本状态 + 分隔线 + 预设
    HMENU statusMenu = CreatePopupMenu();

    auto add_status = [&](UINT id, const wchar_t* text, const std::string& st) {
        UINT flags = MF_STRING | ((g_cfg && g_cfg->status == st) ? MF_CHECKED : 0);
        AppendMenuW(statusMenu, flags, id, text);
    };
    add_status(IDM_STATUS_ONLINE,  L"在线 (online)",  "online");
    add_status(IDM_STATUS_AWAY,    L"离开 (away)",    "away");
    add_status(IDM_STATUS_BUSY,    L"忙碌 (busy)",    "busy");
    add_status(IDM_STATUS_OFFLINE, L"离线 (offline)", "offline");

    if (g_cfg && !g_cfg->presets.empty()) {
        AppendMenuW(statusMenu, MF_SEPARATOR, 0, nullptr);
        for (size_t i = 0; i < g_cfg->presets.size(); ++i) {
            std::wstring label = utf8_to_wide(g_cfg->presets[i].label);
            AppendMenuW(statusMenu, MF_STRING,
                        (UINT)(IDM_PRESET_BASE + i), label.c_str());
        }
    }

    AppendMenuW(menu, MF_POPUP | MF_STRING,
                (UINT_PTR)statusMenu, L"设置状态");

    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, IDM_PUSH_NOW, L"立即推送");
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, IDM_EXIT, L"退出");

    SetForegroundWindow(hwnd);

    int cmd = TrackPopupMenu(
        menu,
        TPM_RETURNCMD | TPM_RIGHTBUTTON,
        pt.x, pt.y, 0, hwnd, nullptr);

    DestroyMenu(menu);

    if (cmd)
        PostMessageW(hwnd, WM_COMMAND, (WPARAM)cmd, 0);
}

static LRESULT CALLBACK tray_wnd_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_TRAY_NOTIFY:
        if (LOWORD(lp) == WM_RBUTTONUP || LOWORD(lp) == WM_CONTEXTMENU) {
            show_tray_menu(hwnd);
        } else if (LOWORD(lp) == WM_LBUTTONDBLCLK) {
            if (g_cfg && !g_pushing) {
                g_pushing = true;
                push_once(*g_cfg, g_quiet, g_verbose);
                g_pushing = false;
                update_tray_tip();
            }
        }
        return 0;

    case WM_TRAY_WAKE:
        // 已有实例收到新实例的唤醒信号，短暂闪烁托盘图标
        if (g_cfg) update_tray_tip();
        return 0;

    case WM_COMMAND: {
        int id = LOWORD(wp);

        if (id == IDM_EXIT) {
            DestroyWindow(hwnd);
            return 0;
        }

        if (id == IDM_PUSH_NOW) {
            if (g_cfg && !g_pushing) {
                g_pushing = true;
                push_once(*g_cfg, g_quiet, g_verbose);
                g_pushing = false;
                update_tray_tip();
            }
            return 0;
        }

        // 预设菜单
        if (id >= IDM_PRESET_BASE && id < IDM_PRESET_BASE + 1000) {
            int idx = id - IDM_PRESET_BASE;
            if (g_cfg && idx < (int)g_cfg->presets.size()) {
                const Preset& p = g_cfg->presets[idx];
                g_cfg->status      = p.status;
                g_cfg->statusText  = p.text.empty()
                                     ? default_status_text(p.status)
                                     : p.text;
                g_cfg->statusManual = true;
                update_tray_tip();

                if (!g_pushing) {
                    g_pushing = true;
                    push_once(*g_cfg, g_quiet, g_verbose);
                    g_pushing = false;
                }
            }
            return 0;
        }

        std::string st;
        switch (id) {
        case IDM_STATUS_ONLINE:  st = "online";  break;
        case IDM_STATUS_AWAY:    st = "away";    break;
        case IDM_STATUS_BUSY:    st = "busy";    break;
        case IDM_STATUS_OFFLINE: st = "offline"; break;
        default: return 0;
        }

        if (g_cfg) {
            g_cfg->status = st;
            g_cfg->statusText = default_status_text(st);
            g_cfg->statusManual = true;
            update_tray_tip();

            if (!g_pushing) {
                g_pushing = true;
                push_once(*g_cfg, g_quiet, g_verbose);
                g_pushing = false;
            }
        }
        return 0;
    }

    case WM_POWERBROADCAST:
        if (wp == PBT_APMSUSPEND) {
            // 进入睡眠/休眠前：推送「挂起」状态（如果配置了）
            if (g_cfg && !g_cfg->powerSuspendStatus.empty()) {
                std::string st = to_lower(g_cfg->powerSuspendStatus);
                if (st == "online" || st == "away" ||
                    st == "busy"   || st == "offline") {
                    push_with_status(*g_cfg, st, "", true, false);
                }
            }
            return TRUE;
        }
        if (wp == PBT_APMRESUMEAUTOMATIC || wp == PBT_APMRESUMESUSPEND) {
            // 恢复后：推送配置的状态；未配置则推送当前状态
            if (g_cfg) {
                std::string st = to_lower(g_cfg->powerResumeStatus);
                if (st == "online" || st == "away" ||
                    st == "busy"   || st == "offline") {
                    push_with_status(*g_cfg, st, "", true, false);
                } else if (!g_pushing) {
                    g_pushing = true;
                    push_once(*g_cfg, g_quiet, g_verbose);
                    g_pushing = false;
                }
                update_tray_tip();
            }
            return TRUE;
        }
        break;

    case WM_TIMER:
        if (wp == TIMER_PUSH && g_cfg && !g_pushing) {
            g_pushing = true;
            int rc = push_once(*g_cfg, g_quiet, g_verbose);
            g_pushing = false;
            update_tray_tip();

            if (rc == 2) {
                MessageBoxW(hwnd, L"配置错误，程序将退出。",
                            L"StatusClient", MB_OK | MB_ICONERROR);
                DestroyWindow(hwnd);
            }
        }
        return 0;

    case WM_CLOSE:
        // 退出前主动推一次 offline
        if (g_cfg) {
            g_cfg->status = "offline";
            g_cfg->statusText = default_status_text("offline");
            push_once(*g_cfg, true, false);
        }
        DestroyWindow(hwnd);
        return 0;

    case WM_DESTROY:
        KillTimer(hwnd, TIMER_PUSH);
        Shell_NotifyIconW(NIM_DELETE, &g_nid);
        PostQuitMessage(0);
        return 0;
    }

    return DefWindowProcW(hwnd, msg, wp, lp);
}

static bool init_tray(HINSTANCE hInst, Config& cfg, bool quiet, bool verbose) {
    g_cfg = &cfg;
    g_quiet = quiet;
    g_verbose = verbose;

    WNDCLASSEXW wc = { sizeof(wc) };
    wc.lpfnWndProc = tray_wnd_proc;
    wc.hInstance = hInst;
    wc.lpszClassName = kTrayWndClass;

    if (!RegisterClassExW(&wc))
        return false;

    // 使用隐藏的顶层窗口（非 message-only），
    // 这样 WM_POWERBROADCAST 电源广播才能送达
    HWND hwnd = CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        kTrayWndClass, L"StatusClient",
        WS_POPUP,
        0, 0, 0, 0,
        nullptr, nullptr, hInst, nullptr);

    if (!hwnd)
        return false;

    g_tray_hwnd = hwnd;

    ZeroMemory(&g_nid, sizeof(g_nid));
    g_nid.cbSize = sizeof(g_nid);
    g_nid.hWnd = hwnd;
    g_nid.uID = 1;
    g_nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    g_nid.uCallbackMessage = WM_TRAY_NOTIFY;
    g_nid.hIcon = LoadIconW(nullptr, (LPCWSTR)IDI_APPLICATION);

    lstrcpynW(g_nid.szTip, L"StatusClient", ARRAYSIZE(g_nid.szTip));

    if (!Shell_NotifyIconW(NIM_ADD, &g_nid)) {
        DestroyWindow(hwnd);
        return false;
    }

    update_tray_tip();
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
        "; 请求超时（毫秒）\n"
        "timeout_ms = 5000\n"
        "\n"
        "; 持续推送间隔（秒）\n"
        ";   >0 : 每隔该秒数推送一次（托盘常驻，可在托盘菜单退出）\n"
        ";   <=0: 只推送一次后退出\n"
        "interval_seconds = 30\n"
        "\n"
        "[status]\n"
        "; 你的名称（必填，用于服务端识别身份）\n"
        "name =\n"
        "\n"
        "[auto]\n"
        "; 是否自动探测前台程序名并写入 program_name\n"
        "detect_program = false\n"
        "\n"
        "; 是否根据键鼠空闲时长自动切换 away / online\n"
        "; 注意：在托盘菜单手动选择状态后，本次运行不再被自动检测覆盖\n"
        "detect_status = false\n"
        "\n"
        "; 判定离开的空闲分钟数\n"
        "idle_minutes = 10\n"
        "\n"
        "[filter]\n"
        "; 程序名白名单：命中时才抓取前台窗口标题（program_title）\n"
        "; 逗号 / 分号 / 竖线分隔；不区分大小写；可省略 .exe 后缀\n"
        "; 以 re: 或 regex: 开头表示正则，此时竖线归正则内容\n"
        "; 例：\n"
        ";   program_whitelist = chrome,firefox,code,windowsterminal\n"
        ";   program_whitelist = re:^(chrome|msedge)$,re:^code$\n"
        "program_whitelist =\n"
        "\n"
        "; 程序名黑名单：命中时 program_name 变为「黑名单」，program_title 置空\n"
        "; 黑名单优先级高于白名单\n"
        "; 同样支持 re: 前缀正则\n"
        "; 例：wechat,kpassword,1password,re:^bitwarden\n"
        "program_blacklist =\n"
        "\n"
        "[since_rules]\n"
        "; 规则：当 program_name 命中左侧模式时，覆盖右侧列出的字段\n"
        "; 左值：普通程序名（不区分大小写、可省略 .exe），或以 re: / regex: 开头的正则\n"
        "; 右值：一个或多个 \"字段=值\"，用分号分隔；只应用第一条命中的规则\n"
        "; 提示：since 字段必须是 ISO 8601 时间，详见 [since_rules] 段说明。\n"
        ";\n"
"; 可覆盖字段：\n"
";   status         online / away / busy / offline\n"
";   status_text    状态文案（摸鱼中 / 开会中 …… 用这个字段，不要塞进 since）\n"
";   program_name   上报的程序名（可用来隐藏真实程序名）\n"
";   program_title  窗口标题\n"
";   since          状态起始时间，必须是 ISO 8601 时间，例如 2026-10-04T22:17:21+08:00\n"
";                  也可以写 now 让客户端用“当前时间”\n"
";                  注意：不能写“现在”“摸鱼中”这类文案，否则服务端会返回 400\n"
";   name           上报的名称\n"
        ";\n"
"; 示例：\n"
";   chrome                = status=busy; status_text=摸鱼中\n"
";   re:^code$             = status=busy; status_text=码代码中; program_title=\n"
";   re:^(devenv|rider64)$ = status=busy; status_text=IDE 中\n"
";   wechat                = status=busy; status_text=聊天中; program_name=通讯工具\n"
";\n"
"; 如果需要固定 since 为一个具体时间（必须为 ISO 8601）：\n"
";   chrome                = status=busy; status_text=摸鱼中; since=2026-10-04T12:00:00+08:00\n"
";\n"
"; 如果需要 since 跟随当前时间动态刷新（每次切换程序时重置），留空即可：\n"
";   chrome                = status=busy; status_text=摸鱼中\n"
";\n"
"; ⚠ 常见错误：\n"
";   错误：chrome = since=现在            （“现在”不是 ISO 时间，服务端 400）\n"
";   错误：chrome = since=摸鱼中          （同理）\n"
";   正确：chrome = status=busy; status_text=摸鱼中\n"
";   正确：chrome = since=2026-10-04T12:00:00+08:00\n"
";   正确：chrome = since=now             （客户端会替换成当前时间）\n"
        ";\n"
        "\n"
        "[presets]\n"
        "; 托盘菜单「设置状态」子菜单里的常用状态\n"
        "; 格式：显示名称 = 状态|文案；文案可省略（自动用默认文案）\n"
        "; 状态只能是 online / away / busy / offline\n"
        "; 例：\n"
        ";   会议中 = busy|开会\n"
        ";   午休 = away|午休\n"
        ";   专注中 = busy|请勿打扰\n"
        ";\n"
        "\n"
        "[power]\n"
        "; 电源事件：睡眠/休眠前与恢复后自动推送\n"
        "; 状态只能是 online / away / busy / offline；留空表示不推送\n"
        "; 例：suspend_status = offline  （睡眠前标记为离线）\n"
        ";     resume_status  = online   （恢复后自动回到在线）\n"
        "; 若 resume_status 留空，则恢复后推送当前状态\n"
        "suspend_status =\n"
        "resume_status  =\n";

    f.flush();
    return (bool)f;
}

// ============================ 命令行 ============================

static void print_usage() {
    std::cout <<
        "个人状态 API 客户端（托盘版）\n"
        "\n"
        "用法: client.exe [选项]\n"
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
        "      --interval <秒>   持续推送间隔；0 表示只推送一次\n"
        "      --once            只推送一次后退出（覆盖 interval_seconds）\n"
        "\n"
        "      --get             查询当前状态\n"
        "      --health          健康检查\n"
        "  -v, --verbose         输出完整响应\n"
        "  -q, --quiet           只输出错误\n"
        "  -h, --help            显示帮助\n";
}

// ============================ 主流程 ============================

static void enable_dpi_awareness() {
    // Win10 1703+：Per-Monitor V2（托盘菜单在混合 DPI 下才不会糊）
    if (HMODULE hUser32 = GetModuleHandleW(L"user32.dll")) {
        using SetCtxFn = BOOL (WINAPI*)(HANDLE);
        auto fn = (SetCtxFn)GetProcAddress(hUser32, "SetProcessDpiAwarenessContext");
        // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == (HANDLE)-4
        if (fn && fn((HANDLE)-4)) return;
    }
    // Vista+ 兜底：System DPI Aware
    SetProcessDPIAware();
}

int main() {
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
    enable_dpi_awareness();

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
    bool once    = false;
    int  timeoutOverride  = -1;
    int  intervalOverride = -1;

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
            else if (a == "--interval")                  intervalOverride = std::atoi(need("--interval").c_str());
            else if (a == "--once")                      once = true;
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

    // --- 检查配置文件是否存在；不存在则生成模板并弹窗提示用户填写 ---
    {
        std::wstring cfgPathW = utf8_to_wide(cfgPath);
        DWORD attrs = GetFileAttributesW(cfgPathW.c_str());
        bool exists = (attrs != INVALID_FILE_ATTRIBUTES) &&
                      !(attrs & FILE_ATTRIBUTE_DIRECTORY);

        if (!exists) {
            std::string werr;
            if (write_default_ini(cfgPath, werr)) {
                std::wstring msg =
                    L"已生成配置文件模板：\n\n" +
                    utf8_to_wide(cfgPath) +
                    L"\n\n请至少填写：\n"
                    L"  [server] url\n"
                    L"  [server] api_key（或同目录 .api_token）\n"
                    L"  [status] name\n\n"
                    L"填写后重新运行本程序。";

                MessageBoxW(nullptr, msg.c_str(),
                            L"StatusClient 配置提示",
                            MB_OK | MB_ICONINFORMATION);
                return 0;
            } else {
                std::wstring msg =
                    L"无法创建配置文件：\n" + utf8_to_wide(werr);

                MessageBoxW(nullptr, msg.c_str(),
                            L"StatusClient 错误",
                            MB_OK | MB_ICONERROR);
                return 2;
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
    cfg.timeoutMs  = ini.get_int("server", "timeout_ms", cfg.timeoutMs);
    cfg.intervalSeconds = ini.get_int("server", "interval_seconds", cfg.intervalSeconds);

    cfg.name        = ini.get("status", "name");
    cfg.status      = "online";  // 不再从 INI 读取 status，由托盘菜单/命令行控制

    cfg.detectProgram = ini.get_bool("auto", "detect_program", false);
    cfg.detectStatus  = ini.get_bool("auto", "detect_status", false);
    cfg.idleMinutes   = ini.get_int("auto", "idle_minutes", 10);

    cfg.programWhitelist = parse_matchers(ini.get("filter", "program_whitelist"));
    cfg.programBlacklist = parse_matchers(ini.get("filter", "program_blacklist"));

    cfg.sinceRules = parse_since_rules(ini);
    cfg.presets    = parse_presets(ini);

    cfg.powerSuspendStatus = ini.get("power", "suspend_status");
    cfg.powerResumeStatus  = ini.get("power", "resume_status");

    // 命令行覆盖
    auto applyOverride = [&](const char* key, std::string& target) {
        auto it = overrides.find(key);
        if (it != overrides.end()) target = it->second;
    };
    applyOverride("url", cfg.url);
    applyOverride("api_key", cfg.apiKey);
    applyOverride("name", cfg.name);
    applyOverride("status", cfg.status);

    // 命令行指定了 --status：标记为手动，自动检测不再覆盖
    if (overrides.find("status") != overrides.end()) {
        cfg.statusManual = true;
        if (overrides.find("status_text") == overrides.end())
            cfg.statusText = default_status_text(cfg.status);
    }

    applyOverride("status_text", cfg.statusText);
    applyOverride("program_name", cfg.programName);
    applyOverride("since", cfg.since);
    if (timeoutOverride  > 0) cfg.timeoutMs = timeoutOverride;
    if (intervalOverride >= 0) cfg.intervalSeconds = intervalOverride;

    // --- API Key 兜底：读 .api_token ---
    if (cfg.apiKey.empty()) {
        std::string tf = exeDir + "\\.api_token";
        std::string tok;
        if (read_token_file(tf, tok)) cfg.apiKey = tok;
    }

        // ------------------------------------------------------------------
    // 启动前扫描 since_rules：如果发现非法 ISO 8601 值，一次性弹窗提示，
    // 并把这类规则列出来，避免用户改完一个又漏一个。
    // 仅在 Push 模式 + 非 quiet 时弹，避免影响 --get / --health 的脚本调用。
    // ------------------------------------------------------------------
    if (mode == Mode::Push && !quiet) {
        struct BadSince { std::string ruleKey; std::string badValue; };
        std::vector<BadSince> badList;

        for (const auto& r : cfg.sinceRules) {
            for (const auto& a : r.actions) {
                if (a.field != "since") continue;
                // now 是客户端保留关键字，会替换成当前时间，允许
                if (a.value == "now") continue;
                if (!is_valid_iso8601(a.value)) {
                    std::string key = (r.is_regex ? "re:" : "") + r.literal;
                    badList.push_back({ key, a.value });
                }
            }
        }

        if (!badList.empty()) {
            std::wstring msg =
                L"检测到 client.ini 的 [since_rules] 中存在非法 since 值：\n\n";
            for (const auto& b : badList) {
                msg += L"  • " + utf8_to_wide(b.ruleKey)
                     + L"  ->  since=" + utf8_to_wide(b.badValue) + L"\n";
            }
            msg +=
                L"\n服务端要求 since 必须是 ISO 8601 时间（如 2026-10-04T22:17:21+08:00），\n"
                L"或者客户端关键字 now（会替换为当前时间）。\n"
                L"\n这些非法值本轮已被自动忽略，程序会继续运行，\n"
                L"但建议你尽快修改 client.ini：\n\n"
                L"  ✗ 错误：chrome = since=现在\n"
                L"  ✗ 错误：chrome = since=摸鱼中\n"
                L"  ✓ 正确：chrome = status=busy; status_text=摸鱼中\n"
                L"  ✓ 正确：chrome = since=2026-10-04T12:00:00+08:00\n"
                L"  ✓ 正确：chrome = since=now\n";

            MessageBoxW(nullptr, msg.c_str(),
                        L"StatusClient 配置提示",
                        MB_OK | MB_ICONWARNING);
        }
    }


    // ============================ Push 模式 ============================
    if (mode == Mode::Push) {
        // 必要项目检查
        std::vector<std::wstring> missing;
        if (cfg.url.empty())   missing.push_back(L"[server] url");
        if (cfg.name.empty())  missing.push_back(L"[status] name");
        if (cfg.apiKey.empty())
            missing.push_back(L"[server] api_key（或同目录 .api_token）");

        if (!missing.empty()) {
            std::wstring msg = L"必要配置缺失，程序无法启动：\n\n";
            for (const auto& m : missing) msg += L"  • " + m + L"\n";
            msg += L"\n请编辑 client.ini 或使用命令行参数后重试。";
            MessageBoxW(nullptr, msg.c_str(),
                        L"StatusClient 配置错误",
                        MB_OK | MB_ICONERROR);
            return 2;
        }

        if (!cfg.statusText.empty() && cfg.statusText.size() > 32 && !quiet)
            std::cerr << "[提示] status_text 超过 32 字符，服务端可能拒绝\n";

        // 单次推送：--once 或 interval_seconds <= 0
        if (once || cfg.intervalSeconds <= 0) {
            return push_once(cfg, quiet, verbose);
        }

        // ---- 单实例锁（仅托盘常驻模式）----
        HANDLE hMutex = CreateMutexW(nullptr, TRUE,
                                     L"Local\\StatusClient_Tray_SingleInstance");
        if (hMutex && GetLastError() == ERROR_ALREADY_EXISTS) {
            HWND existing = FindWindowW(kTrayWndClass, nullptr);
            if (existing) PostMessageW(existing, WM_TRAY_WAKE, 0, 0);
            if (!quiet) {
                MessageBoxW(nullptr,
                            L"StatusClient 已经在运行中。\n请查看系统托盘图标。",
                            L"StatusClient",
                            MB_OK | MB_ICONINFORMATION);
            }
            CloseHandle(hMutex);
            return 0;
        }

        // ---- 托盘常驻模式 ----
        // 优雅脱离控制台：
        //   - stdout 是真实控制台 → FreeConsole()，进程彻底不再挂控制台
        //   - stdout 已被重定向（管道/日志文件）→ 只隐藏窗口，保留输出
        if (!verbose) {
            HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
            DWORD ft = (hOut == INVALID_HANDLE_VALUE || hOut == nullptr)
                           ? FILE_TYPE_UNKNOWN
                           : GetFileType(hOut);
            if (ft == FILE_TYPE_CHAR) {
                FreeConsole();
            } else {
                if (HWND hCon = GetConsoleWindow()) ShowWindow(hCon, SW_HIDE);
            }
        }

        HINSTANCE hInst = GetModuleHandleW(nullptr);
        if (!init_tray(hInst, cfg, quiet, verbose)) {
            MessageBoxW(nullptr, L"托盘初始化失败。",
                        L"StatusClient", MB_OK | MB_ICONERROR);
            return 1;
        }

        // 启动后立即推送一次
        int rc = push_once(cfg, quiet, verbose);
        if (rc == 2) {
            MessageBoxW(nullptr, L"配置错误，程序退出。",
                        L"StatusClient", MB_OK | MB_ICONERROR);
            Shell_NotifyIconW(NIM_DELETE, &g_nid);
            return 2;
        }

        SetTimer(g_nid.hWnd, TIMER_PUSH,
                 (UINT)cfg.intervalSeconds * 1000, nullptr);

        MSG msg;
        while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }

        if (hMutex) CloseHandle(hMutex);
        return 0;
    }

    // ============================ GET / Health 模式 ============================
    std::wstring url;
    std::vector<std::wstring> headers;

    if (mode == Mode::Health) {
        std::string h = cfg.healthUrl.empty() ? derive_health_url(cfg.url) : cfg.healthUrl;
        url = utf8_to_wide(h);
    } else {
        url = utf8_to_wide(cfg.url);
    }
    headers.push_back(L"Accept: application/json");
    headers.push_back(L"User-Agent: status-client/1.0");

    if (verbose && !quiet) {
        std::cout << "[请求] GET " << wide_to_utf8(url) << "\n";
    }

    HttpResult r = http_request(L"GET", url, "", headers, cfg.timeoutMs);

    if (!r.ok) {
        std::cerr << "[错误] " << r.error << "\n";
        return 1;
    }

    bool httpOk = (r.status >= 200 && r.status < 300);

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
        std::string nm, st, tx, pg, pt, sc, up;
        json_extract(r.body, "name", nm);
        json_extract(r.body, "status", st);
        json_extract(r.body, "status_text", tx);
        json_extract(r.body, "program_name", pg);
        json_extract(r.body, "program_title", pt);
        json_extract(r.body, "since", sc);
        json_extract(r.body, "server_updated", up);

        if (quiet) return 0;

        std::cout << "名称       : " << (nm.empty() ? "(未设置)" : nm) << "\n";
        std::cout << "状态       : " << (st.empty() ? "?" : st);
        if (!tx.empty()) std::cout << "  (" << tx << ")";
        std::cout << "\n";
        std::cout << "当前程序   : " << (pg.empty() ? "(无)" : pg) << "\n";
        std::cout << "窗口标题   : " << (pt.empty() ? "(无)" : pt) << "\n";
        std::cout << "状态开始于 : " << (sc.empty() ? "?" : sc) << "\n";
        std::cout << "服务端更新 : " << (up.empty() ? "?" : up) << "\n";

        if (verbose) std::cout << "\n" << r.body << "\n";
    }
    return 0;
}