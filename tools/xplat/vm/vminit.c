#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <fcntl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>

static int insmod(const char *path) {
    struct stat st;
    int fd = open(path, O_RDONLY);
    if (fd < 0 || fstat(fd, &st) != 0) return -1;
    void *buf = malloc(st.st_size);
    if (read(fd, buf, st.st_size) != st.st_size) return -1;
    close(fd);
    long r = syscall(SYS_init_module, buf, (unsigned long) st.st_size, "");
    free(buf);
    return (int) r;
}
static int cmp(const void *a, const void *b) { return strcmp(*(char **) a, *(char **) b); }

int main(void) {
    struct utsname u;
    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    uname(&u);
    printf("VMINIT kernel %s %s\n", u.release, u.machine);
    {
        DIR *d = opendir("/mods");
        char *names[64]; int n = 0, i;
        struct dirent *e;
        while (d && (e = readdir(d)) && n < 64) if (e->d_name[0] != '.') names[n++] = strdup(e->d_name);
        if (d) closedir(d);
        qsort(names, n, sizeof *names, cmp);
        for (i = 0; i < n; ++i) {
            char p[300]; snprintf(p, sizeof p, "/mods/%s", names[i]);
            printf("insmod %s -> %d\n", names[i], insmod(p));
        }
    }
    mkdir("/newroot", 0755);
    int r = mount("rootfs", "/newroot", "9p", MS_RDONLY, "trans=virtio,version=9p2000.L,msize=524288,cache=mmap");
    printf("mount rootfs: %d\n", r);
    if (r != 0) { perror("mount"); sync(); reboot(RB_POWER_OFF); }
     mkdir("/newroot/proc", 0755); mkdir("/newroot/sys", 0755); mkdir("/newroot/dev", 0755); mkdir("/newroot/tmp", 0755);
    printf("mount work: %d\n", mount("work", "/newroot/work", "9p", 0, "trans=virtio,version=9p2000.L,msize=524288,cache=mmap"));
    printf("mount iso: %d\n", mount("iso", "/newroot/mnt/c", "9p", MS_RDONLY, "trans=virtio,version=9p2000.L,msize=524288,cache=mmap"));
    mount("proc", "/newroot/proc", "proc", 0, NULL);
    mount("sysfs", "/newroot/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/newroot/dev", "devtmpfs", 0, NULL);
    mount("tmpfs", "/newroot/tmp", "tmpfs", 0, "size=3g");
    mkdir("/newroot/dev/shm", 0777);
    mount("tmpfs", "/newroot/dev/shm", "tmpfs", 0, "size=1g");
    if (chroot("/newroot") != 0 || chdir("/") != 0) { perror("chroot"); sync(); reboot(RB_POWER_OFF); }
    pid_t p = fork();
    if (p == 0) {
        char *envp[] = { "HOME=/root", "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "TERM=dumb", "LANG=C.UTF-8", NULL };
        char *argv[] = { "/bin/bash", "/work/vm_run.sh", NULL };
        execve("/bin/bash", argv, envp);
        perror("exec bash");
        _exit(127);
    }
    int st; waitpid(p, &st, 0);
    printf("VMINIT done status %d\n", WEXITSTATUS(st));
    sync();
    reboot(RB_POWER_OFF);
    return 0;
}
