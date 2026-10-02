typedef unsigned int u32;
typedef unsigned long long u64;
struct shared { char marker; u64 value; double weight; };
extern u64 host_mixed(u32, u64, float, double, u32);
u64 abi_mixed(u32 a, u64 b, float c, double d, u32 e) {
    return (u64)a + b + (u64)(c * 4) + (u64)(d * 8) + e;
}
u64 abi_callback(u32 a, u64 b, float c, double d, u32 e) {
    return host_mixed(a, b, c, d, e);
}
double abi_float(float a, double b, int c) { return a + b + c; }
u64 abi_divide(long long a, long long b) { return a / b; }
u32 abi_layout(void) { return sizeof(struct shared) * 256 + __builtin_offsetof(struct shared, value); }
u64 abi_shared(struct shared *p) { return p->marker + p->value + (u64)p->weight; }
u32 abi_stack(u32 seed) {
    volatile u32 storage[2048];
    for (u32 i = 0; i < 2048; ++i) storage[i] = seed + i;
    return storage[0] + storage[2047];
}
