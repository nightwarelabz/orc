/*
 * orc — launcher
 *
 * A tiny native shim. It does three things and nothing else:
 *   1. finds the bundled LibreWolf engine next to itself
 *      (path baked in at compile time via -DENGINE_REL),
 *   2. makes sure orc's own profile folder exists and, the first
 *      time only, seeds it with orc's user.js (via -DSEED_REL),
 *   3. launches the engine with -profile <orc profile> and every
 *      argument it was given, forwarded verbatim.
 *
 * The engine binaries are unmodified upstream LibreWolf builds
 * (MPL-2.0). orc never touches another browser's profile.
 *
 * Compile (done by packaging/build-launcher.{sh,ps1} and CI):
 *   -DENGINE_REL='"engine/librewolf"'            (platform separators)
 *   -DSEED_REL='"profile-seed/user.js"'
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef ENGINE_REL
#error "ENGINE_REL must be defined (path of the engine binary, relative to the launcher)"
#endif
#ifndef SEED_REL
#error "SEED_REL must be defined (path of the seed user.js, relative to the launcher)"
#endif

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

/* ENGINE_REL / SEED_REL arrive as narrow ASCII strings; widen them. */
static wchar_t *widen(const char *s) {
    size_t n = strlen(s);
    wchar_t *w = (wchar_t *)malloc((n + 1) * sizeof(wchar_t));
    if (!w) return NULL;
    for (size_t i = 0; i <= n; i++) w[i] = (wchar_t)(unsigned char)s[i];
    return w;
}

static void dir_of(const wchar_t *path, wchar_t *out, size_t outlen) {
    wcsncpy(out, path, outlen - 1);
    out[outlen - 1] = L'\0';
    wchar_t *slash = wcsrchr(out, L'\\');
    if (slash) *slash = L'\0';
}

static void join_path(wchar_t *out, size_t outlen, const wchar_t *a, const wchar_t *b) {
    _snwprintf(out, outlen, L"%s\\%s", a, b);
    out[outlen - 1] = L'\0';
}

static void make_dirs(wchar_t *path) {
    /* CreateDirectoryW one level at a time (the string is ours to scratch). */
    for (wchar_t *p = path + 1; *p; p++) {
        if (*p == L'\\') {
            *p = L'\0';
            CreateDirectoryW(path, NULL);
            *p = L'\\';
        }
    }
    CreateDirectoryW(path, NULL);
}

static int file_exists(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

/* Append s to buf, quoted for CommandLineToArgvW-style parsing. */
static void append_quoted(wchar_t *buf, size_t cap, const wchar_t *s) {
    size_t len = wcslen(buf);
    if (len + 1 >= cap) return;
    buf[len++] = L'"';
    buf[len] = L'\0';
    size_t backslashes = 0;
    for (const wchar_t *p = s; *p; p++) {
        if (*p == L'\\') { backslashes++; continue; }
        if (*p == L'"') {
            while (backslashes && len + 1 < cap) { buf[len++] = L'\\'; backslashes--; }
            if (len + 2 < cap) { buf[len++] = L'\\'; buf[len++] = L'"'; }
            buf[len] = L'\0';
            continue;
        }
        while (backslashes && len + 1 < cap) { buf[len++] = L'\\'; backslashes--; }
        if (len + 1 < cap) buf[len++] = *p;
        buf[len] = L'\0';
    }
    while (backslashes && len + 1 < cap) { buf[len++] = L'\\'; backslashes--; }
    if (len + 1 < cap) buf[len++] = L'"';
    buf[len] = L'\0';
}

int wmain(int argc, wchar_t **argv) {
    wchar_t exe[32768];
    DWORD n = GetModuleFileNameW(NULL, exe, (DWORD)(sizeof(exe) / sizeof(exe[0])));
    if (n == 0 || n >= sizeof(exe) / sizeof(exe[0])) {
        fwprintf(stderr, L"orc: could not resolve its own path\n");
        return 1;
    }
    wchar_t dir[32768];
    dir_of(exe, dir, sizeof(dir) / sizeof(dir[0]));

    wchar_t *engine_rel = widen(ENGINE_REL);
    wchar_t *seed_rel = widen(SEED_REL);
    if (!engine_rel || !seed_rel) {
        fwprintf(stderr, L"orc: out of memory\n");
        return 1;
    }
    wchar_t engine[32768], seed[32768];
    join_path(engine, sizeof(engine) / sizeof(engine[0]), dir, engine_rel);
    join_path(seed, sizeof(seed) / sizeof(seed[0]), dir, seed_rel);

    if (!file_exists(engine)) {
        fwprintf(stderr, L"orc: engine not found at %s\norc: the install looks incomplete - reinstall orc.\n", engine);
        return 1;
    }

    /* Profile: %APPDATA%\Nightware Labz\orc\profile */
    wchar_t profile[32768];
    const wchar_t *appdata = _wgetenv(L"APPDATA");
    if (appdata && *appdata) {
        _snwprintf(profile, sizeof(profile) / sizeof(profile[0]),
                   L"%s\\Nightware Labz\\orc\\profile", appdata);
    } else {
        const wchar_t *home = _wgetenv(L"USERPROFILE");
        if (!home || !*home) {
            fwprintf(stderr, L"orc: neither APPDATA nor USERPROFILE is set\n");
            return 1;
        }
        _snwprintf(profile, sizeof(profile) / sizeof(profile[0]),
                   L"%s\\AppData\\Roaming\\Nightware Labz\\orc\\profile", home);
    }
    profile[sizeof(profile) / sizeof(profile[0]) - 1] = L'\0';
    {
        wchar_t scratch[32768];
        wcsncpy(scratch, profile, sizeof(scratch) / sizeof(scratch[0]) - 1);
        scratch[sizeof(scratch) / sizeof(scratch[0]) - 1] = L'\0';
        make_dirs(scratch);
    }

    /* Seed user.js on first run only - never overwrite the user's. */
    wchar_t userjs[32768];
    join_path(userjs, sizeof(userjs) / sizeof(userjs[0]), profile, L"user.js");
    if (!file_exists(userjs) && file_exists(seed)) {
        CopyFileW(seed, userjs, TRUE);
    }

    /* Command line: "engine" -profile "profile" <args...> */
    size_t cap = 65536;
    wchar_t *cmd = (wchar_t *)calloc(cap, sizeof(wchar_t));
    if (!cmd) {
        fwprintf(stderr, L"orc: out of memory\n");
        return 1;
    }
    append_quoted(cmd, cap, engine);
    wcscat_s(cmd, cap, L" -profile ");
    append_quoted(cmd, cap, profile);
    for (int i = 1; i < argc; i++) {
        wcscat_s(cmd, cap, L" ");
        append_quoted(cmd, cap, argv[i]);
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcessW(engine, cmd, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        fwprintf(stderr, L"orc: failed to launch the engine (error %lu)\n", GetLastError());
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}

#else /* POSIX: macOS + Linux */

#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <limits.h>

#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

static void dir_of(const char *path, char *out, size_t outlen) {
    snprintf(out, outlen, "%s", path);
    char *slash = strrchr(out, '/');
    if (slash) *slash = '\0';
}

static void join_path(char *out, size_t outlen, const char *a, const char *b) {
    snprintf(out, outlen, "%s/%s", a, b);
}

static void make_dirs(const char *path) {
    char scratch[PATH_MAX];
    snprintf(scratch, sizeof(scratch), "%s", path);
    for (char *p = scratch + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(scratch, 0755);
            *p = '/';
        }
    }
    mkdir(scratch, 0755);
}

static int file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static int copy_file(const char *from, const char *to) {
    FILE *in = fopen(from, "rb");
    if (!in) return -1;
    FILE *out = fopen(to, "wb");
    if (!out) { fclose(in); return -1; }
    char buf[8192];
    size_t r;
    while ((r = fread(buf, 1, sizeof(buf), in)) > 0) {
        if (fwrite(buf, 1, r, out) != r) { fclose(in); fclose(out); return -1; }
    }
    fclose(in);
    fclose(out);
    return 0;
}

static int self_dir(char *out, size_t outlen) {
    char exe[PATH_MAX];
#ifdef __APPLE__
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) != 0) return -1;
    char resolved[PATH_MAX];
    if (realpath(exe, resolved) != NULL) {
        dir_of(resolved, out, outlen);
    } else {
        dir_of(exe, out, outlen);
    }
#else
    ssize_t n = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    if (n < 0) return -1;
    exe[n] = '\0';
    dir_of(exe, out, outlen);
#endif
    return 0;
}

int main(int argc, char **argv) {
    char dir[PATH_MAX];
    if (self_dir(dir, sizeof(dir)) != 0) {
        fprintf(stderr, "orc: could not resolve its own path\n");
        return 1;
    }

    char engine[PATH_MAX], seed[PATH_MAX];
    join_path(engine, sizeof(engine), dir, ENGINE_REL);
    join_path(seed, sizeof(seed), dir, SEED_REL);

    if (!file_exists(engine)) {
        fprintf(stderr, "orc: engine not found at %s\n", engine);
        fprintf(stderr, "orc: the install looks incomplete - reinstall orc.\n");
        return 1;
    }

    /* Profile folder, per OS. */
    char profile[PATH_MAX];
    const char *home = getenv("HOME");
#ifdef __APPLE__
    if (!home || !*home) {
        fprintf(stderr, "orc: HOME is not set\n");
        return 1;
    }
    snprintf(profile, sizeof(profile), "%s/Library/Application Support/orc/profile", home);
#else
    const char *xdg = getenv("XDG_DATA_HOME");
    if (xdg && *xdg) {
        snprintf(profile, sizeof(profile), "%s/orc/profile", xdg);
    } else {
        if (!home || !*home) {
            fprintf(stderr, "orc: neither XDG_DATA_HOME nor HOME is set\n");
            return 1;
        }
        snprintf(profile, sizeof(profile), "%s/.local/share/orc/profile", home);
    }
#endif
    make_dirs(profile);

    /* Seed user.js on first run only - never overwrite the user's. */
    char userjs[PATH_MAX];
    join_path(userjs, sizeof(userjs), profile, "user.js");
    if (!file_exists(userjs) && file_exists(seed)) {
        copy_file(seed, userjs);
    }

    /* Launch: engine -profile <profile> <args...> */
    char **args = (char **)calloc((size_t)argc + 3, sizeof(char *));
    if (!args) {
        fprintf(stderr, "orc: out of memory\n");
        return 1;
    }
    args[0] = engine;
    args[1] = "-profile";
    args[2] = profile;
    for (int i = 1; i < argc; i++) args[2 + i] = argv[i];
    args[2 + argc] = NULL;

    execv(engine, args);
    fprintf(stderr, "orc: failed to launch the engine: %s\n", strerror(errno));
    return 1;
}

#endif
