/* Windows CreateProcessW takes a command line, not argv. Encode each
 * argument using the Microsoft CRT rules, including trailing backslashes.
 * Kept independent of windows.h so the encoder can be checked on any OS. */
#ifndef ORC_WINDOWS_COMMAND_LINE_H
#define ORC_WINDOWS_COMMAND_LINE_H
#include <stddef.h>
#include <wchar.h>

static int orc_command_arg(wchar_t *buf, size_t cap, const wchar_t *arg) {
    size_t used = wcslen(buf), needed = 2, slashes = 0;
    for (const wchar_t *p = arg;; p++) {
        if (*p == L'\\') { slashes++; continue; }
        needed += slashes * ((*p == L'"' || !*p) ? 2 : 1);
        slashes = 0;
        if (!*p) break;
        needed += *p == L'"' ? 2 : 1;
    }
    if (used) needed++; /* separator */
    if (used >= cap || needed >= cap - used) return -1;
    size_t pos = used;
    if (pos) buf[pos++] = L' ';
    buf[pos++] = L'"';
    for (const wchar_t *p = arg;; p++) {
        if (*p == L'\\') { slashes++; continue; }
        size_t count = slashes * ((*p == L'"' || !*p) ? 2 : 1);
        while (count--) buf[pos++] = L'\\';
        slashes = 0;
        if (!*p) break;
        if (*p == L'"') buf[pos++] = L'\\';
        buf[pos++] = *p;
    }
    buf[pos++] = L'"';
    buf[pos] = L'\0';
    return 0;
}
#endif
