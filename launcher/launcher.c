/* orc — native launcher and recursive workspace boundary.
 * The bundled Gecko engine owns rendering and web security. orc owns
 * workspace identity, profile selection, first-run seeding and argv.
 * No shell, profile copying, or changes to another browser's profile. */
#ifndef _WIN32
# ifndef _POSIX_C_SOURCE
#  define _POSIX_C_SOURCE 200809L
# endif
# ifndef _DEFAULT_SOURCE
#  define _DEFAULT_SOURCE 1
# endif
# ifdef __APPLE__
#  ifndef _DARWIN_C_SOURCE
#   define _DARWIN_C_SOURCE 1
#  endif
# endif
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "workspace.h"

#ifndef ENGINE_REL
#error "ENGINE_REL must be the bundled engine path relative to the launcher"
#endif
#ifndef SEED_REL
#error "SEED_REL must be the seed user.js path relative to the launcher"
#endif
#ifndef SEED_CHROME_REL
#define SEED_CHROME_REL ""
#endif
#ifndef TRACTOR_REL
#define TRACTOR_REL ""
#endif

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "windows_command_line.h"
#define ORC_PATH_CAP 32768
#define ORC_SEP L'\\'
#define orc_main wmain
#define orc_getenv _wgetenv
#else
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <limits.h>
#include <signal.h>
#include <time.h>
#include <sys/wait.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif
#define ORC_PATH_CAP PATH_MAX
#define ORC_SEP '/'
#define orc_main main
#define orc_getenv getenv
#endif

/* All paths are checked before use: truncation must never select a
 * different workspace or silently put profile data beside the engine. */
static int path_copy(OrcChar *out, const OrcChar *value) {
    size_t len = orc_strlen(value);
    if (len >= ORC_PATH_CAP) return -1;
    memcpy(out, value, (len + 1) * sizeof(OrcChar));
    return 0;
}

static int path_append(OrcChar *out, const OrcChar *value) {
    size_t a = orc_strlen(out), b = orc_strlen(value);
    int separator = a && out[a - 1] != ORC_SEP;
    if (a + (size_t)separator + b >= ORC_PATH_CAP) return -1;
    if (separator) out[a++] = ORC_SEP;
    memcpy(out + a, value, (b + 1) * sizeof(OrcChar));
    return 0;
}

static int path_append_ascii(OrcChar *out, const char *value) {
    OrcChar converted[ORC_PATH_CAP];
    size_t i;
    if (strlen(value) >= ORC_PATH_CAP) return -1;
    for (i = 0; value[i]; i++) converted[i] = (OrcChar)value[i];
    converted[i] = 0;
    return path_append(out, converted);
}

#ifdef _WIN32
static int windows_directory_exists(const OrcChar *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY);
}

static int windows_profile_roots(OrcChar *current, OrcChar *legacy) {
    const OrcChar *home = orc_getenv(ORC_TEXT("APPDATA"));
    if (home && *home) {
        if (path_copy(current, home) || path_copy(legacy, home)) return -1;
    } else {
        home = orc_getenv(ORC_TEXT("USERPROFILE"));
        if (!home || !*home || path_copy(current, home) ||
            path_copy(legacy, home) ||
            path_append(current, ORC_TEXT("AppData\\Roaming")) ||
            path_append(legacy, ORC_TEXT("AppData\\Roaming"))) return -1;
    }
    if (path_append(current, ORC_TEXT("orc")) ||
        path_append(legacy, ORC_TEXT("Nightware Labz")) ||
        path_append(legacy, ORC_TEXT("orc"))) return -1;
    return 0;
}

/* Move the former per-user profile root once. If both roots already exist,
 * leave both intact and keep using the old root so no profile is overwritten. */
static int migrate_windows_profile_root(void) {
    OrcChar current[ORC_PATH_CAP], legacy[ORC_PATH_CAP];
    if (windows_profile_roots(current, legacy)) return -1;
    if (!windows_directory_exists(legacy) || windows_directory_exists(current))
        return 0;
    if (MoveFileExW(legacy, current, MOVEFILE_COPY_ALLOWED | MOVEFILE_WRITE_THROUGH))
        return 0;
    return windows_directory_exists(current) ? 0 : -1;
}
#endif

static int append_ascii(OrcChar *out, const char *value) {
    OrcChar native[ORC_MAX_WORKSPACE];
    size_t i = 0;
    for (; value[i] && i < ORC_MAX_WORKSPACE - 1; i++) native[i] = (OrcChar)value[i];
    if (value[i]) return -1;
    native[i] = 0;
    return path_append(out, native);
}

static int self_dir(OrcChar *out) {
#ifdef _WIN32
    DWORD n = GetModuleFileNameW(NULL, out, ORC_PATH_CAP);
    if (!n || n >= ORC_PATH_CAP) return -1;
    OrcChar *slash = wcsrchr(out, ORC_SEP);
#else
#ifdef __APPLE__
    char exe[ORC_PATH_CAP];
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) || !realpath(exe, out)) return -1;
#else
    ssize_t n = readlink("/proc/self/exe", out, ORC_PATH_CAP - 1);
    if (n < 0 || n >= ORC_PATH_CAP - 1) return -1;
    out[n] = 0;
#endif
    OrcChar *slash = strrchr(out, ORC_SEP);
#endif
    if (!slash) return -1;
    /* Keep the separator when the executable lives at the filesystem root. */
    if (slash == out
#ifdef _WIN32
        || (slash == out + 2 && out[1] == L':')
#endif
    ) slash[1] = 0;
    else *slash = 0;
    return 0;
}

static int make_dir(const OrcChar *path) {
#ifdef _WIN32
    if (CreateDirectoryW(path, NULL)) return 0;
    if (GetLastError() != ERROR_ALREADY_EXISTS) return -1;
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY) ? 0 : -1;
#else
    if (!mkdir(path, 0700)) return 0;
    struct stat st;
    return errno == EEXIST && !stat(path, &st) && S_ISDIR(st.st_mode) ? 0 : -1;
#endif
}

static int make_dirs(const OrcChar *path) {
    OrcChar scratch[ORC_PATH_CAP];
    if (path_copy(scratch, path)) return -1;
    size_t start = 1;
#ifdef _WIN32
    /* Skip drive roots and the server/share part of UNC paths. */
    if (scratch[0] && scratch[1] == L':') start = 3;
    else if (scratch[0] == L'\\' && scratch[1] == L'\\') {
        start = 2;
        for (int n = 0; n < 2; n++) {
            while (scratch[start] && scratch[start] != L'\\') start++;
            if (scratch[start]) start++;
        }
    }
#endif
    for (OrcChar *p = scratch + start; *p; p++) {
        if (*p == ORC_SEP) {
            *p = 0;
            int result = make_dir(scratch);
            *p = ORC_SEP;
            if (result) return -1;
        }
    }
    return make_dir(scratch);
}

static int regular_file(const OrcChar *path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    return !stat(path, &st) && S_ISREG(st.st_mode);
#endif
}

/* Publish a complete seed atomically without replacing an existing file.
 * Concurrent launchers must never start Gecko with a half-written user.js.
 * Missing/failed seeds stop startup; the user's entry always wins. */
static int seed_profile(const OrcChar *seed, const OrcChar *target) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesW(target);
    if (attr != INVALID_FILE_ATTRIBUTES)
        return attr & FILE_ATTRIBUTE_DIRECTORY ? -1 : 0;
    OrcChar staging[ORC_PATH_CAP];
    int copied = 0;
    /* CopyFileW with fail-if-exists avoids clobbering another launcher's
     * staging file and has no GetTempFileNameW MAX_PATH restriction. */
    for (unsigned attempt = 0; attempt < 100; attempt++) {
        int n = _snwprintf(staging, ORC_PATH_CAP, L"%ls.orc-%lu-%u", target,
                           GetCurrentProcessId(), attempt);
        if (n < 0 || n >= ORC_PATH_CAP) return -1;
        if (CopyFileW(seed, staging, TRUE)) { copied = 1; break; }
        DWORD error = GetLastError();
        if (error != ERROR_FILE_EXISTS && error != ERROR_ALREADY_EXISTS) {
            DeleteFileW(staging);
            return -1;
        }
    }
    if (!copied) return -1;
    int failed = 0;
    if (!MoveFileExW(staging, target, 0)) {
        DWORD error = GetLastError();
        failed = !((error == ERROR_FILE_EXISTS || error == ERROR_ALREADY_EXISTS) && regular_file(target));
    }
    DeleteFileW(staging);
    return failed ? -1 : 0;
#else
    struct stat st;
    /* lstat also protects dangling symlinks: never replace a user's entry. */
    if (!lstat(target, &st)) return regular_file(target) ? 0 : -1;
    if (errno != ENOENT) return -1;
    if (!regular_file(seed)) return -1;
    int input = open(seed, O_RDONLY);
    if (input < 0) return -1;
    OrcChar staging[ORC_PATH_CAP];
    size_t len = strlen(target);
    const char suffix[] = ".orc-XXXXXX";
    if (len + sizeof(suffix) > sizeof(staging)) { close(input); return -1; }
    memcpy(staging, target, len);
    memcpy(staging + len, suffix, sizeof(suffix));
    int output = mkstemp(staging);
    if (output < 0) {
        close(input);
        return -1;
    }
    char buffer[8192];
    ssize_t size;
    int failed = 0;
    while ((size = read(input, buffer, sizeof(buffer))) != 0) {
        if (size < 0) {
            if (errno == EINTR) continue;
            failed = 1;
            break;
        }
        ssize_t written = 0;
        while (written < size) {
            ssize_t n = write(output, buffer + written, (size_t)(size - written));
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) { failed = 1; break; }
            written += n;
        }
        if (failed) break;
    }
    if (close(input)) failed = 1;
    if (close(output)) failed = 1;
    /* link is an atomic no-replace publication on the same filesystem.
     * Another successful launcher may have published first. */
    if (!failed && link(staging, target))
        failed = !(errno == EEXIST && regular_file(target));
    unlink(staging);
    return failed ? -1 : 0;
#endif
}

static int profile_path(OrcChar *profile, const OrcWorkspace *ws) {
#ifndef _WIN32
    const OrcChar *home;
#endif
#ifdef _WIN32
    OrcChar current[ORC_PATH_CAP], legacy[ORC_PATH_CAP];
    if (windows_profile_roots(current, legacy)) return -1;
    if (windows_directory_exists(legacy)) {
        if (path_copy(profile, legacy)) return -1;
    } else if (path_copy(profile, current)) return -1;
#elif defined(__APPLE__)
    home = getenv("HOME");
    if (!home || home[0] != '/' || path_copy(profile, home) ||
        path_append(profile, "Library/Application Support/orc")) return -1;
#else
    home = getenv("XDG_DATA_HOME");
    /* XDG paths must be absolute; ignore relative values per the spec. */
    if (home && home[0] == '/') {
        if (path_copy(profile, home) || path_append(profile, "orc")) return -1;
    } else {
        home = getenv("HOME");
        if (!home || home[0] != '/' || path_copy(profile, home) ||
            path_append(profile, ".local/share/orc")) return -1;
    }
#endif
    if (ws->depth) {
        if (path_append(profile, ORC_TEXT("workspaces"))) return -1;
        const char *cursor = ws->name;
        for (unsigned i = 0; i < ws->depth; i++) {
            char segment[ORC_MAX_SEGMENT + 1];
            size_t len = 0;
            while (*cursor && *cursor != '/') segment[len++] = *cursor++;
            segment[len] = 0;
            if (*cursor) cursor++;
            if ((i && path_append(profile, ORC_TEXT("children"))) ||
                append_ascii(profile, segment)) return -1;
        }
    }
    return path_append(profile, ORC_TEXT("profile"));
}

static int process_alive(unsigned long pid) {
    if (!pid) return 0;
#ifdef _WIN32
    HANDLE process = OpenProcess(SYNCHRONIZE, FALSE, (DWORD)pid);
    if (!process) return 0;
    DWORD state = WaitForSingleObject(process, 0);
    CloseHandle(process);
    return state == WAIT_TIMEOUT;
#else
    return kill((pid_t)pid, 0) == 0 || errno == EPERM;
#endif
}

static int search_service_ready(const OrcChar *pid_file) {
#ifdef _WIN32
    FILE *file = _wfopen(pid_file, L"r");
#else
    FILE *file = fopen(pid_file, "r");
#endif
    if (!file) return 0;
    unsigned long pid = 0;
    int read_ok = fscanf(file, "%lu", &pid) == 1;
    fclose(file);
    return read_ok && process_alive(pid);
}

/* Start the local Tractor search endpoint before Gecko. The global Orc
 * profile owns the service so every workspace shares the same local port.
 * Its parent PID remains the launcher PID (exec on Unix, wait on Windows). */
static int launch_search_service(const OrcChar *dir) {
    if (!TRACTOR_REL[0]) return 0; /* launcher-only fixture builds */
    OrcChar service[ORC_PATH_CAP], data_dir[ORC_PATH_CAP], pid_file[ORC_PATH_CAP];
    OrcWorkspace root = {0};
    if (path_copy(service, dir) || path_append_ascii(service, TRACTOR_REL) ||
        path_copy(data_dir, dir) || profile_path(data_dir, &root) ||
        path_append(data_dir, ORC_TEXT("tractor-data")) || make_dirs(data_dir) ||
        path_copy(pid_file, data_dir) || path_append(pid_file, ORC_TEXT("search-service.pid"))) {
        fprintf(stderr, "orc: could not prepare Tractor's local search service\n");
        return -1;
    }
    if (!regular_file(service)) {
        fprintf(stderr, "orc: Tractor's local search engine is missing; reinstall orc\n");
        return -1;
    }
#ifdef _WIN32
    OrcChar pid[32], *args[6];
    _snwprintf(pid, 32, L"%lu", (unsigned long)GetCurrentProcessId());
    args[0] = service;
    args[1] = L"--serve";
    args[2] = L"--data-dir";
    args[3] = data_dir;
    args[4] = L"--parent-pid";
    args[5] = pid;
    wchar_t *command = (wchar_t *)calloc(32767, sizeof(wchar_t));
    if (!command) return -1;
    for (int i = 0; i < 6; i++) {
        if (orc_command_arg(command, 32767, args[i])) {
            free(command);
            return -1;
        }
    }
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    BOOL started = CreateProcessW(service, command, NULL, NULL, FALSE,
                                  CREATE_NO_WINDOW, NULL, dir, &si, &pi);
    DWORD error = started ? 0 : GetLastError();
    free(command);
    if (!started) {
        fprintf(stderr, "orc: could not start Tractor's search engine (Windows error %lu)\n", error);
        return -1;
    }
    CloseHandle(pi.hThread);
#else
    char pid[32];
    snprintf(pid, sizeof(pid), "%lu", (unsigned long)getpid());
    char *args[] = {(char *)service, "--serve", "--data-dir", (char *)data_dir,
                    "--parent-pid", pid, NULL};
    pid_t child = fork();
    if (child < 0) {
        fprintf(stderr, "orc: could not start Tractor's search engine: %s\n", strerror(errno));
        return -1;
    }
    if (child == 0) {
        execv(service, args);
        _exit(127);
    }
#endif
    int ready = 0;
    /* 600 attempts x 50 ms = 30 s. A cold PyInstaller/Qt start on a
     * slow machine outlasts the old 5 s window easily; the loop still
     * bails at once if the child dies, so a long window costs nothing
     * on the failure path. */
    for (int attempt = 0; attempt < 600; attempt++) {
        if (search_service_ready(pid_file)) {
            ready = 1;
            break;
        }
#ifdef _WIN32
        if (WaitForSingleObject(pi.hProcess, 0) == WAIT_OBJECT_0) break;
        Sleep(50);
#else
        int status = 0;
        if (waitpid(child, &status, WNOHANG) == child) break;
        struct timespec delay = {0, 50000000};
        nanosleep(&delay, NULL);
#endif
    }
#ifdef _WIN32
    CloseHandle(pi.hProcess);
#endif
    if (!ready) {
        fprintf(stderr, "orc: Tractor's local search service did not become ready\n");
        return -1;
    }
    return 0;
}

static void json_string(const char *value) {
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)value; *p; p++) {
        if (*p == '"' || *p == '\\') { putchar('\\'); putchar(*p); }
        else if (*p < 32) printf("\\u%04x", *p);
        else putchar(*p);
    }
    putchar('"');
}

static int print_info(const OrcWorkspace *ws, const OrcChar *profile) {
    OrcWorkspace parent = *ws;
    orc_workspace_parent(&parent);
    printf("{\"workspace\":");
    json_string(ws->depth ? ws->name : "/");
    printf(",\"parent\":");
    if (ws->depth) json_string(parent.depth ? parent.name : "/");
    else printf("null");
    printf(",\"depth\":%u,\"max_depth\":%d,\"profile\":", ws->depth, ORC_MAX_DEPTH);
#ifdef _WIN32
    char utf8[ORC_PATH_CAP * 4];
    if (!WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, profile, -1,
                             utf8, (int)sizeof(utf8), NULL, NULL)) return -1;
    json_string(utf8);
#else
    json_string(profile);
#endif
    printf("}\n");
    return 0;
}

static int export_workspace(const OrcWorkspace *ws) {
    char depth[16];
    snprintf(depth, sizeof(depth), "%u", ws->depth);
#ifdef _WIN32
    OrcChar name[ORC_MAX_WORKSPACE], number[16];
    const char *value = ws->depth ? ws->name : "/";
    size_t i;
    for (i = 0; value[i]; i++) name[i] = (OrcChar)value[i];
    name[i] = 0;
    for (i = 0; depth[i]; i++) number[i] = (OrcChar)depth[i];
    number[i] = 0;
    return _wputenv_s(L"ORC_WORKSPACE", name) || _wputenv_s(L"ORC_WORKSPACE_DEPTH", number) ? -1 : 0;
#else
    return setenv("ORC_WORKSPACE", ws->depth ? ws->name : "/", 1) ||
           setenv("ORC_WORKSPACE_DEPTH", depth, 1) ? -1 : 0;
#endif
}

static int launch_engine(const OrcChar *engine, const OrcChar *dir,
                         const OrcChar *profile, int argc, OrcChar **argv,
                         const OrcWorkspace *ws) {
    OrcChar **args = (OrcChar **)calloc((size_t)argc + 5, sizeof(OrcChar *));
    if (!args) return -1;
    int count = 0;
    args[count++] = (OrcChar *)engine;
    args[count++] = ORC_TEXT("-profile");
    args[count++] = (OrcChar *)profile;
    /* Never let a named branch hand its URL to a different running profile.
     * Gecko's own profile lock rejects a second concurrent open of this branch. */
    if (ws->depth) args[count++] = ORC_TEXT("-no-remote");
    for (int i = 1; i < argc; i++) args[count++] = argv[i];
#ifdef _WIN32
    const size_t cap = 32767; /* CreateProcessW limit, including NUL */
    wchar_t *command = (wchar_t *)calloc(cap, sizeof(wchar_t));
    if (!command) { free(args); return -1; }
    for (int i = 0; i < count; i++) {
        if (orc_command_arg(command, cap, args[i])) {
            fprintf(stderr, "orc: engine command line exceeds the Windows limit\n");
            free(command);
            free(args);
            return -1;
        }
    }
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    BOOL started = CreateProcessW(engine, command, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi);
    DWORD error = started ? 0 : GetLastError();
    free(command);
    free(args);
    if (!started) {
        fprintf(stderr, "orc: could not start engine (Windows error %lu)\n", error);
        return -1;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    return 0;
#else
    (void)dir;
    execv(engine, args);
    free(args);
    fprintf(stderr, "orc: could not start engine: %s\n", strerror(errno));
    return -1;
#endif
}

int orc_main(int argc, OrcChar **argv) {
    OrcWorkspace ws = {0};
    argc = orc_workspace_parse(argc, argv, orc_getenv(ORC_TEXT("ORC_WORKSPACE")), &ws);
    if (argc < 0) return 2;
    if (ws.help) {
        puts("orc — recursive browser workspaces\n"
             "  --orc-workspace <path>   Select / (default) or a named branch\n"
             "  --orc-child <name>       Descend into a fresh, separate profile\n"
             "  --orc-parent             Select the parent workspace\n"
             "  --orc-workspace-info     Print lineage and profile as JSON; do not launch\n"
             "  --orc-help               Show this help\n"
             "Workspace selection starts at ORC_WORKSPACE, or / when unset.\n"
             "Selectors apply left to right; --orc-workspace resets the path.\n"
             "Named workspaces use -no-remote; close a branch before reopening it.\n"
             "Other engine arguments are forwarded; profile selectors are reserved.");
        return 0;
    }
    OrcChar profile[ORC_PATH_CAP];
    if (ws.info) {
        if (profile_path(profile, &ws)) {
            fprintf(stderr, "orc: cannot resolve workspace profile (missing home or path too long)\n");
            return 1;
        }
        return print_info(&ws, profile) ? 1 : 0;
    }
#ifdef _WIN32
    if (migrate_windows_profile_root()) {
        fprintf(stderr, "orc: could not migrate the existing profile folder safely\n");
        return 1;
    }
#endif
    if (profile_path(profile, &ws)) {
        fprintf(stderr, "orc: cannot resolve workspace profile (missing home or path too long)\n");
        return 1;
    }
    OrcChar dir[ORC_PATH_CAP], engine[ORC_PATH_CAP], seed[ORC_PATH_CAP], userjs[ORC_PATH_CAP];
    if (self_dir(dir) || path_copy(engine, dir) || path_copy(seed, dir)) goto path_error;
    /* Compile-time relative paths contain ASCII only. */
    OrcChar engine_rel[ORC_PATH_CAP], seed_rel[ORC_PATH_CAP];
    size_t i;
    if (strlen(ENGINE_REL) >= ORC_PATH_CAP || strlen(SEED_REL) >= ORC_PATH_CAP) goto path_error;
    for (i = 0; ENGINE_REL[i]; i++) engine_rel[i] = (OrcChar)ENGINE_REL[i];
    engine_rel[i] = 0;
    for (i = 0; SEED_REL[i]; i++) seed_rel[i] = (OrcChar)SEED_REL[i];
    seed_rel[i] = 0;
    if (path_append(engine, engine_rel) || path_append(seed, seed_rel)) goto path_error;
    if (!regular_file(engine)) {
        fprintf(stderr, "orc: bundled engine missing; the install is incomplete, reinstall orc\n");
        return 1;
    }
#ifndef _WIN32
    /* macOS engine bundle lookup requires a canonical path with no '..'. */
    OrcChar clean[ORC_PATH_CAP];
    if (!realpath(engine, clean) || path_copy(engine, clean)) goto path_error;
#endif
    if (make_dirs(profile)) {
        fprintf(stderr, "orc: could not create workspace profile\n");
        return 1;
    }
    if (path_copy(userjs, profile) || path_append(userjs, ORC_TEXT("user.js"))) goto path_error;
    if (seed_profile(seed, userjs)) {
        fprintf(stderr, "orc: could not seed workspace profile; check the installation and permissions\n");
        return 1;
    }
    if (SEED_CHROME_REL[0]) {
        OrcChar chrome_seed[ORC_PATH_CAP], chrome_dir[ORC_PATH_CAP], chrome_css[ORC_PATH_CAP];
        if (path_copy(chrome_seed, dir) || path_append_ascii(chrome_seed, SEED_CHROME_REL) ||
            path_copy(chrome_dir, profile) || path_append(chrome_dir, ORC_TEXT("chrome")) ||
            make_dirs(chrome_dir) || path_copy(chrome_css, chrome_dir) ||
            path_append(chrome_css, ORC_TEXT("userChrome.css")) ||
            seed_profile(chrome_seed, chrome_css)) {
            fprintf(stderr, "orc: could not seed the default workspace theme; check the installation and permissions\n");
            return 1;
        }
    }
    if (export_workspace(&ws)) {
        fprintf(stderr, "orc: could not export workspace context\n");
        return 1;
    }
    if (launch_search_service(dir)) return 1;
    return launch_engine(engine, dir, profile, argc, argv, &ws) ? 1 : 0;
path_error:
    fprintf(stderr, "orc: could not resolve installation path (invalid or too long)\n");
    return 1;
}
