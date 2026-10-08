/* Probe for gw_writewatch_linux.c: backend, correctness over random write patterns, and the cost of one
 * "frame" (write ~1500 pages, poll+reset). Exit 0 also when no backend exists (the game then runs in
 * full-copy mode); prints which. Run it on the target kernel: `writewatch-probe`. */
#define _GNU_SOURCE
#include "gw_compat_linux.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1e3 + t.tv_nsec / 1e6;
}

int main(void) {
    const size_t size = 40u * 1024 * 1024, npages = size / 4096;
    volatile unsigned char *m = (volatile unsigned char *) VirtualAlloc((void *) 0x80000000u, size,
                                                                         MEM_RESERVE | MEM_COMMIT | MEM_WRITE_WATCH, PAGE_READWRITE);
    PVOID *got;
    unsigned char *want;
    int frame, bad = 0;
    double t_write = 0, t_poll = 0;
    unsigned long total = 0;
    if (m == NULL) {
        printf("writewatch: no backend on this kernel (the game runs snapshots in full-copy mode)\n");
        return 0;
    }
    printf("writewatch: backend = %s\n", gw_linux_writewatch_name());
    for (size_t i = 0; i < npages; ++i) m[i * 4096] = 1; /* populate everything, like a running game */
    got = (PVOID *) malloc(npages * sizeof *got);
    want = (unsigned char *) malloc(npages);
    srand(12345);
    {
        ULONG_PTR c = npages;
        DWORD g;
        GetWriteWatch(WRITE_WATCH_FLAG_RESET, (PVOID) 0x80000000u, size, got, &c, &g);
    }
    for (frame = 0; frame < 600; ++frame) {
        ULONG_PTR c = npages;
        DWORD g;
        int n = 200 + rand() % 2600;
        double t0, t1, t2;
        t0 = now_ms();
        for (size_t i = 0; i < npages; ++i) want[i] = 0;
        for (int k = 0; k < n; ++k) {
            size_t p = (size_t) rand() % npages;
            m[p * 4096 + (size_t) (rand() % 4096)] = (unsigned char) frame;
            want[p] = 1;
        }
        t1 = now_ms();
        if (GetWriteWatch(WRITE_WATCH_FLAG_RESET, (PVOID) 0x80000000u, size, got, &c, &g) != 0) {
            printf("writewatch: GetWriteWatch failed at frame %d\n", frame);
            return 1;
        }
        t2 = now_ms();
        t_write += t1 - t0;
        t_poll += t2 - t1;
        total += c;
        {
            static unsigned char seen[10240];
            for (size_t i = 0; i < npages; ++i) seen[i] = 0;
            for (ULONG_PTR i = 0; i < c; ++i) seen[((uintptr_t) got[i] - 0x80000000u) / 4096] = 1;
            for (size_t i = 0; i < npages; ++i) {
                if (want[i] && !seen[i]) {
                    if (bad++ < 5) printf("writewatch: MISSED page %zu in frame %d\n", i, frame);
                }
            }
        }
    }
    printf("writewatch: 600 frames, avg %.0f dirty pages reported, poll+reset %.3f ms/frame (the writes themselves %.3f ms/frame), missed %d\n",
           total / 600.0, t_poll / 600, t_write / 600, bad);
    return bad != 0;
}
