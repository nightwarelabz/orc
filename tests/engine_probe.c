/* Test engine: report the exact argv/environment received from the launcher. */
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#define probe_main wmain
#define probe_env _wgetenv
#define P(s) L##s
typedef wchar_t ProbeChar;
#else
#define probe_main main
#define probe_env getenv
#define P(s) s
typedef char ProbeChar;
#endif

static void string(FILE *out, const ProbeChar *value) {
#ifdef _WIN32
    char converted[131072];
    if (!WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value, -1,
                             converted, (int)sizeof(converted), NULL, NULL)) exit(5);
    const unsigned char *p = (const unsigned char *)converted;
#else
    const unsigned char *p = (const unsigned char *)value;
#endif
    fputc('"', out);
    for (; *p; p++) {
        if (*p == '"' || *p == '\\') { fputc('\\', out); fputc(*p, out); }
        else if (*p < 32) fprintf(out, "\\u%04x", *p);
        else fputc(*p, out);
    }
    fputc('"', out);
}

int probe_main(int argc, ProbeChar **argv) {
    const ProbeChar *capture = probe_env(P("ORC_TEST_CAPTURE"));
    if (!capture) return 3;
#ifdef _WIN32
    FILE *out = _wfopen(capture, L"wb");
#else
    FILE *out = fopen(capture, "wb");
#endif
    if (!out) return 4;
    fprintf(out, "{\"argv\":[");
    for (int i = 0; i < argc; i++) {
        if (i) fputc(',', out);
        string(out, argv[i]);
    }
    fprintf(out, "],\"workspace\":");
    const ProbeChar *name = probe_env(P("ORC_WORKSPACE"));
    string(out, name ? name : P(""));
    fprintf(out, ",\"depth\":");
    const ProbeChar *depth = probe_env(P("ORC_WORKSPACE_DEPTH"));
    string(out, depth ? depth : P(""));
    fprintf(out, "}\n");
    return fclose(out) ? 6 : 0;
}
