/* orc workspace names are portable, bounded paths, never filesystem input.
 * A slash is the default workspace; named descendants are ASCII and folded
 * to lowercase so the same tree has the same identity on every OS. */
#ifndef ORC_WORKSPACE_H
#define ORC_WORKSPACE_H

#include <stdio.h>
#include <string.h>
#include <wchar.h>

#ifdef _WIN32
typedef wchar_t OrcChar;
#define ORC_TEXT(s) L##s
#define orc_strlen wcslen
#define orc_strcmp wcscmp
#else
typedef char OrcChar;
#define ORC_TEXT(s) s
#define orc_strlen strlen
#define orc_strcmp strcmp
#endif

#define ORC_MAX_DEPTH 16
#define ORC_MAX_SEGMENT 48
#define ORC_MAX_WORKSPACE (ORC_MAX_DEPTH * (ORC_MAX_SEGMENT + 1))

typedef struct {
    char name[ORC_MAX_WORKSPACE];
    unsigned depth;
    int info;
    int help;
} OrcWorkspace;

static int orc_reserved_segment(const char *s) {
    return !strcmp(s, "con") || !strcmp(s, "prn") || !strcmp(s, "aux") ||
           !strcmp(s, "nul") ||
           (strlen(s) == 4 &&
            (!strncmp(s, "com", 3) || !strncmp(s, "lpt", 3)) &&
            s[3] >= '0' && s[3] <= '9');
}

static int orc_workspace_set(OrcWorkspace *ws, const OrcChar *value) {
    OrcWorkspace next = {0};
    char segment[ORC_MAX_SEGMENT + 1];
    size_t pos = 0, len = 0;
    if (!value || !*value) return -1;
    if (!orc_strcmp(value, ORC_TEXT("/"))) {
        ws->name[0] = '\0';
        ws->depth = 0;
        return 0;
    }
    for (const OrcChar *p = value;; p++) {
        unsigned long c = (unsigned long)*p;
        if (!c || c == '/') {
            if (!len) return -1;
            segment[len] = '\0';
            if (orc_reserved_segment(segment) || ++next.depth > ORC_MAX_DEPTH)
                return -1;
            if (pos) next.name[pos++] = '/';
            memcpy(next.name + pos, segment, len);
            pos += len;
            next.name[pos] = '\0';
            len = 0;
            if (!c) break;
            continue;
        }
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
              (len && (c == '-' || c == '_'))) || len >= ORC_MAX_SEGMENT)
            return -1;
        segment[len++] = (char)c;
    }
    memcpy(ws->name, next.name, sizeof(ws->name));
    ws->depth = next.depth;
    return 0;
}

static int orc_workspace_child(OrcWorkspace *ws, const OrcChar *value) {
    OrcWorkspace child = {0};
    OrcChar combined[ORC_MAX_WORKSPACE];
    if (orc_workspace_set(&child, value) || child.depth != 1 ||
        ws->depth >= ORC_MAX_DEPTH) return -1;
    size_t pos = strlen(ws->name);
    for (size_t i = 0; i < pos; i++) combined[i] = (OrcChar)ws->name[i];
    if (pos) combined[pos++] = '/';
    for (size_t i = 0; child.name[i]; i++) combined[pos++] = (OrcChar)child.name[i];
    combined[pos] = 0;
    return orc_workspace_set(ws, combined);
}

static void orc_workspace_parent(OrcWorkspace *ws) {
    char *slash = strrchr(ws->name, '/');
    if (slash) *slash = '\0';
    else ws->name[0] = '\0';
    if (ws->depth) ws->depth--;
}

/* Gecko accepts profile selectors in several spellings. They must not
 * override the profile selected by orc, even after a -- separator. */
static int orc_profile_option(const OrcChar *arg) {
    char option[32];
    size_t len = 0;
    if (*arg == '-') {
        arg++;
        if (*arg == '-') arg++;
    }
#ifdef _WIN32
    else if (*arg == '/') arg++;
#endif
    else return 0;
    while (*arg && *arg != '=' && len < sizeof(option) - 1) {
        unsigned long c = (unsigned long)*arg++;
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
        option[len++] = c < 128 ? (char)c : '?';
    }
    option[len] = '\0';
    return !strcmp(option, "profile") || !strcmp(option, "p") ||
           !strcmp(option, "profilemanager") || !strcmp(option, "createprofile");
}

/* Consume only orc's options. All other arguments keep their exact bytes
 * (UTF-16 on Windows) and ordering. Return the compacted argc, or -1. */
static int orc_workspace_parse(int argc, OrcChar **argv, const OrcChar *inherited,
                               OrcWorkspace *ws) {
    int out = 1, literal = 0, explicit_workspace = 0;
    for (int i = 1; i < argc; i++)
        if (!orc_strcmp(argv[i], ORC_TEXT("--"))) break;
        else if (!orc_strcmp(argv[i], ORC_TEXT("--orc-workspace"))) {
            explicit_workspace = 1;
            break;
        }
    if (!explicit_workspace && inherited && *inherited &&
        orc_workspace_set(ws, inherited)) {
        fprintf(stderr, "orc: invalid ORC_WORKSPACE; select a workspace explicitly to reset it\n");
        return -1;
    }
    for (int i = 1; i < argc; i++) {
        if (orc_profile_option(argv[i])) {
            fprintf(stderr, "orc: engine profile selectors are reserved; use --orc-workspace\n");
            return -1;
        }
        if (!orc_strcmp(argv[i], ORC_TEXT("--"))) literal = 1;
        if (!literal && !orc_strcmp(argv[i], ORC_TEXT("--orc-workspace"))) {
            if (++i >= argc || orc_workspace_set(ws, argv[i])) goto invalid;
        } else if (!literal && !orc_strcmp(argv[i], ORC_TEXT("--orc-child"))) {
            if (++i >= argc || orc_workspace_child(ws, argv[i])) goto invalid;
        } else if (!literal && !orc_strcmp(argv[i], ORC_TEXT("--orc-parent"))) {
            orc_workspace_parent(ws);
        } else if (!literal && !orc_strcmp(argv[i], ORC_TEXT("--orc-workspace-info"))) {
            ws->info = 1;
        } else if (!literal && !orc_strcmp(argv[i], ORC_TEXT("--orc-help"))) {
            ws->help = 1;
        } else {
            if (!literal) {
                const OrcChar *prefix = ORC_TEXT("--orc-");
                size_t j = 0;
                while (prefix[j] && argv[i][j] == prefix[j]) j++;
                if (!prefix[j]) {
                    fprintf(stderr, "orc: unknown orc option; see --orc-help\n");
                    return -1;
                }
            }
            argv[out++] = argv[i];
        }
    }
    argv[out] = NULL;
    return out;
invalid:
    fprintf(stderr, "orc: invalid workspace: use / or slash-separated names "
                    "(letters/digits, then letters/digits/-/_, at most %d characters "
                    "per name and %d levels; device names are reserved)\n",
                    ORC_MAX_SEGMENT, ORC_MAX_DEPTH);
    return -1;
}

#endif
