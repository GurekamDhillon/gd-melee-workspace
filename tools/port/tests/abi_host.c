#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern uint64_t gw_abi_mixed(uint32_t, uint64_t, float, double, uint32_t);
extern uint64_t gw_abi_callback(uint32_t, uint64_t, float, double, uint32_t);
extern double gw_abi_float(float, double, int);
extern uint64_t gw_abi_divide(int64_t, int64_t);
extern uint32_t gw_abi_layout(void);
extern uint64_t gw_abi_shared(void *);
extern uint32_t gw_abi_stack(uint32_t);
uint64_t gw_host_mixed(uint32_t a, uint64_t b, float c, double d, uint32_t e) {
    assert(a == 17 && b == UINT64_C(0x1234567887654321) && c == 1.25f && d == 2.5 && e == 31);
    return a + b + (uint64_t)(c * 4) + (uint64_t)(d * 8) + e;
}
int main(void) {
    const uint64_t big = UINT64_C(0x1234567887654321);
    for (int i = 0; i < 1000; ++i) {
        assert(gw_abi_mixed(17, big, 1.25f, 2.5, 31) == big + 73);
        assert(gw_abi_callback(17, big, 1.25f, 2.5, 31) == big + 73);
        assert(gw_abi_float(1.25f, 2.5, 3) == 6.75);
    }
    assert(gw_abi_divide(-INT64_C(9000000000), 3) == (uint64_t)-INT64_C(3000000000));
    assert(gw_abi_layout() == 24 * 256 + 8);
    unsigned char storage[24] __attribute__((aligned(8))) = {3};
    uint64_t value = __builtin_bswap64(big);
    double weight = 7.0;
    uint64_t bits;
    memcpy(&bits, &weight, 8); bits = __builtin_bswap64(bits);
    memcpy(storage + 8, &value, 8); memcpy(storage + 16, &bits, 8);
    assert(gw_abi_shared(storage) == big + 10);
    assert(gw_abi_stack(5) == 2057);
    puts("PASS: Linux mixed arguments, callbacks, float/i64 returns, guest aggregate storage, stack and division");
}
