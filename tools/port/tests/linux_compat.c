#define _GNU_SOURCE
#include "gw_compat_linux.h"
#include <assert.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <string.h>
#include <stdio.h>
static CRITICAL_SECTION recursive;
static SRWLOCK srw=SRWLOCK_INIT;
static INIT_ONCE outer=INIT_ONCE_STATIC_INIT, inner=INIT_ONCE_STATIC_INIT;
static int count, init_count;
static BOOL initialize_inner(PINIT_ONCE once,void *arg,void **result) { (void)once;(void)arg; ++init_count; *result=&count; return TRUE; }
static BOOL initialize_outer(PINIT_ONCE once,void *arg,void **result) { (void)once;(void)arg; return InitOnceExecuteOnce(&inner,initialize_inner,NULL,result); }
static DWORD worker(void *arg) {
    (void)arg;
    void *result=NULL;
    assert(InitOnceExecuteOnce(&outer,initialize_outer,NULL,&result) && result==&count);
    for(int i=0;i<5000;++i) { AcquireSRWLockExclusive(&srw); ++count; ReleaseSRWLockExclusive(&srw); }
    return 0;
}
static int destination(int a,int b) { return a+3*b; }
static uintptr_t trap_address;
static uintptr_t resolve(uintptr_t address) { return address==trap_address ? (uintptr_t)destination : 0; }
int main(void) {
    InitializeCriticalSection(&recursive);
    EnterCriticalSection(&recursive); EnterCriticalSection(&recursive);
    LeaveCriticalSection(&recursive); LeaveCriticalSection(&recursive); DeleteCriticalSection(&recursive);
    HANDLE threads[8];
    for(int i=0;i<8;++i) { threads[i]=CreateThread(NULL,0,worker,NULL,0,NULL); assert(threads[i]); }
    for(int i=0;i<8;++i) { assert(WaitForSingleObject(threads[i],5000)==WAIT_OBJECT_0); assert(CloseHandle(threads[i])); }
    assert(count==40000 && init_count==1);
    HANDLE timer=CreateWaitableTimerExW(NULL,NULL,0,0);
    LARGE_INTEGER due={.QuadPart=-200000};
    assert(timer && SetWaitableTimer(timer,&due,0,NULL,NULL,FALSE));
    assert(WaitForSingleObject(timer,0)==WAIT_TIMEOUT);
    assert(WaitForSingleObject(timer,1000)==WAIT_OBJECT_0); assert(CloseHandle(timer));
    char path[1024]; char *part;
    assert(GetFullPathNameA("/tmp/not-created/sub/../file",sizeof path,path,&part));
    assert(!strcmp(path,"/tmp/not-created/file") && !strcmp(part,"file"));
    unsigned char *mapped=VirtualAlloc(NULL,4096,MEM_COMMIT,PAGE_READWRITE);
    assert(mapped); mapped[0]=0xa5;
    assert(!VirtualAlloc(mapped,4096,MEM_COMMIT,PAGE_READWRITE) && mapped[0]==0xa5);
    assert(gw_linux_install_signals());
    trap_address=(uintptr_t)mapped;
    gw_linux_set_exec_resolver(resolve);
    assert(((int(*)(int,int))mapped)(5,7)==26);
    pid_t child=fork(); assert(child>=0);
    if(!child) {
        struct rlimit limit={0,0}; setrlimit(RLIMIT_CORE,&limit);
        mprotect(mapped,4096,PROT_NONE);
        *(volatile unsigned char *)mapped=0; /* Data fault must never be routed as execution. */
        _exit(99);
    }
    int status; assert(waitpid(child,&status,0)==child);
    assert(WIFSIGNALED(status) && WTERMSIG(status)==SIGSEGV);
    munmap(mapped,4096);
    puts("PASS: recursive/once/SRW synchronization, threads, timers, paths, safe mapping and execution-only traps");
}
