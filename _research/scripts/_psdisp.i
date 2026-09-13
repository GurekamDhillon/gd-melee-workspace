# 1 "src/sysdolphin/baselib/psdisp.c"
# 1 "<built-in>" 1
# 1 "<built-in>" 3
# 377 "<built-in>" 3
# 1 "<command line>" 1
# 1 "<built-in>" 2
# 1 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\psdisp.h" 1



# 1 "src\\Runtime/platform.h" 1



# 1 "src/MSL\\stdbool.h" 1 3





typedef int bool;
# 5 "src\\Runtime/platform.h" 2
# 1 "src/MSL\\stddef.h" 1 3



typedef unsigned short wchar_t;

typedef unsigned long size_t;

typedef signed int intptr_t;
typedef unsigned int uintptr_t;
# 6 "src\\Runtime/platform.h" 2

# 1 "extern/dolphin/include\\dolphin/types.h" 1 3



typedef signed char s8;
typedef unsigned char u8;
typedef signed short int s16;
typedef unsigned short int u16;
typedef signed long s32;
typedef unsigned long u32;
typedef signed long long int s64;
typedef unsigned long long int u64;

typedef float f32;
typedef double f64;
typedef volatile f32 vf32;
typedef volatile f64 vf64;

typedef char* Ptr;

typedef int BOOL;
# 35 "extern/dolphin/include\\dolphin/types.h" 3
# 1 "extern/dolphin/include\\cmath.h" 1 3



f32 powf(f32 x, f32 y);
f32 tanf(f32);
# 36 "extern/dolphin/include\\dolphin/types.h" 2 3

# 1 "src/MSL\\ctype.h" 1 3



extern const unsigned char __ctype_map[];
extern const unsigned char __lower_map[];
extern const unsigned char __upper_map[];
# 26 "src/MSL\\ctype.h" 3
static inline int isalpha(int c)
{
    return (int) (__ctype_map[(unsigned char) c] & (0x40 | 0x80));
}
static inline int isdigit(int c)
{
    return (int) (__ctype_map[(unsigned char) c] & 0x10);
}
static inline int isspace(int c)
{
    return (int) (__ctype_map[(unsigned char) c] & (0x02 | 0x04));
}
static inline int isupper(int c)
{
    return (int) (__ctype_map[(unsigned char) c] & 0x80);
}
static inline int isxdigit(int c)
{
    return (int) (__ctype_map[(unsigned char) c] & 0x20);
}

int toupper(int c);
int tolower(int c);
# 38 "extern/dolphin/include\\dolphin/types.h" 2 3
# 1 "src/MSL\\stdarg.h" 1 3



typedef struct {
    char gpr;
    char fpr;
    char reserved[2];
    char* input_arg_area;
    char* reg_save_area;
} __va_list[1];
typedef __va_list va_list;

extern void __builtin_va_info(void*);

void* __va_arg(va_list v_list, unsigned char type);
# 39 "extern/dolphin/include\\dolphin/types.h" 2 3
# 1 "src/MSL\\stdio.h" 1 3
# 13 "src/MSL\\stdio.h" 3
typedef unsigned long __file_handle;
typedef unsigned long fpos_t;





enum __io_modes {
    __read = 1,
    __write = 2,
    __read_write = 3,
    __append = 4,
};
enum __file_kinds {
    __closed_file,
    __disk_file,
    __console_file,
    __unavailable_file,
};
enum __file_orientation {
    __unoriented,
    __char_oriented,
    __wide_oriented,
};

enum __io_results {
    __no_io_error,
    __io_error,
    __io_EOF,
};

typedef struct {
    unsigned int open_mode : 2;
    unsigned int io_mode : 3;
    unsigned int buffer_mode : 2;
    unsigned int file_kind : 3;
    unsigned int file_orientation : 2;
    unsigned int binary_io : 1;
} __file_modes;

enum __io_states {
    __neutral,
    __writing,
    __reading,
    __rereading,
};

typedef struct {
    unsigned int io_state : 3;
    unsigned int free_buffer : 1;
    unsigned char eof;
    unsigned char error;
} __file_state;

typedef void (*__idle_proc)(void);
typedef int (*__pos_proc)(__file_handle file, fpos_t* position, int mode,
                          __idle_proc idle_proc);
typedef int (*__io_proc)(__file_handle file, unsigned char* buff,
                         size_t* count, __idle_proc idle_proc);
typedef int (*__close_proc)(__file_handle file);

typedef struct _IO_FILE {
    __file_handle handle;
    __file_modes mode;
    __file_state state;
    unsigned char char_buffer;
    unsigned char char_buffer_overflow;
    unsigned char ungetc_buffer[2];
    wchar_t ungetwc_buffer[2];
    unsigned long position;
    unsigned char* buffer;
    unsigned long buffer_size;
    unsigned char* buffer_ptr;
    unsigned long buffer_len;
    unsigned long buffer_alignment;
    unsigned long saved_buffer_len;
    unsigned long buffer_pos;
    __pos_proc position_proc;
    __io_proc read_proc;
    __io_proc write_proc;
    __close_proc close_proc;
    __idle_proc idle_proc;
} FILE;

typedef struct {
    char* CharStr;
    size_t MaxCharCount;
    size_t CharsWritten;
} __OutStrCtrl;

typedef struct {
    char* NextChar;
    int NullCharDetected;
} __InStrCtrl;



enum __ReadProcActions {
    __GetAChar,
    __UngetAChar,
    __TestForError,
};

int __StringRead(void* str, int ch, int behavior);





extern FILE __files[3];





int printf(const char* format, ...);
int sprintf(char* s, const char* format, ...);
int vprintf(const char* format, va_list arg);
int vsprintf(char* s, const char* format, va_list arg);

size_t fwrite(const void*, size_t memb_size, size_t num_memb, FILE*);
# 40 "extern/dolphin/include\\dolphin/types.h" 2 3
# 1 "src/MSL\\string.h" 1 3





char* strcpy(char* dst, const char* src);
char* strncpy(char* dst, const char* src, size_t num);
char* strcat(char* dest, const char* src);
size_t strlen(const char* s);
int strcmp(const char* s1, const char* s2);
int strncmp(const char* s1, const char* s2, size_t n);
char* strchr(const char* str, int chr);

void* memchr(const void* p, int val, size_t n);
int memcmp(const void* p1, const void* p2, size_t n);
void* memset(void* dst, int val, size_t n);
void* memcpy(void* dst, const void* src, size_t n);
void* memmove(void* dst, const void* src, size_t n);
# 41 "extern/dolphin/include\\dolphin/types.h" 2 3
# 8 "src\\Runtime/platform.h" 2
# 28 "src\\Runtime/platform.h"
typedef int enum_t;


typedef signed int ssize_t;


typedef void (*Event)(void);

typedef bool (*Predicate)(void);
# 5 "src/sysdolphin/baselib\\psdisp.h" 2

# 1 "src\\sysdolphin/baselib/forward.h" 1





typedef struct GObjFuncs GObjFuncs;
typedef struct HSD_AnimJoint HSD_AnimJoint;
typedef struct HSD_AObj HSD_AObj;
typedef struct HSD_AObjDesc HSD_AObjDesc;
typedef struct HSD_Archive HSD_Archive;
typedef struct HSD_ArchiveExternInfo HSD_ArchiveExternInfo;
typedef struct HSD_ArchiveHeader HSD_ArchiveHeader;
typedef struct HSD_ArchivePublicInfo HSD_ArchivePublicInfo;
typedef struct HSD_ArchiveRelocationInfo HSD_ArchiveRelocationInfo;
typedef struct HSD_ByteCodeExpDesc HSD_ByteCodeExpDesc;
typedef struct HSD_CameraAnim HSD_CameraAnim;
typedef struct HSD_CameraDescCommon HSD_CameraDescCommon;
typedef struct HSD_CameraDescFrustum HSD_CameraDescFrustum;
typedef struct HSD_CameraDescPerspective HSD_CameraDescPerspective;
typedef struct HSD_CObj HSD_CObj;
typedef struct HSD_CObjInfo HSD_CObjInfo;
typedef struct HSD_DevCom HSD_DevCom;
typedef struct HSD_DObj HSD_DObj;
typedef struct HSD_DObjDesc HSD_DObjDesc;
typedef struct HSD_DObjInfo HSD_DObjInfo;
typedef struct HSD_Envelope HSD_Envelope;
typedef struct HSD_EnvelopeDesc HSD_EnvelopeDesc;
typedef struct HSD_Exp HSD_Exp;
typedef struct HSD_ExpDesc HSD_ExpDesc;
typedef struct HSD_FObj HSD_FObj;
typedef struct HSD_Fog HSD_Fog;
typedef struct HSD_FogAdj HSD_FogAdj;
typedef struct HSD_FogAdjDesc HSD_FogAdjDesc;
typedef struct HSD_FogAdjInfo HSD_FogAdjInfo;
typedef struct HSD_FogDesc HSD_FogDesc;
typedef struct HSD_FogInfo HSD_FogInfo;
typedef struct HSD_Generator HSD_Generator;
typedef struct HSD_GObj HSD_GObj;
typedef struct HSD_GObjProc HSD_GObjProc;
typedef struct HSD_Hash HSD_Hash;
typedef struct HSD_HashEntry HSD_HashEntry;
typedef struct HSD_IKHint HSD_IKHint;
typedef struct HSD_IKHintDesc HSD_IKHintDesc;
typedef struct HSD_ImageDesc HSD_ImageDesc;
typedef struct HSD_JObj HSD_JObj;
typedef struct HSD_Joint HSD_Joint;
typedef struct HSD_LightAnim HSD_LightAnim;
typedef struct HSD_LightAttn HSD_LightAttn;
typedef struct HSD_LightDesc HSD_LightDesc;
typedef struct HSD_LightPoint HSD_LightPoint;
typedef struct HSD_LightPointDesc HSD_LightPointDesc;
typedef struct HSD_LightSpot HSD_LightSpot;
typedef struct HSD_LightSpotDesc HSD_LightSpotDesc;
typedef struct HSD_LObj HSD_LObj;
typedef struct HSD_LObjInfo HSD_LObjInfo;
typedef struct HSD_MatAnimJoint HSD_MatAnimJoint;
typedef struct HSD_Material HSD_Material;
typedef struct HSD_MObj HSD_MObj;
typedef struct HSD_MObjInfo HSD_MObjInfo;
typedef struct HSD_Obj HSD_Obj;
typedef struct HSD_PadData HSD_PadData;
typedef struct HSD_PadRumbleListData HSD_PadRumbleListData;
typedef struct HSD_PadStatus HSD_PadStatus;
typedef struct HSD_Particle HSD_Particle;
typedef struct HSD_PEDesc HSD_PEDesc;
typedef struct HSD_PObj HSD_PObj;
typedef struct HSD_PObjDesc HSD_PObjDesc;
typedef struct HSD_PObjInfo HSD_PObjInfo;
typedef struct HSD_psAppSRT HSD_psAppSRT;
typedef struct HSD_RObj HSD_RObj;
typedef struct HSD_RObjAnimJoint HSD_RObjAnimJoint;
typedef struct HSD_RObjDesc HSD_RObjDesc;
typedef struct HSD_RumbleData HSD_RumbleData;
typedef struct HSD_Rvalue HSD_Rvalue;
typedef struct HSD_RvalueList HSD_RvalueList;
typedef struct HSD_Shadow HSD_Shadow;
typedef struct HSD_ShapeAnim HSD_ShapeAnim;
typedef struct HSD_ShapeAnimDObj HSD_ShapeAnimDObj;
typedef struct HSD_ShapeAnimJoint HSD_ShapeAnimJoint;
typedef struct HSD_ShapeSet HSD_ShapeSet;
typedef struct HSD_ShapeSetDesc HSD_ShapeSetDesc;
typedef struct HSD_SM HSD_SM;
typedef struct HSD_SObj HSD_SObj;
typedef struct HSD_TExpDag HSD_TExpDag;
typedef struct HSD_TExpRes HSD_TExpRes;
typedef struct HSD_Text HSD_Text;
typedef struct HSD_TObj HSD_TObj;
typedef struct HSD_ViewingRect HSD_ViewingRect;
typedef struct HSD_VtxDescList HSD_VtxDescList;
typedef struct HSD_WObj HSD_WObj;
typedef struct HSD_WObjAnim HSD_WObjAnim;
typedef struct HSD_WObjDesc HSD_WObjDesc;
typedef struct HSD_WObjInfo HSD_WObjInfo;
typedef struct PadLibData PadLibData;
typedef struct RumbleCommand RumbleCommand;
typedef struct RumbleInfo RumbleInfo;
typedef struct SisBlock SisBlock;
typedef struct sislib_UnkAlloc3 sislib_UnkAlloc3;
typedef struct TextKerning TextKerning;
typedef union HSD_CObjDesc HSD_CObjDesc;
typedef union HSD_ObjData HSD_ObjData;
typedef union HSD_Rumble HSD_Rumble;
typedef union HSD_TExp HSD_TExp;

typedef void (*GObj_RenderFunc)(HSD_GObj* gobj, int code);
typedef void (*HSD_ObjUpdateFunc)(void* obj, enum_t type, HSD_ObjData* fval);
typedef void (*HSD_DevComCallback)(int, int, void*, bool cancelflag);
typedef void (*HSD_GObjEvent)(HSD_GObj* gobj);
typedef void (*HSD_UserDataEvent)(void* user_data);
typedef bool (*HSD_GObjPredicate)(HSD_GObj* gobj);
typedef void (*HSD_GObjInteraction)(HSD_GObj* gobj0, HSD_GObj* gobj1);
typedef void (*HSD_MObjSetupFunc)(HSD_MObj* mobj, u32 rendermode);
# 131 "src\\sysdolphin/baselib/forward.h"
typedef enum PObjSetupFlag {
    SETUP_NORMAL = 1,
    SETUP_REFLECTION = 2,
    SETUP_HIGHLIGHT = 4,
    SETUP_NORMAL_PROJECTION = 6,
    SETUP_JOINT0 = 1,
    SETUP_JOINT1 = 2,
    SETUP_NONE = 0
} PObjSetupFlag;

typedef enum HSD_TrspMask {
    HSD_TRSP_OPA = 1,
    HSD_TRSP_XLU = 2,
    HSD_TRSP_TEXEDGE = 4,
    HSD_TRSP_ALL = 7,
} HSD_TrspMask;
# 7 "src/sysdolphin/baselib\\psdisp.h" 2

void psDispParticles(u32 target_link, u32 sw);
HSD_Particle* particleSort(s32, u8, HSD_Particle**, HSD_Particle**);
void setVtxDesc(s32);
# 2 "src/sysdolphin/baselib/psdisp.c" 2



# 1 "src/sysdolphin/baselib\\cobj.h" 1







# 1 "extern/dolphin/include\\dolphin/gx/GXEnum.h" 1 3





typedef u8 GXBool;







typedef enum _GXProjectionType
{
    GX_PERSPECTIVE,
    GX_ORTHOGRAPHIC,
} GXProjectionType;

typedef enum _GXCompare
{
    GX_NEVER,
    GX_LESS,
    GX_EQUAL,
    GX_LEQUAL,
    GX_GREATER,
    GX_NEQUAL,
    GX_GEQUAL,
    GX_ALWAYS,
} GXCompare;

typedef enum _GXAlphaOp
{
    GX_AOP_AND,
    GX_AOP_OR,
    GX_AOP_XOR,
    GX_AOP_XNOR,
    GX_MAX_ALPHAOP,
} GXAlphaOp;

typedef enum _GXZFmt16
{
    GX_ZC_LINEAR,
    GX_ZC_NEAR,
    GX_ZC_MID,
    GX_ZC_FAR,
} GXZFmt16;

typedef enum _GXGamma
{
    GX_GM_1_0,
    GX_GM_1_7,
    GX_GM_2_2,
} GXGamma;

typedef enum _GXPixelFmt
{
    GX_PF_RGB8_Z24,
    GX_PF_RGBA6_Z24,
    GX_PF_RGB565_Z16,
    GX_PF_Z24,
    GX_PF_Y8,
    GX_PF_U8,
    GX_PF_V8,
    GX_PF_YUV420,
} GXPixelFmt;

typedef enum _GXPrimitive
{
    GX_QUADS = 0x80,
    GX_TRIANGLES = 0x90,
    GX_TRIANGLESTRIP = 0x98,
    GX_TRIANGLEFAN = 0xA0,
    GX_LINES = 0xA8,
    GX_LINESTRIP = 0xB0,
    GX_POINTS = 0xB8,
} GXPrimitive;

typedef enum _GXVtxFmt
{
    GX_VTXFMT0,
    GX_VTXFMT1,
    GX_VTXFMT2,
    GX_VTXFMT3,
    GX_VTXFMT4,
    GX_VTXFMT5,
    GX_VTXFMT6,
    GX_VTXFMT7,
    GX_MAX_VTXFMT,
} GXVtxFmt;

typedef enum _GXAttr
{
    GX_VA_PNMTXIDX,
    GX_VA_TEX0MTXIDX,
    GX_VA_TEX1MTXIDX,
    GX_VA_TEX2MTXIDX,
    GX_VA_TEX3MTXIDX,
    GX_VA_TEX4MTXIDX,
    GX_VA_TEX5MTXIDX,
    GX_VA_TEX6MTXIDX,
    GX_VA_TEX7MTXIDX,
    GX_VA_POS,
    GX_VA_NRM,
    GX_VA_CLR0,
    GX_VA_CLR1,
    GX_VA_TEX0,
    GX_VA_TEX1,
    GX_VA_TEX2,
    GX_VA_TEX3,
    GX_VA_TEX4,
    GX_VA_TEX5,
    GX_VA_TEX6,
    GX_VA_TEX7,
    GX_POS_MTX_ARRAY,
    GX_NRM_MTX_ARRAY,
    GX_TEX_MTX_ARRAY,
    GX_LIGHT_ARRAY,
    GX_VA_NBT,
    GX_VA_MAX_ATTR,
    GX_VA_NULL = 0xFF,
} GXAttr;

typedef enum _GXAttrType
{
    GX_NONE,
    GX_DIRECT,
    GX_INDEX8,
    GX_INDEX16,
} GXAttrType;




typedef enum _GXTexFmt
{
    GX_TF_I4 = 0x0,
    GX_TF_I8 = 0x1,
    GX_TF_IA4 = 0x2,
    GX_TF_IA8 = 0x3,
    GX_TF_RGB565 = 0x4,
    GX_TF_RGB5A3 = 0x5,
    GX_TF_RGBA8 = 0x6,
    GX_TF_CMPR = 0xE,

    GX_CTF_R4 = 0x0 | 0x20,
    GX_CTF_RA4 = 0x2 | 0x20,
    GX_CTF_RA8 = 0x3 | 0x20,
    GX_CTF_YUVA8 = 0x6 | 0x20,
    GX_CTF_A8 = 0x7 | 0x20,
    GX_CTF_R8 = 0x8 | 0x20,
    GX_CTF_G8 = 0x9 | 0x20,
    GX_CTF_B8 = 0xA | 0x20,
    GX_CTF_RG8 = 0xB | 0x20,
    GX_CTF_GB8 = 0xC | 0x20,

    GX_TF_Z8 = 0x1 | 0x10,
    GX_TF_Z16 = 0x3 | 0x10,
    GX_TF_Z24X8 = 0x6 | 0x10,

    GX_CTF_Z4 = 0x0 | 0x10 | 0x20,
    GX_CTF_Z8M = 0x9 | 0x10 | 0x20,
    GX_CTF_Z8L = 0xA | 0x10 | 0x20,
    GX_CTF_Z16L = 0xC | 0x10 | 0x20,

    GX_TF_A8 = GX_CTF_A8,

    GX_TF_C4 = 0x8,
    GX_TF_C8 = 0x9,
    GX_TF_C14X2 = 0xA,
} GXTexFmt;

typedef enum _GXTexWrapMode
{
    GX_CLAMP,
    GX_REPEAT,
    GX_MIRROR,
    GX_MAX_TEXWRAPMODE,
} GXTexWrapMode;

typedef enum _GXTexFilter
{
    GX_NEAR,
    GX_LINEAR,
    GX_NEAR_MIP_NEAR,
    GX_LIN_MIP_NEAR,
    GX_NEAR_MIP_LIN,
    GX_LIN_MIP_LIN,
} GXTexFilter;

typedef enum _GXAnisotropy
{
    GX_ANISO_1,
    GX_ANISO_2,
    GX_ANISO_4,
    GX_MAX_ANISOTROPY,
} GXAnisotropy;

typedef enum _GXTexMapID
{
    GX_TEXMAP0,
    GX_TEXMAP1,
    GX_TEXMAP2,
    GX_TEXMAP3,
    GX_TEXMAP4,
    GX_TEXMAP5,
    GX_TEXMAP6,
    GX_TEXMAP7,
    GX_MAX_TEXMAP,
    GX_TEXMAP_NULL = 0xFF,
    GX_TEX_DISABLE = 0x100,
} GXTexMapID;

typedef enum _GXTexCoordID
{
    GX_TEXCOORD0,
    GX_TEXCOORD1,
    GX_TEXCOORD2,
    GX_TEXCOORD3,
    GX_TEXCOORD4,
    GX_TEXCOORD5,
    GX_TEXCOORD6,
    GX_TEXCOORD7,
    GX_MAX_TEXCOORD,
    GX_TEXCOORD_NULL = 0xFF,
} GXTexCoordID;

typedef enum _GXTevStageID
{
    GX_TEVSTAGE0,
    GX_TEVSTAGE1,
    GX_TEVSTAGE2,
    GX_TEVSTAGE3,
    GX_TEVSTAGE4,
    GX_TEVSTAGE5,
    GX_TEVSTAGE6,
    GX_TEVSTAGE7,
    GX_TEVSTAGE8,
    GX_TEVSTAGE9,
    GX_TEVSTAGE10,
    GX_TEVSTAGE11,
    GX_TEVSTAGE12,
    GX_TEVSTAGE13,
    GX_TEVSTAGE14,
    GX_TEVSTAGE15,
    GX_MAX_TEVSTAGE,
} GXTevStageID;

typedef enum _GXTevMode
{
    GX_MODULATE,
    GX_DECAL,
    GX_BLEND,
    GX_REPLACE,
    GX_PASSCLR,
} GXTevMode;

typedef enum _GXTexMtxType
{
    GX_MTX3x4,
    GX_MTX2x4,
} GXTexMtxType;

typedef enum _GXTexGenType
{
    GX_TG_MTX3x4,
    GX_TG_MTX2x4,
    GX_TG_BUMP0,
    GX_TG_BUMP1,
    GX_TG_BUMP2,
    GX_TG_BUMP3,
    GX_TG_BUMP4,
    GX_TG_BUMP5,
    GX_TG_BUMP6,
    GX_TG_BUMP7,
    GX_TG_SRTG,
} GXTexGenType;

typedef enum _GXPosNrmMtx
{
    GX_PNMTX0 = 0,
    GX_PNMTX1 = 3,
    GX_PNMTX2 = 6,
    GX_PNMTX3 = 9,
    GX_PNMTX4 = 12,
    GX_PNMTX5 = 15,
    GX_PNMTX6 = 18,
    GX_PNMTX7 = 21,
    GX_PNMTX8 = 24,
    GX_PNMTX9 = 27,
} GXPosNrmMtx;

typedef enum _GXTexMtx
{
    GX_TEXMTX0 = 30,
    GX_TEXMTX1 = 33,
    GX_TEXMTX2 = 36,
    GX_TEXMTX3 = 39,
    GX_TEXMTX4 = 42,
    GX_TEXMTX5 = 45,
    GX_TEXMTX6 = 48,
    GX_TEXMTX7 = 51,
    GX_TEXMTX8 = 54,
    GX_TEXMTX9 = 57,
    GX_IDENTITY = 60,
} GXTexMtx;

typedef enum _GXChannelID
{
    GX_COLOR0,
    GX_COLOR1,
    GX_ALPHA0,
    GX_ALPHA1,
    GX_COLOR0A0,
    GX_COLOR1A1,
    GX_COLOR_ZERO,
    GX_ALPHA_BUMP,
    GX_ALPHA_BUMPN,
    GX_COLOR_NULL = 0xFF,
} GXChannelID;

typedef enum _GXTexGenSrc
{
    GX_TG_POS,
    GX_TG_NRM,
    GX_TG_BINRM,
    GX_TG_TANGENT,
    GX_TG_TEX0,
    GX_TG_TEX1,
    GX_TG_TEX2,
    GX_TG_TEX3,
    GX_TG_TEX4,
    GX_TG_TEX5,
    GX_TG_TEX6,
    GX_TG_TEX7,
    GX_TG_TEXCOORD0,
    GX_TG_TEXCOORD1,
    GX_TG_TEXCOORD2,
    GX_TG_TEXCOORD3,
    GX_TG_TEXCOORD4,
    GX_TG_TEXCOORD5,
    GX_TG_TEXCOORD6,
    GX_TG_COLOR0,
    GX_TG_COLOR1,
} GXTexGenSrc;

typedef enum _GXBlendMode
{
    GX_BM_NONE,
    GX_BM_BLEND,
    GX_BM_LOGIC,
    GX_BM_SUBTRACT,
    GX_MAX_BLENDMODE,
} GXBlendMode;

typedef enum _GXBlendFactor
{
    GX_BL_ZERO,
    GX_BL_ONE,
    GX_BL_SRCCLR,
    GX_BL_INVSRCCLR,
    GX_BL_SRCALPHA,
    GX_BL_INVSRCALPHA,
    GX_BL_DSTALPHA,
    GX_BL_INVDSTALPHA,
    GX_BL_DSTCLR = GX_BL_SRCCLR,
    GX_BL_INVDSTCLR = GX_BL_INVSRCCLR,
} GXBlendFactor;

typedef enum _GXLogicOp
{
    GX_LO_CLEAR,
    GX_LO_AND,
    GX_LO_REVAND,
    GX_LO_COPY,
    GX_LO_INVAND,
    GX_LO_NOOP,
    GX_LO_XOR,
    GX_LO_OR,
    GX_LO_NOR,
    GX_LO_EQUIV,
    GX_LO_INV,
    GX_LO_REVOR,
    GX_LO_INVCOPY,
    GX_LO_INVOR,
    GX_LO_NAND,
    GX_LO_SET,
} GXLogicOp;

typedef enum _GXCompCnt
{
    GX_POS_XY = 0,
    GX_POS_XYZ = 1,
    GX_NRM_XYZ = 0,
    GX_NRM_NBT = 1,
    GX_NRM_NBT3 = 2,
    GX_CLR_RGB = 0,
    GX_CLR_RGBA = 1,
    GX_TEX_S = 0,
    GX_TEX_ST = 1,
} GXCompCnt;

typedef enum _GXCompType
{
    GX_U8 = 0,
    GX_S8 = 1,
    GX_U16 = 2,
    GX_S16 = 3,
    GX_F32 = 4,
    GX_RGB565 = 0,
    GX_RGB8 = 1,
    GX_RGBX8 = 2,
    GX_RGBA4 = 3,
    GX_RGBA6 = 4,
    GX_RGBA8 = 5,
} GXCompType;

typedef enum _GXPTTexMtx
{
    GX_PTTEXMTX0 = 64,
    GX_PTTEXMTX1 = 67,
    GX_PTTEXMTX2 = 70,
    GX_PTTEXMTX3 = 73,
    GX_PTTEXMTX4 = 76,
    GX_PTTEXMTX5 = 79,
    GX_PTTEXMTX6 = 82,
    GX_PTTEXMTX7 = 85,
    GX_PTTEXMTX8 = 88,
    GX_PTTEXMTX9 = 91,
    GX_PTTEXMTX10 = 94,
    GX_PTTEXMTX11 = 97,
    GX_PTTEXMTX12 = 100,
    GX_PTTEXMTX13 = 103,
    GX_PTTEXMTX14 = 106,
    GX_PTTEXMTX15 = 109,
    GX_PTTEXMTX16 = 112,
    GX_PTTEXMTX17 = 115,
    GX_PTTEXMTX18 = 118,
    GX_PTTEXMTX19 = 121,
    GX_PTIDENTITY = 125,
} GXPTTexMtx;

typedef enum _GXTevRegID
{
    GX_TEVPREV,
    GX_TEVREG0,
    GX_TEVREG1,
    GX_TEVREG2,
    GX_MAX_TEVREG,
} GXTevRegID;

typedef enum _GXDiffuseFn
{
    GX_DF_NONE,
    GX_DF_SIGN,
    GX_DF_CLAMP,
} GXDiffuseFn;

typedef enum _GXColorSrc
{
    GX_SRC_REG,
    GX_SRC_VTX,
} GXColorSrc;

typedef enum _GXAttnFn
{
    GX_AF_SPEC,
    GX_AF_SPOT,
    GX_AF_NONE,
} GXAttnFn;

typedef enum _GXLightID
{
    GX_LIGHT0 = 0x001,
    GX_LIGHT1 = 0x002,
    GX_LIGHT2 = 0x004,
    GX_LIGHT3 = 0x008,
    GX_LIGHT4 = 0x010,
    GX_LIGHT5 = 0x020,
    GX_LIGHT6 = 0x040,
    GX_LIGHT7 = 0x080,
    GX_MAX_LIGHT = 0x100,
    GX_LIGHT_NULL = 0,
} GXLightID;

typedef enum _GXTexOffset
{
    GX_TO_ZERO,
    GX_TO_SIXTEENTH,
    GX_TO_EIGHTH,
    GX_TO_FOURTH,
    GX_TO_HALF,
    GX_TO_ONE,
    GX_MAX_TEXOFFSET,
} GXTexOffset;

typedef enum _GXSpotFn
{
    GX_SP_OFF,
    GX_SP_FLAT,
    GX_SP_COS,
    GX_SP_COS2,
    GX_SP_SHARP,
    GX_SP_RING1,
    GX_SP_RING2,
} GXSpotFn;

typedef enum _GXDistAttnFn
{
    GX_DA_OFF,
    GX_DA_GENTLE,
    GX_DA_MEDIUM,
    GX_DA_STEEP,
} GXDistAttnFn;

typedef enum _GXCullMode
{
    GX_CULL_NONE,
    GX_CULL_FRONT,
    GX_CULL_BACK,
    GX_CULL_ALL

} GXCullMode;

typedef enum _GXTevSwapSel
{
    GX_TEV_SWAP0 = 0,
    GX_TEV_SWAP1,
    GX_TEV_SWAP2,
    GX_TEV_SWAP3,
    GX_MAX_TEVSWAP
} GXTevSwapSel;

typedef enum _GXTevColorChan
{
    GX_CH_RED = 0,
    GX_CH_GREEN,
    GX_CH_BLUE,
    GX_CH_ALPHA
} GXTevColorChan;

typedef enum _GXFogType
{
    GX_FOG_NONE = 0,
    GX_FOG_LIN = 2,
    GX_FOG_EXP = 4,
    GX_FOG_EXP2 = 5,
    GX_FOG_REVEXP = 6,
    GX_FOG_REVEXP2 = 7
} GXFogType;

typedef enum _GXTevColorArg
{
    GX_CC_CPREV,
    GX_CC_APREV,
    GX_CC_C0,
    GX_CC_A0,
    GX_CC_C1,
    GX_CC_A1,
    GX_CC_C2,
    GX_CC_A2,
    GX_CC_TEXC,
    GX_CC_TEXA,
    GX_CC_RASC,
    GX_CC_RASA,
    GX_CC_ONE,
    GX_CC_HALF,
    GX_CC_KONST,
    GX_CC_ZERO,
    GX_CC_TEXRRR,
    GX_CC_TEXGGG,
    GX_CC_TEXBBB,
    GX_CC_QUARTER = GX_CC_KONST
} GXTevColorArg;

typedef enum _GXTevAlphaArg
{
    GX_CA_APREV,
    GX_CA_A0,
    GX_CA_A1,
    GX_CA_A2,
    GX_CA_TEXA,
    GX_CA_RASA,
    GX_CA_KONST,
    GX_CA_ZERO,
    GX_CA_ONE = GX_CA_KONST
} GXTevAlphaArg;

typedef enum _GXTevOp
{
    GX_TEV_ADD = 0,
    GX_TEV_SUB = 1,
    GX_TEV_COMP_R8_GT = 8,
    GX_TEV_COMP_R8_EQ = 9,
    GX_TEV_COMP_GR16_GT = 10,
    GX_TEV_COMP_GR16_EQ = 11,
    GX_TEV_COMP_BGR24_GT = 12,
    GX_TEV_COMP_BGR24_EQ = 13,
    GX_TEV_COMP_RGB8_GT = 14,
    GX_TEV_COMP_RGB8_EQ = 15,
    GX_TEV_COMP_A8_GT = GX_TEV_COMP_RGB8_GT,
    GX_TEV_COMP_A8_EQ = GX_TEV_COMP_RGB8_EQ
} GXTevOp;

typedef enum _GXTevBias
{
    GX_TB_ZERO,
    GX_TB_ADDHALF,
    GX_TB_SUBHALF,
    GX_MAX_TEVBIAS
} GXTevBias;

typedef enum _GXTevClampMode
{
    GX_TC_LINEAR,
    GX_TC_GE,
    GX_TC_EQ,
    GX_TC_LE,
    GX_MAX_TEVCLAMPMODE
} GXTevClampMode;

typedef enum _GXTevScale
{
    GX_CS_SCALE_1,
    GX_CS_SCALE_2,
    GX_CS_SCALE_4,
    GX_CS_DIVIDE_2,
    GX_MAX_TEVSCALE
} GXTevScale;

typedef enum _GXTevKColorSel
{
    GX_TEV_KCSEL_1 = 0x00,
    GX_TEV_KCSEL_7_8 = 0x01,
    GX_TEV_KCSEL_3_4 = 0x02,
    GX_TEV_KCSEL_5_8 = 0x03,
    GX_TEV_KCSEL_1_2 = 0x04,
    GX_TEV_KCSEL_3_8 = 0x05,
    GX_TEV_KCSEL_1_4 = 0x06,
    GX_TEV_KCSEL_1_8 = 0x07,
    GX_TEV_KCSEL_K0 = 0x0C,
    GX_TEV_KCSEL_K1 = 0x0D,
    GX_TEV_KCSEL_K2 = 0x0E,
    GX_TEV_KCSEL_K3 = 0x0F,
    GX_TEV_KCSEL_K0_R = 0x10,
    GX_TEV_KCSEL_K1_R = 0x11,
    GX_TEV_KCSEL_K2_R = 0x12,
    GX_TEV_KCSEL_K3_R = 0x13,
    GX_TEV_KCSEL_K0_G = 0x14,
    GX_TEV_KCSEL_K1_G = 0x15,
    GX_TEV_KCSEL_K2_G = 0x16,
    GX_TEV_KCSEL_K3_G = 0x17,
    GX_TEV_KCSEL_K0_B = 0x18,
    GX_TEV_KCSEL_K1_B = 0x19,
    GX_TEV_KCSEL_K2_B = 0x1A,
    GX_TEV_KCSEL_K3_B = 0x1B,
    GX_TEV_KCSEL_K0_A = 0x1C,
    GX_TEV_KCSEL_K1_A = 0x1D,
    GX_TEV_KCSEL_K2_A = 0x1E,
    GX_TEV_KCSEL_K3_A = 0x1F
} GXTevKColorSel;

typedef enum _GXTevKAlphaSel
{
    GX_TEV_KASEL_1 = 0x00,
    GX_TEV_KASEL_7_8 = 0x01,
    GX_TEV_KASEL_3_4 = 0x02,
    GX_TEV_KASEL_5_8 = 0x03,
    GX_TEV_KASEL_1_2 = 0x04,
    GX_TEV_KASEL_3_8 = 0x05,
    GX_TEV_KASEL_1_4 = 0x06,
    GX_TEV_KASEL_1_8 = 0x07,
    GX_TEV_KASEL_K0_R = 0x10,
    GX_TEV_KASEL_K1_R = 0x11,
    GX_TEV_KASEL_K2_R = 0x12,
    GX_TEV_KASEL_K3_R = 0x13,
    GX_TEV_KASEL_K0_G = 0x14,
    GX_TEV_KASEL_K1_G = 0x15,
    GX_TEV_KASEL_K2_G = 0x16,
    GX_TEV_KASEL_K3_G = 0x17,
    GX_TEV_KASEL_K0_B = 0x18,
    GX_TEV_KASEL_K1_B = 0x19,
    GX_TEV_KASEL_K2_B = 0x1A,
    GX_TEV_KASEL_K3_B = 0x1B,
    GX_TEV_KASEL_K0_A = 0x1C,
    GX_TEV_KASEL_K1_A = 0x1D,
    GX_TEV_KASEL_K2_A = 0x1E,
    GX_TEV_KASEL_K3_A = 0x1F
} GXTevKAlphaSel;

typedef enum _GXTevKColorID
{
    GX_KCOLOR0 = 0,
    GX_KCOLOR1,
    GX_KCOLOR2,
    GX_KCOLOR3,
    GX_MAX_KCOLOR
} GXTevKColorID;

typedef enum _GXZTexOp
{
    GX_ZT_DISABLE,
    GX_ZT_ADD,
    GX_ZT_REPLACE,
    GX_MAX_ZTEXOP,
} GXZTexOp;

typedef enum _GXIndTexFormat
{
    GX_ITF_8,
    GX_ITF_5,
    GX_ITF_4,
    GX_ITF_3,
    GX_MAX_ITFORMAT,
} GXIndTexFormat;

typedef enum _GXIndTexBiasSel
{
    GX_ITB_NONE,
    GX_ITB_S,
    GX_ITB_T,
    GX_ITB_ST,
    GX_ITB_U,
    GX_ITB_SU,
    GX_ITB_TU,
    GX_ITB_STU,
    GX_MAX_ITBIAS,
} GXIndTexBiasSel;

typedef enum _GXIndTexAlphaSel
{
    GX_ITBA_OFF,
    GX_ITBA_S,
    GX_ITBA_T,
    GX_ITBA_U,
    GX_MAX_ITBALPHA,
} GXIndTexAlphaSel;

typedef enum _GXIndTexMtxID
{
    GX_ITM_OFF,
    GX_ITM_0,
    GX_ITM_1,
    GX_ITM_2,
    GX_ITM_S0 = 5,
    GX_ITM_S1,
    GX_ITM_S2,
    GX_ITM_T0 = 9,
    GX_ITM_T1,
    GX_ITM_T2,
} GXIndTexMtxID;

typedef enum _GXIndTexWrap
{
    GX_ITW_OFF,
    GX_ITW_256,
    GX_ITW_128,
    GX_ITW_64,
    GX_ITW_32,
    GX_ITW_16,
    GX_ITW_0,
    GX_MAX_ITWRAP,
} GXIndTexWrap;

typedef enum _GXIndTexStageID
{
    GX_INDTEXSTAGE0,
    GX_INDTEXSTAGE1,
    GX_INDTEXSTAGE2,
    GX_INDTEXSTAGE3,
    GX_MAX_INDTEXSTAGE,
} GXIndTexStageID;

typedef enum _GXIndTexScale
{
    GX_ITS_1,
    GX_ITS_2,
    GX_ITS_4,
    GX_ITS_8,
    GX_ITS_16,
    GX_ITS_32,
    GX_ITS_64,
    GX_ITS_128,
    GX_ITS_256,
    GX_MAX_ITSCALE,
} GXIndTexScale;

typedef enum _GXPerf0
{
    GX_PERF0_VERTICES,
    GX_PERF0_CLIP_VTX,
    GX_PERF0_CLIP_CLKS,
    GX_PERF0_XF_WAIT_IN,
    GX_PERF0_XF_WAIT_OUT,
    GX_PERF0_XF_XFRM_CLKS,
    GX_PERF0_XF_LIT_CLKS,
    GX_PERF0_XF_BOT_CLKS,
    GX_PERF0_XF_REGLD_CLKS,
    GX_PERF0_XF_REGRD_CLKS,
    GX_PERF0_CLIP_RATIO,

    GX_PERF0_TRIANGLES,
    GX_PERF0_TRIANGLES_CULLED,
    GX_PERF0_TRIANGLES_PASSED,
    GX_PERF0_TRIANGLES_SCISSORED,
    GX_PERF0_TRIANGLES_0TEX,
    GX_PERF0_TRIANGLES_1TEX,
    GX_PERF0_TRIANGLES_2TEX,
    GX_PERF0_TRIANGLES_3TEX,
    GX_PERF0_TRIANGLES_4TEX,
    GX_PERF0_TRIANGLES_5TEX,
    GX_PERF0_TRIANGLES_6TEX,
    GX_PERF0_TRIANGLES_7TEX,
    GX_PERF0_TRIANGLES_8TEX,
    GX_PERF0_TRIANGLES_0CLR,
    GX_PERF0_TRIANGLES_1CLR,
    GX_PERF0_TRIANGLES_2CLR,

    GX_PERF0_QUAD_0CVG,
    GX_PERF0_QUAD_NON0CVG,
    GX_PERF0_QUAD_1CVG,
    GX_PERF0_QUAD_2CVG,
    GX_PERF0_QUAD_3CVG,
    GX_PERF0_QUAD_4CVG,
    GX_PERF0_AVG_QUAD_CNT,

    GX_PERF0_CLOCKS,
    GX_PERF0_NONE,
} GXPerf0;

typedef enum _GXPerf1
{
    GX_PERF1_TEXELS,
    GX_PERF1_TX_IDLE,
    GX_PERF1_TX_REGS,
    GX_PERF1_TX_MEMSTALL,
    GX_PERF1_TC_CHECK1_2,
    GX_PERF1_TC_CHECK3_4,
    GX_PERF1_TC_CHECK5_6,
    GX_PERF1_TC_CHECK7_8,
    GX_PERF1_TC_MISS,

    GX_PERF1_VC_ELEMQ_FULL,
    GX_PERF1_VC_MISSQ_FULL,
    GX_PERF1_VC_MEMREQ_FULL,
    GX_PERF1_VC_STATUS7,
    GX_PERF1_VC_MISSREP_FULL,
    GX_PERF1_VC_STREAMBUF_LOW,
    GX_PERF1_VC_ALL_STALLS,
    GX_PERF1_VERTICES,

    GX_PERF1_FIFO_REQ,
    GX_PERF1_CALL_REQ,
    GX_PERF1_VC_MISS_REQ,
    GX_PERF1_CP_ALL_REQ,

    GX_PERF1_CLOCKS,
    GX_PERF1_NONE,
} GXPerf1;

typedef enum _GXVCachePerf
{
    GX_VC_POS = 0,
    GX_VC_NRM = 1,
    GX_VC_CLR0 = 2,
    GX_VC_CLR1 = 3,
    GX_VC_TEX0 = 4,
    GX_VC_TEX1 = 5,
    GX_VC_TEX2 = 6,
    GX_VC_TEX3 = 7,
    GX_VC_TEX4 = 8,
    GX_VC_TEX5 = 9,
    GX_VC_TEX6 = 10,
    GX_VC_TEX7 = 11,
    GX_VC_ALL = 15,
} GXVCachePerf;

typedef enum _GXClipMode
{
    GX_CLIP_ENABLE = 0,
    GX_CLIP_DISABLE = 1,
} GXClipMode;

typedef enum _GXFBClamp
{
    GX_CLAMP_NONE = 0,
    GX_CLAMP_TOP = 1,
    GX_CLAMP_BOTTOM = 2,
} GXFBClamp;

typedef enum _GXCopyMode
{
    GX_COPY_PROGRESSIVE = 0,
    GX_COPY_INTLC_EVEN = 2,
    GX_COPY_INTLC_ODD = 3,
} GXCopyMode;

typedef enum _GXAlphaReadMode
{
    GX_READ_00,
    GX_READ_FF,
    GX_READ_NONE,
} GXAlphaReadMode;

typedef enum _GXTexCacheSize
{
    GX_TEXCACHE_32K,
    GX_TEXCACHE_128K,
    GX_TEXCACHE_512K,
    GX_TEXCACHE_NONE,
} GXTexCacheSize;

typedef enum _GXTlut
{
    GX_TLUT0,
    GX_TLUT1,
    GX_TLUT2,
    GX_TLUT3,
    GX_TLUT4,
    GX_TLUT5,
    GX_TLUT6,
    GX_TLUT7,
    GX_TLUT8,
    GX_TLUT9,
    GX_TLUT10,
    GX_TLUT11,
    GX_TLUT12,
    GX_TLUT13,
    GX_TLUT14,
    GX_TLUT15,
    GX_BIGTLUT0,
    GX_BIGTLUT1,
    GX_BIGTLUT2,
    GX_BIGTLUT3,
} GXTlut;

typedef enum _GXTlutFmt
{
    GX_TL_IA8,
    GX_TL_RGB565,
    GX_TL_RGB5A3,
    GX_MAX_TLUTFMT,
} GXTlutFmt;

typedef enum _GXTlutSize
{
    GX_TLUT_16 = 1,
    GX_TLUT_32 = 2,
    GX_TLUT_64 = 4,
    GX_TLUT_128 = 8,
    GX_TLUT_256 = 16,
    GX_TLUT_512 = 32,
    GX_TLUT_1K = 64,
    GX_TLUT_2K = 128,
    GX_TLUT_4K = 256,
    GX_TLUT_8K = 512,
    GX_TLUT_16K = 1024,
} GXTlutSize;

typedef enum _GXMiscToken
{
    GX_MT_XF_FLUSH = 1,
    GX_MT_DL_SAVE_CONTEXT = 2,
    GX_MT_NULL = 0,
} GXMiscToken;
# 9 "src/sysdolphin/baselib\\cobj.h" 2
# 1 "extern/dolphin/include\\dolphin/mtx.h" 1 3
# 10 "extern/dolphin/include\\dolphin/mtx.h" 3
typedef struct {
    f32 x, y;
} Vec2, *Vec2Ptr, Point2d, *Point2dPtr;

typedef struct {
    f32 x, y, z;
} Vec, Vec3, *VecPtr, Point3d, *Point3dPtr;

typedef struct {
    s8 x, y, z;
} S8Vec3, S8Vec, *S8Vec3Ptr, *S8VecPtr;

typedef struct {
    u8 x, y, z, w;
} U8Vec4, *U8Vec4Ptr;

typedef struct {
    s16 x, y, z;
} S16Vec, S16Vec3, *S16VecPtr, *S16Vec3Ptr;

typedef struct {
    int x, y;
} IntVec2, *IntVec2Ptr;

typedef struct {
    s32 x, y;
} S32Vec2, *S32Vec2Ptr;

typedef struct {
    int x, y, z;
} IntVec3, *IntVec3Ptr;

typedef struct {
    s32 x, y, z;
} S32Vec, S32Vec3, *S32VecPtr, *S32Vec3Ptr;

typedef struct {
    f32 x, y, z, w;
} Quaternion, Vec4, *QuaternionPtr, Qtrn, *QtrnPtr;

typedef f32 Mtx[3][4];
typedef f32 Mtx44[4][4];

typedef f32 (*MtxPtr)[4];
typedef f32 (*Mtx44Ptr)[4];

typedef f32 ROMtx[4][3];
typedef f32 (*ROMtxPtr)[3];




void MTXFrustum(Mtx m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 f);
void MTXPerspective(Mtx m, f32 fovY, f32 aspect, f32 n, f32 f);
void MTXOrtho(Mtx m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 f);
void MTXPerspective(Mtx44 m, f32 fovY, f32 aspect, f32 n, f32 f);
void C_MTXLookAt(Mtx m, Point3dPtr camPos, VecPtr camUp, Point3dPtr target);
# 124 "extern/dolphin/include\\dolphin/mtx.h" 3
void MTXRotRad(Mtx m, char axis, f32 rad);
void PSMTXTrans(Mtx m, f32 xT, f32 yT, f32 zT);
void MTXTransApply(Mtx src, Mtx dst, f32 xT, f32 yT, f32 zT);
void MTXScaleApply(Mtx src, Mtx dst, f32 xS, f32 yS, f32 zS);
void MTXReflect(Mtx m, Vec* p, Vec* n);
void MTXLookAt(Mtx m, Vec* camPos, Vec* camUp, Vec* target);
void MTXLightFrustum(Mtx m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 scaleS,
                     f32 scaleT, f32 transS, f32 transT);
void MTXLightPerspective(Mtx m, f32 fovY, f32 aspect, f32 scaleS, f32 scaleT,
                         f32 transS, f32 transT);
void MTXLightOrtho(Mtx m, f32 t, f32 b, f32 l, f32 r, f32 scaleS, f32 scaleT,
                   f32 transS, f32 transT);


void C_MTXIdentity(Mtx m);
void C_MTXCopy(Mtx src, Mtx dst);
void C_MTXConcat(Mtx a, Mtx b, Mtx ab);
void C_MTXTranspose(Mtx src, Mtx xPose);
void C_MTXScale(Mtx m, f32 xS, f32 yS, f32 zS);
void C_MTXRotAxisRad(Mtx m, Vec* axis, f32 rad);
void C_MTXRotTrig(Mtx m, char axis, f32 sinA, f32 cosA);
void C_MTXQuat(Mtx m, QuaternionPtr q);
u32 C_MTXInverse(Mtx src, Mtx inv);
u32 C_MTXInvXpose(Mtx src, Mtx invX);


void PSMTXIdentity(Mtx m);
void PSMTXCopy(Mtx src, Mtx dst);
void PSMTXConcat(Mtx mA, Mtx mB, Mtx mAB);
void PSMTXTranspose(Mtx src, Mtx xPose);
void PSMTXScale(Mtx m, f32 xS, f32 yS, f32 zS);
void PSMTXRotAxisRad(Mtx m, Vec* axis, f32 rad);
void PSMTXRotTrig(Mtx m, char axis, f32 sinA, f32 cosA);
void PSMTXQuat(Mtx m, QuaternionPtr q);
u32 PSMTXInverse(Mtx src, Mtx inv);
u32 PSMTXInvXpose(Mtx src, Mtx invX);


typedef struct {
    u32 numMtx;
    Mtx* stackBase;
    Mtx* stackPtr;
} MTXStack;

void MTXInitStack(MTXStack* sPtr, u32 numMtx);
Mtx* MTXPush(MTXStack* sPtr, Mtx m);
Mtx* MTXPushFwd(MTXStack* sPtr, Mtx m);
Mtx* MTXPushInv(MTXStack* sPtr, Mtx m);
Mtx* MTXPushInvXpose(MTXStack* sPtr, Mtx m);
Mtx* MTXPop(MTXStack* sPtr);
Mtx* MTXGetStackPtr(MTXStack* sPtr);


void C_MTXMultVecSR(Mtx44 m, Vec* src, Vec* dst);
void PSMTXMultVecSR(Mtx44 m, Vec* src, Vec* dst);
void MTXMultVecArraySR(Mtx44 m, Vec* srcBase, Vec* dstBase, u32 count);


void C_MTXMultVec(Mtx44 m, Vec* src, Vec* dst);
void C_MTXMultVecArray(Mtx m, Vec* srcBase, Vec* dstBase, u32 count);


void PSMTXMultVec(Mtx44 m, Vec* src, Vec* dst);
void PSMTXMultVecArray(Mtx m, Vec* srcBase, Vec* dstBase, u32 count);


void PSMTXReorder(Mtx src, ROMtx dest);
void PSMTXROMultVecArray(ROMtx* m, Vec* srcBase, Vec* dstBase, u32 count);
void PSMTXROSkin2VecArray(ROMtx* m0, ROMtx* m1, f32* wtBase, Vec* srcBase,
                          Vec* dstBase, u32 count);
void PSMTXROMultS16VecArray(ROMtx* m, S16Vec* srcBase, Vec* dstBase,
                            u32 count);
void PSMTXMultS16VecArray(Mtx44* m, S16Vec* srcBase, Vec* dstBase, u32 count);


f32 C_VECMag(Vec* v);
f32 PSVECMag(Vec* v);
void VECHalfAngle(Vec* a, Vec* b, Vec* half);
void VECReflect(Vec* src, Vec* normal, Vec* dst);
f32 VECDistance(Vec* a, Vec* b);


void C_VECAdd(Vec* a, Vec* b, Vec* c);
void C_VECSubtract(Vec* a, Vec* b, Vec* c);
void C_VECScale(Vec* src, Vec* dst, f32 scale);
void C_VECNormalize(Vec* src, Vec* unit);
f32 C_VECSquareMag(Vec* v);
f32 C_VECDotProduct(Vec* a, Vec* b);
void C_VECCrossProduct(Vec* a, Vec* b, Vec* axb);
f32 C_VECSquareDistance(Vec* a, Vec* b);


void PSVECAdd(Vec* a, Vec* b, Vec* c);
void PSVECSubtract(Vec* a, Vec* b, Vec* c);
void PSVECScale(Vec* src, Vec* dst, f32 scale);
void PSVECNormalize(Vec* vec1, Vec* dst);
f32 PSVECSquareMag(Vec* vec1);
f32 PSVECDotProduct(Vec* vec1, Vec* vec2);
void PSVECCrossProduct(Vec* vec1, Vec* vec2, Vec* dst);
f32 PSVECSquareDistance(Vec* vec1, Vec* vec2);
# 10 "src/sysdolphin/baselib\\cobj.h" 2
# 1 "src\\sysdolphin/baselib/object.h" 1







# 1 "src\\sysdolphin/baselib/class.h" 1
# 14 "src\\sysdolphin/baselib/class.h"
typedef struct _HSD_Class {
    struct _HSD_ClassInfo* class_info;
} HSD_Class;

typedef struct _HSD_ClassInfoHead {
    void (*info_init)(void);
    u32 flags;
    char* library_name;
    char* class_name;
    s16 obj_size;
    s16 info_size;
    struct _HSD_ClassInfo* parent;
    struct _HSD_ClassInfo* next;
    struct _HSD_ClassInfo* child;
    u32 nb_exist;
    u32 nb_peak;
} HSD_ClassInfoHead;

typedef struct _HSD_ClassInfo {
    struct _HSD_ClassInfoHead head;
    HSD_Class* (*alloc)(struct _HSD_ClassInfo* c);
    int (*init)(struct _HSD_Class* c);
    void (*release)(struct _HSD_Class* c);
    void (*destroy)(struct _HSD_Class* c);
    void (*amnesia)(struct _HSD_ClassInfo* c);
} HSD_ClassInfo;

typedef struct _HSD_FreeList {
    struct _HSD_FreeList* next;
} HSD_FreeList;

typedef struct _HSD_MemoryEntry {
    u32 size;
    u32 nb_alloc;
    u32 nb_free;
    struct _HSD_FreeList* free_list;
    struct _HSD_MemoryEntry* next;
} HSD_MemoryEntry;

extern HSD_ClassInfo hsdClass;


void ClassInfoInit(HSD_ClassInfo* info);
void hsdInitClassInfo(HSD_ClassInfo* class_info, HSD_ClassInfo* parent_info,
                      char* base_class_library, char* type, s32 info_size,
                      s32 class_size);
void OSReport_PrintSpaces(s32 count);

void* hsdAllocMemPiece(s32 size);
void hsdFreeMemPiece(void* mem, s32 size);
void* hsdNew(HSD_ClassInfo*);
bool hsdChangeClass(void* object, void* class_info);
bool hsdIsDescendantOf(void* info, void* p);
bool hsdObjIsDescendantOf(HSD_Obj* o, HSD_ClassInfo* p);
HSD_ClassInfo* hsdSearchClassInfo(const char* class_name);
void hsdForgetClassLibrary(const char* library_name);

HSD_MemoryEntry* GetMemoryEntry(s32 idx);
HSD_Class* _hsdClassAlloc(HSD_ClassInfo* info);
int _hsdClassInit(HSD_Class* arg0);
void _hsdClassRelease(HSD_Class* cls);
void _hsdClassDestroy(HSD_Class* cls);
void _hsdClassAmnesia(HSD_ClassInfo* info);
void class_set_flags(HSD_ClassInfo* class_info, s32 set, s32 reset);
void ForgetClassLibraryReal(HSD_ClassInfo* class_info);
void DumpClassStat(HSD_ClassInfo* info, s32 level);
void hsdDumpClassStat(HSD_ClassInfo* info, bool recursive, s32 level);

void ForgetClassLibraryChild(const char* library_name,
                             HSD_ClassInfo* class_info);

static inline void hsdDelete(void* object)
{
    if (object == 0L) {
        return;
    }

    (((HSD_Class*) object)->class_info)->release((HSD_Class*) object);
    (((HSD_Class*) object)->class_info)->destroy((HSD_Class*) object);
}
# 9 "src\\sysdolphin/baselib/object.h" 2
# 1 "src\\sysdolphin/baselib/debug.h" 1





# 1 "extern/dolphin/include\\dolphin/os.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os.h" 3
typedef s64 OSTime;
typedef u32 OSTick;

typedef s16 __OSInterrupt;
typedef u32 OSInterruptMask;

# 1 "extern/dolphin/include\\dolphin/os/OSContext.h" 1 3
# 137 "extern/dolphin/include\\dolphin/os/OSContext.h" 3
typedef struct OSContext
{
              u32 gpr[32];
              u32 cr;
              u32 lr;
              u32 ctr;
              u32 xer;
              f64 fpr[32];
              u32 fpscr_pad;
              u32 fpscr;
              u32 srr0;
              u32 srr1;
              u16 mode;
              u16 state;
              u32 gqr[8];
              f64 psf[32];
} OSContext;

u32 OSGetStackPointer(void);
void OSDumpContext(OSContext *context);
void OSLoadContext(OSContext *context);
u32 OSSaveContext(OSContext *context);
void OSClearContext(OSContext *context);
OSContext *OSGetCurrentContext(void);
void OSSetCurrentContext(OSContext *context);
void OSLoadFPUContext(OSContext *fpuContext);
void OSSaveFPUContext(OSContext *fpuContext);
u32 OSSwitchStack(u32 newsp);
int OSSwitchFiber(u32 pc, u32 newsp);
void OSInitContext(OSContext *context, u32 pc, u32 newsp);
void OSFillFPUContext(OSContext *context);
# 17 "extern/dolphin/include\\dolphin/os.h" 2 3

typedef void (*__OSInterruptHandler)(__OSInterrupt interrupt,
                                     OSContext* context);


# 1 "extern/dolphin/include\\dolphin/os/OSAlarm.h" 1 3



# 1 "extern/dolphin/include\\dolphin/os.h" 1 3
# 5 "extern/dolphin/include\\dolphin/os/OSAlarm.h" 2 3


typedef struct OSAlarm OSAlarm;
typedef void (*OSAlarmHandler)(OSAlarm* alarm, OSContext* context);

struct OSAlarm {
    OSAlarmHandler handler;
    u32 tag;
    OSTime fire;
    OSAlarm* prev;
    OSAlarm* next;
    OSTime period;
    OSTime start;
};

BOOL OSCheckAlarmQueue(void);
void OSInitAlarm(void);
void OSCreateAlarm(OSAlarm* alarm);
void OSSetAlarm(OSAlarm* alarm, OSTime tick, OSAlarmHandler handler);
void OSSetAbsAlarm(struct OSAlarm* alarm, long long time,
                   void (*handler)(struct OSAlarm*, struct OSContext*));
void OSSetPeriodicAlarm(OSAlarm* alarm, OSTime start, OSTime period,
                        OSAlarmHandler handler);
void OSCancelAlarm(OSAlarm* alarm);
# 23 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSAlloc.h" 1 3





typedef int OSHeapHandle;

extern volatile OSHeapHandle __OSCurrHeap;

void * OSAllocFromHeap(int heap, unsigned long size);
void * OSAllocFixed(void * rstart, void * rend);
void OSFreeToHeap(int heap, void * ptr);
int OSSetCurrentHeap(int heap);
void * OSInitAlloc(void * arenaStart, void * arenaEnd, int maxHeaps);
int OSCreateHeap(void * start, void * end);
void OSDestroyHeap(int heap);
void OSAddToHeap(int heap, void * start, void * end);
long OSCheckHeap(int heap);
unsigned long OSReferentSize(void * ptr);
void OSDumpHeap(int heap);
void OSVisitAllocated(void (* visitor)(void *, unsigned long));
# 24 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSCache.h" 1 3





void DCInvalidateRange(void* addr, u32 nBytes);
void DCFlushRange(void* addr, u32 nBytes);
void DCStoreRange(void* addr, u32 nBytes);
void DCFlushRangeNoSync(void* addr, u32 nBytes);
void DCStoreRangeNoSync(void* addr, u32 nBytes);
void DCZeroRange(void* addr, u32 nBytes);
void DCTouchRange(void* addr, u32 nBytes);
void ICInvalidateRange(void* addr, u32 nBytes);





void LCEnable(void);
void LCDisable(void);
void LCLoadBlocks(void* destTag, void* srcAddr, u32 numBlocks);
void LCStoreBlocks(void* destAddr, void* srcTag, u32 numBlocks);
u32 LCLoadData(void* destAddr, void* srcAddr, u32 nBytes);
u32 LCStoreData(void* destAddr, void* srcAddr, u32 nBytes);
u32 LCQueueLength(void);
void LCQueueWait(u32 len);
void LCFlushQueue(void);
void __OSCacheInit(void);
# 25 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSDC.h" 1 3







void DCFlashInvalidate(void);
void DCEnable(void);
void DCDisable(void);
void DCFreeze(void);
void DCUnfreeze(void);
void DCTouchLoad(void *addr);
void DCBlockZero(void *addr);
void DCBlockStore(void *addr);
void DCBlockFlush(void *addr);
void DCBlockInvalidate(void *addr);
# 26 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSError.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSError.h" 3
typedef u16 OSError;
typedef void (*OSErrorHandler)(OSError error, OSContext* context, ...);
# 30 "extern/dolphin/include\\dolphin/os/OSError.h" 3
extern OSErrorHandler OSErrorTable[15];

OSErrorHandler OSSetErrorHandler(OSError error, OSErrorHandler handler);
# 27 "extern/dolphin/include\\dolphin/os.h" 2 3

# 1 "extern/dolphin/include\\dolphin/os/OSException.h" 1 3
# 29 "extern/dolphin/include\\dolphin/os/OSException.h" 3
typedef u8 __OSException;
typedef void (*__OSExceptionHandler)(__OSException exception,
                                     OSContext* context);

__OSExceptionHandler __OSSetExceptionHandler(__OSException exception,
                                             __OSExceptionHandler handler);
__OSExceptionHandler __OSGetExceptionHandler(__OSException exception);
# 29 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSFont.h" 1 3
# 17 "extern/dolphin/include\\dolphin/os/OSFont.h" 3
typedef struct OSFontHeader
{
             u16 fontType;
             u16 firstChar;
             u16 lastChar;
             u16 invalChar;
             u16 ascent;
             u16 descent;
             u16 width;
             u16 leading;
             u16 cellWidth;
             u16 cellHeight;
             u32 sheetSize;
             u16 sheetFormat;
             u16 sheetColumn;
             u16 sheetRow;
             u16 sheetWidth;
             u16 sheetHeight;
             u16 widthTable;
             u32 sheetImage;
             u32 sheetFullSize;
             u8 c0;
             u8 c1;
             u8 c2;
             u8 c3;
} OSFontHeader;

u16 OSGetFontEncode(void);
BOOL OSInitFont(OSFontHeader *fontData);
u32 OSLoadFont(OSFontHeader *fontData, void *temp);
char *OSGetFontTexture(char *string, void **image, s32 *x, s32 *y, s32 *width);
char *OSGetFontWidth(char *string, s32 *width);
char *OSGetFontTexel(char *string, void *image, s32 pos, s32 stride, s32 *width);
# 30 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSIC.h" 1 3







void ICFlashInvalidate(void);
void ICEnable(void);
void ICDisable(void);
void ICFreeze(void);
void ICUnfreeze(void);
void ICBlockInvalidate(void *addr);
void ICSync(void);
# 31 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSInterrupt.h" 1 3



# 1 "extern/dolphin/include\\dolphin/os.h" 1 3
# 5 "extern/dolphin/include\\dolphin/os/OSInterrupt.h" 2 3
# 102 "extern/dolphin/include\\dolphin/os/OSInterrupt.h" 3
extern volatile __OSInterrupt __OSLastInterrupt;
extern volatile u32 __OSLastInterruptSrr0;
extern volatile OSTime __OSLastInterruptTime;

__OSInterruptHandler __OSSetInterruptHandler(__OSInterrupt interrupt,
                                             __OSInterruptHandler handler);

__OSInterruptHandler __OSGetInterruptHandler(__OSInterrupt interrupt);

void __OSDispatchInterrupt(__OSException exception, OSContext* context);

OSInterruptMask OSGetInterruptMask(void);
OSInterruptMask OSSetInterruptMask(OSInterruptMask mask);
OSInterruptMask __OSMaskInterrupts(OSInterruptMask mask);
OSInterruptMask __OSUnmaskInterrupts(OSInterruptMask mask);
# 32 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSL2.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSL2.h" 3
void L2Enable(void);
void L2Disable(void);
void L2GlobalInvalidate(void);
void L2SetDataOnly(BOOL dataOnly);
void L2SetWriteThrough(BOOL writeThrough);
# 33 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSLC.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSLC.h" 3
void LCAllocOneTag(BOOL invalidate, void *tag);
void LCAllocTags(BOOL invalidate, void *startTag, u32 numBlocks);
void LCAlloc(void *addr, u32 nBytes);
void LCAllocNoInvalidate(void *addr, u32 nBytes);
# 34 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSMessage.h" 1 3



# 1 "extern/dolphin/include\\dolphin/os/OSThread.h" 1 3





typedef s32 OSPriority;

struct OSThread;
struct OSMutex;
struct OSMutexQueue;

typedef struct OSThread OSThread;

typedef struct OSThreadQueue
{
    struct OSThread *head;
    struct OSThread *tail;
} OSThreadQueue;

typedef struct OSThreadLink
{
    struct OSThread *next;
    struct OSThread *prev;
} OSThreadLink;

typedef struct OSMutexQueue
{
    struct OSMutex *head;
    struct OSMutex *tail;
} OSMutexQueue;

typedef struct OSMutexLink
{
    struct OSMutex *next;
    struct OSMutex *prev;
} OSMutexLink;

typedef struct OSThread
{
              struct OSContext context;
              u16 state;
              u16 attr;
              s32 suspend;
              OSPriority priority;
              OSPriority base;
              void *val;
              struct OSThreadQueue *queue;
              struct OSThreadLink link;
              struct OSThreadQueue queueJoin;
              struct OSMutex *mutex;
              struct OSMutexQueue queueMutex;
              struct OSThreadLink linkActive;
              u8 *stackBase;
              u32 *stackEnd;
} OSThread;

enum OS_THREAD_STATE
{
    OS_THREAD_STATE_READY = 1,
    OS_THREAD_STATE_RUNNING = 2,
    OS_THREAD_STATE_WAITING = 4,
    OS_THREAD_STATE_MORIBUND = 8,
};
# 73 "extern/dolphin/include\\dolphin/os/OSThread.h" 3
void OSInitThreadQueue(OSThreadQueue *queue);
void OSSleepThread(OSThreadQueue *queue);
void OSWakeupThread(OSThreadQueue *queue);
s32 OSSuspendThread(OSThread *thread);
s32 OSResumeThread(OSThread* thread);
void OSCancelThread(OSThread* thread);
OSThread* OSGetCurrentThread(void);
s32 OSEnableScheduler(void);
s32 OSDisableScheduler(void);
long OSCheckActiveThreads(void);
int OSCreateThread(struct OSThread * thread, void * (* func)(void *), void * param, void * stack, unsigned long stackSize, long priority, unsigned short attr);
# 5 "extern/dolphin/include\\dolphin/os/OSMessage.h" 2 3





struct OSMessageQueue {
    struct OSThreadQueue queueSend;
    struct OSThreadQueue queueReceive;
    void * msgArray;
    long msgCount;
    long firstIndex;
    long usedCount;
};

void OSInitMessageQueue(struct OSMessageQueue * mq, void * msgArray, long msgCount);
int OSSendMessage(struct OSMessageQueue * mq, void * msg, long flags);
int OSReceiveMessage(struct OSMessageQueue * mq, void * msg, long flags);
int OSJamMessage(struct OSMessageQueue * mq, void * msg, long flags);
# 35 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSModule.h" 1 3
# 11 "extern/dolphin/include\\dolphin/os/OSModule.h" 3
typedef struct OSModuleHeader OSModuleHeader;

typedef u32 OSModuleID;
typedef struct OSModuleQueue OSModuleQueue;
typedef struct OSModuleLink OSModuleLink;
typedef struct OSModuleInfo OSModuleInfo;
typedef struct OSSectionInfo OSSectionInfo;
typedef struct OSImportInfo OSImportInfo;
typedef struct OSRel OSRel;

struct OSModuleQueue {
  OSModuleInfo* head;
  OSModuleInfo* tail;
};

struct OSModuleLink {
  OSModuleInfo* next;
  OSModuleInfo* prev;
};

struct OSModuleInfo {
  OSModuleID id;
  OSModuleLink link;
  u32 numSections;
  u32 sectionInfoOffset;
  u32 nameOffset;
  u32 nameSize;
  u32 version;
};

struct OSModuleHeader {

  OSModuleInfo info;


  u32 bssSize;
  u32 relOffset;
  u32 impOffset;
  u32 impSize;
  u8 prologSection;
  u8 epilogSection;
  u8 unresolvedSection;
  u8 bssSection;
  u32 prolog;
  u32 epilog;
  u32 unresolved;
# 68 "extern/dolphin/include\\dolphin/os/OSModule.h" 3
};



struct OSSectionInfo {
  u32 offset;
  u32 size;
};





struct OSImportInfo {
  OSModuleID id;
  u32 offset;
};

struct OSRel {
  u16 offset;
  u8 type;
  u8 section;
  u32 addend;
};






void OSSetStringTable(const void* stringTable);
BOOL OSLink(OSModuleInfo* newModule, void* bss);



BOOL OSUnlink(OSModuleInfo* oldModule);

OSModuleInfo* OSSearchModule(void* ptr, u32* section, u32* offset);


void OSNotifyLink(void);
void OSNotifyUnlink(void);
# 36 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSMutex.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSMutex.h" 3
typedef struct OSMutex
{
             OSThreadQueue queue;
             OSThread *thread;
             s32 count;
             OSMutexLink link;
} OSMutex;

struct OSCond
{
    OSThreadQueue queue;
};

void OSInitMutex(struct OSMutex * mutex);
void OSLockMutex(struct OSMutex * mutex);
void OSUnlockMutex(struct OSMutex * mutex);
BOOL OSTryLockMutex(struct OSMutex * mutex);
void OSInitCond(struct OSCond * cond);
void OSWaitCond(struct OSCond * cond, struct OSMutex * mutex);
void OSSignalCond(struct OSCond * cond);
# 37 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSReboot.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSReboot.h" 3
typedef void (*RunCallback)(void);

void Run(RunCallback);
void __OSReboot(u32 resetCode, u32 bootDol);
# 38 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSReset.h" 1 3
# 14 "extern/dolphin/include\\dolphin/os/OSReset.h" 3
struct OSResetFunctionQueue {
    struct OSResetFunctionInfo * head;
    struct OSResetFunctionInfo * tail;
};

typedef BOOL (*OSResetFunction)(BOOL);

typedef struct OSResetFunctionInfo OSResetFunctionInfo;
struct OSResetFunctionInfo
{
    OSResetFunction func;
    u32 priority;
    OSResetFunctionInfo *next;
    OSResetFunctionInfo *prev;
};

void OSRegisterResetFunction(OSResetFunctionInfo *info);
void OSUnregisterResetFunction(OSResetFunctionInfo * info);
void OSResetSystem(int reset, u32 resetCode, BOOL forceMenu);
unsigned long OSGetResetCode();
# 39 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSResetSW.h" 1 3
# 10 "extern/dolphin/include\\dolphin/os/OSResetSW.h" 3
typedef void (*OSResetCallback)(void);

OSResetCallback OSSetResetCallback(OSResetCallback callback);
BOOL OSGetResetSwitchState();
BOOL OSGetResetButtonState(void);
# 40 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSRtc.h" 1 3
# 16 "extern/dolphin/include\\dolphin/os/OSRtc.h" 3
struct SramControl {
    unsigned char sram[64];
    unsigned long offset;
    int enabled;
    int locked;
    int sync;
    void (* callback)();
};

typedef struct OSSram {
    unsigned short checkSum;
    unsigned short checkSumInv;
    unsigned long ead0;
    unsigned long ead1;
    unsigned long counterBias;
    signed char displayOffsetH;
    unsigned char ntd;
    unsigned char language;
    unsigned char flags;
} OSSram;

typedef struct OSSramEx {
    unsigned char flashID[2][12];
    unsigned long wirelessKeyboardID;
    unsigned short wirelessPadID[4];
    unsigned char dvdErrorCode;
    unsigned char _padding0;
    unsigned char flashIDCheckSum[2];
    unsigned char _padding1[4];
} OSSramEx;

unsigned long OSGetSoundMode();
void OSSetSoundMode(unsigned long mode);
unsigned long OSGetVideoMode();
void OSSetVideoMode(unsigned long mode);
unsigned char OSGetLanguage();
void OSSetLanguage(unsigned char language);
unsigned long OSGetProgressiveMode(void);
void OSSetProgressiveMode(u32 mode);
u16 OSGetWirelessID(s32);
# 41 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSSerial.h" 1 3



# 1 "extern/dolphin/include\\dolphin/hw_regs.h" 1 3
# 5 "extern/dolphin/include\\dolphin/os/OSSerial.h" 2 3
# 30 "extern/dolphin/include\\dolphin/os/OSSerial.h" 3
typedef void (*SITypeAndStatusCallback)(long chan, unsigned long type);

struct SIControl {
    long chan;
    unsigned long poll;
    unsigned long inputBytes;
    void* input;
    void (*callback)(long, unsigned long, struct OSContext*);
};

struct SIPacket {
    long chan;
    void* output;
    unsigned long outputBytes;
    void* input;
    unsigned long inputBytes;
    void (*callback)(long, unsigned long, struct OSContext*);
    long long time;
};

int SIBusy();
BOOL SIIsChanBusy(int chan);
BOOL SIRegisterPollingHandler(__OSInterruptHandler);
BOOL SIUnregisterPollingHandler(__OSInterruptHandler);
void SIInit();
unsigned long SISync();
unsigned long SIGetStatus(int);
void SISetCommand(long chan, unsigned long command);
unsigned long SIGetCommand(long chan);
void SITransferCommands();
unsigned long SISetXY(unsigned long x, unsigned long y);
unsigned long SIEnablePolling(unsigned long poll);
unsigned long SIDisablePolling(unsigned long poll);
int SIGetResponse(long chan, void* data);
int SITransfer(long chan, void* output, unsigned long outputBytes, void* input,
               unsigned long inputBytes,
               void (*callback)(long, unsigned long, struct OSContext*),
               OSTime delay);
unsigned long SIGetType(long chan);
unsigned long SIGetTypeAsync(long chan, SITypeAndStatusCallback callback);
# 42 "extern/dolphin/include\\dolphin/os.h" 2 3
# 1 "extern/dolphin/include\\dolphin/os/OSStopwatch.h" 1 3



struct OSStopwatch {
    char * name;
    long long total;
    unsigned long hits;
    long long min;
    long long max;
    long long last;
    int running;
};

void OSInitStopwatch(struct OSStopwatch * sw, char * name);
void OSStartStopwatch(struct OSStopwatch * sw);
void OSStopStopwatch(struct OSStopwatch * sw);
long long OSCheckStopwatch(struct OSStopwatch * sw);
void OSResetStopwatch(struct OSStopwatch * sw);
void OSDumpStopwatch(struct OSStopwatch * sw);
# 43 "extern/dolphin/include\\dolphin/os.h" 2 3

# 1 "extern/dolphin/include\\dolphin/os/OSTime.h" 1 3
# 45 "extern/dolphin/include\\dolphin/os.h" 2 3







u32 OSGetPhysicalMemSize(void);
u32 OSGetConsoleSimulatedMemSize(void);
# 90 "extern/dolphin/include\\dolphin/os.h" 3
unsigned long OSGetConsoleType(void);
void OSInit(void);

void* OSGetArenaHi(void);
void* OSGetArenaLo(void);
void OSSetArenaHi(void*);
void OSSetArenaLo(void*);
void* OSAllocFromArenaLo(u32 size, u32 align);
void* OSAllocFromArenaHi(u32 size, u32 align);

u32 OSGetPhysicalMemSize(void);

void __OSPSInit();
u32 __OSGetDIConfig(void);

typedef struct OSCalendarTime {
             int sec;
             int min;
             int hour;
             int mday;
             int mon;
             int year;
             int wday;
             int yday;
             int msec;
             int usec;
} OSCalendarTime;

# 1 "extern/dolphin/include\\dolphin/dvd.h" 1 3





typedef struct DVDDiskID
{
    char gameName[4];
    char company[2];
    u8 diskNumber;
    u8 gameVersion;
    u8 streaming;
    u8 streamingBufSize;
    u8 padding[22];
} DVDDiskID;

typedef struct DVDCommandBlock DVDCommandBlock;
typedef void (*DVDCBCallback)(s32 result, DVDCommandBlock *block);
struct DVDCommandBlock
{
             DVDCommandBlock *next;
             DVDCommandBlock *prev;
             u32 command;
             s32 state;
             u32 offset;
             u32 length;
             void *addr;
             u32 currTransferSize;
             u32 transferredSize;
             DVDDiskID *id;
             DVDCBCallback callback;
             void *userData;
};

typedef struct DVDFileInfo DVDFileInfo;
typedef void (*DVDCallback)(s32 result, DVDFileInfo *fileInfo);
struct DVDFileInfo
{
          DVDCommandBlock cb;
             u32 startAddr;
             u32 length;
             DVDCallback callback;
};

typedef struct
{
    u32 entryNum;
    u32 location;
    u32 next;
} DVDDir;

typedef struct
{
    u32 entryNum;
    BOOL isDir;
    char *name;
} DVDDirEntry;

typedef struct DVDBB2 {
               u32 bootFilePosition;
               u32 FSTPosition;
               u32 FSTLength;
               u32 FSTMaxLength;
               void * FSTAddress;
               u32 userPosition;
               u32 userLength;
               u32 padding0;
} DVDBB2;

typedef struct DVDDriveInfo {
               u16 revisionLevel;
               u16 deviceCode;
               u32 releaseDate;
               u8 padding[24];
} DVDDriveInfo;

void DVDDumpWaitingQueue(void);
int DVDLowRead(void * addr, unsigned long length, unsigned long offset, void (* callback)(unsigned long));
int DVDLowSeek(unsigned long offset, void (* callback)(unsigned long));
int DVDLowWaitCoverClose(void (* callback)(unsigned long));
int DVDLowReadDiskID(struct DVDDiskID * diskID, void (* callback)(unsigned long));
int DVDLowStopMotor(void (* callback)(unsigned long));
int DVDLowRequestError(void (* callback)(unsigned long));
int DVDLowInquiry(struct DVDDriveInfo * info, void (* callback)(unsigned long));
int DVDLowAudioStream(unsigned long subcmd, unsigned long length, unsigned long offset, void (* callback)(unsigned long));
int DVDLowRequestAudioStatus(unsigned long subcmd, void (* callback)(unsigned long));
int DVDLowAudioBufferConfig(int enable, unsigned long size, void (* callback)(unsigned long));
void DVDLowReset();
void (* DVDLowSetResetCoverCallback(void (* callback)(unsigned long)))(unsigned long);
int DVDLowBreak();
void (* DVDLowClearCallback())(unsigned long);
unsigned long DVDLowGetCoverStatus();


void DVDInit();
int DVDReadAbsAsyncPrio(struct DVDCommandBlock * block, void * addr, long length, long offset, void (* callback)(long, struct DVDCommandBlock *), long prio);
int DVDSeekAbsAsyncPrio(struct DVDCommandBlock * block, long offset, void (* callback)(long, struct DVDCommandBlock *), long prio);
int DVDReadAbsAsyncForBS(struct DVDCommandBlock * block, void * addr, long length, long offset, void (* callback)(long, struct DVDCommandBlock *));
int DVDReadDiskID(struct DVDCommandBlock * block, struct DVDDiskID * diskID, void (* callback)(long, struct DVDCommandBlock *));
int DVDPrepareStreamAbsAsync(struct DVDCommandBlock * block, unsigned long length, unsigned long offset, void (* callback)(long, struct DVDCommandBlock *));
int DVDCancelStreamAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDCancelStream(struct DVDCommandBlock * block);
int DVDStopStreamAtEndAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDStopStreamAtEnd(struct DVDCommandBlock * block);
int DVDGetStreamErrorStatusAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDGetStreamErrorStatus(struct DVDCommandBlock * block);
int DVDGetStreamPlayAddrAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDGetStreamPlayAddr(struct DVDCommandBlock * block);
int DVDGetStreamStartAddrAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDGetStreamStartAddr(struct DVDCommandBlock * block);
int DVDGetStreamLengthAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDGetStreamLength(struct DVDCommandBlock * block);
int DVDChangeDiskAsyncForBS(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
int DVDChangeDiskAsync(struct DVDCommandBlock * block, struct DVDDiskID * id, void (* callback)(long, struct DVDCommandBlock *));
long DVDChangeDisk(struct DVDCommandBlock * block, struct DVDDiskID * id);
int DVDInquiryAsync(struct DVDCommandBlock * block, struct DVDDriveInfo * info, void (* callback)(long, struct DVDCommandBlock *));
long DVDInquiry(struct DVDCommandBlock * block, struct DVDDriveInfo * info);
void DVDReset();
int DVDResetRequired();
long DVDGetCommandBlockStatus(struct DVDCommandBlock * block);
long DVDGetDriveStatus();
int DVDSetAutoInvalidation(int autoInval);
void DVDPause();
void DVDResume();
int DVDCancelAsync(struct DVDCommandBlock * block, void (* callback)(long, struct DVDCommandBlock *));
long DVDCancel(volatile struct DVDCommandBlock * block);
int DVDCancelAllAsync(DVDCBCallback callback);
long DVDCancelAll(void);
struct DVDDiskID * DVDGetCurrentDiskID(void);
BOOL DVDCheckDisk(void);


s32 DVDConvertPathToEntrynum(const char* pathPtr);
BOOL DVDFastOpen(s32 entrynum, DVDFileInfo* fileInfo);
BOOL DVDOpen(char* fileName, DVDFileInfo* fileInfo);
BOOL DVDClose(DVDFileInfo* fileInfo);
BOOL DVDGetCurrentDir(char* path, u32 maxlen);
BOOL DVDChangeDir(char* dirName);
BOOL DVDReadAsyncPrio(DVDFileInfo* fileInfo, void* addr, s32 length, s32 offset,
                      DVDCallback callback, s32 prio);
long DVDReadPrio(struct DVDFileInfo * fileInfo, void * addr, long length, long offset, long prio);
int DVDSeekAsyncPrio(struct DVDFileInfo * fileInfo, long offset, void (* callback)(long, struct DVDFileInfo *), long prio);
long DVDSeekPrio(struct DVDFileInfo * fileInfo, long offset, long prio);
long DVDGetFileInfoStatus(struct DVDFileInfo * fileInfo);
int DVDOpenDir(char * dirName, DVDDir * dir);
int DVDReadDir(DVDDir * dir, DVDDirEntry* dirent);
int DVDCloseDir(DVDDir* dir);
void * DVDGetFSTLocation();
BOOL DVDPrepareStreamAsync(DVDFileInfo* fileInfo, u32 length, u32 offset, DVDCallback callback);
s32 DVDPrepareStream(DVDFileInfo* fileInfo, u32 length, u32 offset);
s32 DVDGetTransferredSize(DVDFileInfo* fileinfo);
# 203 "extern/dolphin/include\\dolphin/dvd.h" 3
extern int DVDReadAbsAsyncForBS(struct DVDCommandBlock * block, void * addr, long length, long offset, void (* callback)(long, struct DVDCommandBlock *));
extern int DVDReadDiskID(struct DVDCommandBlock * block, struct DVDDiskID * diskID, void (* callback)(long, struct DVDCommandBlock *));
extern void DVDReset(void);

int DVDReadAbsAsyncPrio(struct DVDCommandBlock * block , void * addr , long length , long offset , void (* callback)(long, struct DVDCommandBlock *) , long prio );
int DVDSeekAbsAsyncPrio(struct DVDCommandBlock * block , long offset , void (* callback)(long, struct DVDCommandBlock *) , long prio );
int DVDPrepareStreamAbsAsync(struct DVDCommandBlock * block , unsigned long length , unsigned long offset , void (* callback)(long, struct DVDCommandBlock *) );
void __DVDStoreErrorCode(u32 error);
# 119 "extern/dolphin/include\\dolphin/os.h" 2 3

typedef struct OSBootInfo_s {

    DVDDiskID DVDDiskID;
    unsigned long magic;
    unsigned long version;
    unsigned long memorySize;
    unsigned long consoleType;
    void* arenaLo;
    void* arenaHi;
    void* FSTLocation;
    unsigned long FSTMaxLength;
} OSBootInfo;

OSTick OSGetTick(void);
OSTime OSGetTime(void);
void OSTicksToCalendarTime(OSTime ticks, OSCalendarTime* td);
OSTime OSCalendarTimeToTicks(OSCalendarTime* td);
BOOL OSEnableInterrupts(void);
BOOL OSDisableInterrupts(void);
BOOL OSRestoreInterrupts(BOOL level);
# 166 "extern/dolphin/include\\dolphin/os.h" 3
u32 OSGetSoundMode(void);
void OSSetSoundMode(u32 mode);
# 177 "extern/dolphin/include\\dolphin/os.h" 3
void OSReport(char*, ...);
__attribute__((noreturn)) void OSPanic(char* file, int line, char* msg, ...);




void* OSPhysicalToCached(u32 paddr);
void* OSPhysicalToUncached(u32 paddr);
u32 OSCachedToPhysical(void* caddr);
u32 OSUncachedToPhysical(void* ucaddr);
void* OSCachedToUncached(void* caddr);
void* OSUncachedToCached(void* ucaddr);
# 7 "src\\sysdolphin/baselib/debug.h" 2

typedef void (*ReportCallback)(const unsigned char*, size_t);
typedef void (*PanicCallback)(OSContext*, ...);

__attribute__((noreturn)) void __assert(char*, u32, char*);

void HSD_LogInit(void);
__attribute__((noreturn)) void HSD_Panic(char*, u32, char*);
# 35 "src\\sysdolphin/baselib/debug.h"
void HSD_SetReportCallback(ReportCallback cb);
void HSD_SetPanicCallback(PanicCallback cb);
# 10 "src\\sysdolphin/baselib/object.h" 2








typedef enum _HSD_Type {
    AOBJ_TYPE = 1,
    COBJ_TYPE,
    DOBJ_TYPE,
    FOBJ_TYPE,
    FOG_TYPE,
    JOBJ_TYPE,
    LOBJ_TYPE,
    MOBJ_TYPE,
    POBJ_TYPE,
    ROBJ_TYPE,
    TOBJ_TYPE,
    WOBJ_TYPE,
    RENDER_TYPE,
    CHAN_TYPE,
    TEVREG_TYPE,
    CBOBJ_TYPE,
    HSD_MAX_TYPE,
} HSD_Type;



typedef enum _HSD_TypeMask {
    AOBJ_MASK = (1 << ((AOBJ_TYPE) - 1)),
    COBJ_MASK = (1 << ((COBJ_TYPE) - 1)),
    DOBJ_MASK = (1 << ((DOBJ_TYPE) - 1)),
    FOBJ_MASK = (1 << ((FOBJ_TYPE) - 1)),
    FOG_MASK = (1 << ((FOG_TYPE) - 1)),
    JOBJ_MASK = (1 << ((JOBJ_TYPE) - 1)),
    LOBJ_MASK = (1 << ((LOBJ_TYPE) - 1)),
    MOBJ_MASK = (1 << ((MOBJ_TYPE) - 1)),
    POBJ_MASK = (1 << ((POBJ_TYPE) - 1)),
    ROBJ_MASK = (1 << ((ROBJ_TYPE) - 1)),
    TOBJ_MASK = (1 << ((TOBJ_TYPE) - 1)),
    WOBJ_MASK = (1 << ((WOBJ_TYPE) - 1)),
    RENDER_MASK = (1 << ((RENDER_TYPE) - 1)),
    CHAN_MASK = (1 << ((CHAN_TYPE) - 1)),
    TEVREG_MASK = (1 << ((TEVREG_TYPE) - 1)),
    CBOBJ_MASK = (1 << ((CBOBJ_TYPE) - 1)),
    ALL_TYPE_MASK = (1 << ((HSD_MAX_TYPE) - 1)) - 1,
} HSD_TypeMask;

struct HSD_Obj {
    struct _HSD_Class parent;
    u16 ref_count;
    u16 ref_count_individual;
};

typedef struct _HSD_ObjInfo {
    struct _HSD_ClassInfo parent;
} HSD_ObjInfo;

extern HSD_ClassInfo hsdObj;

void ObjInfoInit(void);

static inline bool ref_DEC(void* o)
{
    bool ret;
    if ((ret = (((HSD_Obj*) o)->ref_count == ((u16) - 1)))) {
        return ret;
    }
    return ((HSD_Obj*) o)->ref_count-- == 0;
}

static inline void ref_INC(void* o)
{
    if (o != 0L) {
        ((HSD_Obj*) o)->ref_count++;
        ((((HSD_Obj*) o)->ref_count != ((u16) - 1)) ? ((void) 0) : __assert("src\\sysdolphin/baselib/object.h", 87, "HSD_OBJ(o)->ref_count != HSD_OBJ_NOREF"));
    }
}

static inline int ref_CNT(void* o)
{
    if (((HSD_Obj*) o)->ref_count == ((u16) - 1)) {
        return -1;
    } else {
        return ((HSD_Obj*) o)->ref_count;
    }
}

static inline int iref_CNT(void* o)
{
    return ((HSD_Obj*) o)->ref_count_individual;
}

static inline bool iref_DEC(void* o)
{
    bool ret;
    if ((ret = (((HSD_Obj*) o)->ref_count_individual == 0))) {
        return ret;
    }
    ((HSD_Obj*) o)->ref_count_individual -= 1;
    return ((HSD_Obj*) o)->ref_count_individual == 0;
}

static inline void iref_INC(void* o)
{
    ((HSD_Obj*) o)->ref_count_individual++;
    ((((HSD_Obj*) o)->ref_count_individual != 0) ? ((void) 0) : __assert("src\\sysdolphin/baselib/object.h", 118, "HSD_OBJ(o)->ref_count_individual != 0"));
}
# 11 "src/sysdolphin/baselib\\cobj.h" 2





typedef struct _Scissor {
    u16 left;
    u16 right;
    u16 top;
    u16 bottom;
} Scissor;

typedef struct _HSD_RectS16 {
    s16 xmin;
    s16 xmax;
    s16 ymin;
    s16 ymax;
} HSD_RectS16;

typedef struct _HSD_RectF32 {
    f32 xmin;
    f32 xmax;
    f32 ymin;
    f32 ymax;
} HSD_RectF32;

struct HSD_CObj {
              HSD_Obj parent;
              u32 flags;
              HSD_RectF32 viewport;
              Scissor scissor;
              HSD_WObj* eyepos;
              HSD_WObj* interest;
    union {
                  f32 roll;
                  Vec3 up;
    } u;
              f32 near;
              f32 far;
    union {
        struct {
            f32 fov;
            f32 aspect;
        } perspective;

        struct {
            f32 top;
            f32 bottom;
            f32 left;
            f32 right;
        } frustum;

        struct {
            f32 top;
            f32 bottom;
            f32 left;
            f32 right;
        } ortho;
    } projection_param;
              u8 projection_type;
              Mtx view_mtx;
              HSD_AObj* aobj;
              Mtx* proj_mtx;
};

struct HSD_CameraDescCommon {
    char* class_name;
    u16 flags;
    u16 projection_type;
    HSD_RectS16 viewport;
    Scissor scissor;
    HSD_WObjDesc* eyepos;
    HSD_WObjDesc* interest;
    f32 roll;
    Vec3* up_vector;
    f32 nnear;
    f32 ffar;
};

struct HSD_CameraDescFrustum {
    char* class_name;
    u16 flags;
    u16 projection_type;
    HSD_RectS16 viewport;
    Scissor scissor;
    HSD_WObjDesc* eyepos;
    HSD_WObjDesc* interest;
    f32 roll;
    Vec3* up_vector;
    f32 nnear;
    f32 ffar;
    f32 top;
    f32 bottom;
    f32 left;
    f32 right;
};

struct HSD_CameraDescPerspective {
    char* class_name;
    u16 flags;
    u16 projection_type;
    HSD_RectS16 viewport;
    Scissor scissor;
    HSD_WObjDesc* eyepos;
    HSD_WObjDesc* interest;
    f32 roll;
    Vec3* up_vector;
    f32 nnear;
    f32 ffar;
    f32 fov;
    f32 aspect;
};

union HSD_CObjDesc {
    char* class_name;
    HSD_CameraDescCommon common;
    HSD_CameraDescFrustum frustum;
    HSD_CameraDescFrustum ortho;
    HSD_CameraDescPerspective perspective;
};
_Static_assert((sizeof(HSD_CObjDesc) == 0x40), "(" "sizeof(HSD_CObjDesc) == 0x40" ") failed");

struct HSD_CObjInfo {
    HSD_ObjInfo parent;
    int (*load)(HSD_CObj* cobj, HSD_CObjDesc* desc);
};

struct HSD_CameraAnim {
    HSD_AObjDesc* aobjdesc;
    HSD_WObjAnim* eye_anim;
    HSD_WObjAnim* interest_anim;
};

typedef struct _cobj_Unk1 cobj_Unk1;





void HSD_CObjEraseScreen(HSD_CObj* cobj, s32 enable_color, s32 enable_alpha,
                         s32 enable_depth);
void HSD_CObjRemoveAnim(HSD_CObj* cobj);
HSD_WObj* HSD_CObjGetInterestWObj(HSD_CObj* cobj);
void HSD_CObjSetInterestWObj(HSD_CObj* cobj, HSD_WObj* interest);
HSD_WObj* HSD_CObjGetEyePositionWObj(HSD_CObj* cobj);
void HSD_CObjSetEyePositionWObj(HSD_CObj* cobj, HSD_WObj* eyepos);
void HSD_CObjSetInterest(HSD_CObj* cobj, Vec3*);
void HSD_CObjSetEyePosition(HSD_CObj* cobj, Vec3*);
bool HSD_CObjSetCurrent(HSD_CObj*);
void HSD_CObjEndCurrent(void);
void HSD_CObjSetViewportfx4(HSD_CObj*, f32, f32, f32, f32);
void HSD_CObjGetEyePosition(HSD_CObj* cobj, Vec3* cam_pos);
int HSD_CObjGetEyeVector(HSD_CObj* cobj, Vec3* eye);
int HSD_CObjGetUpVector(HSD_CObj* cobj, Vec3* up);
void HSD_CObjGetInterest(HSD_CObj* cobj, Vec3* interest);
HSD_CObj* HSD_CObjAlloc(void);

void HSD_CObjRemoveAnimByFlags(HSD_CObj* cobj, u32 flags);
void HSD_CObjAddAnim(HSD_CObj* cobj, HSD_CameraAnim* canim);
void HSD_CObjAnim(HSD_CObj* cobj);
void HSD_CObjReqAnim(HSD_CObj* cobj, f32 startframe);
GXProjectionType makeProjectionMtx(HSD_CObj* cobj, Mtx44 mtx);
void HSD_CObjSetupViewingMtx(HSD_CObj* cobj);
f32 HSD_CObjGetEyeDistance(HSD_CObj* cobj);
void HSD_CObjSetUpVector(HSD_CObj* cobj, Vec3* up);
int HSD_CObjGetLeftVector(HSD_CObj* cobj, Vec3* left);
void HSD_CObjSetMtxDirty(HSD_CObj* cobj);
bool HSD_CObjMtxIsDirty(HSD_CObj*);
void HSD_CObjGetViewingMtx(HSD_CObj* cobj, Mtx mtx);
MtxPtr HSD_CObjGetInvViewingMtxPtrDirect(HSD_CObj* cobj);
MtxPtr HSD_CObjGetViewingMtxPtr(HSD_CObj* cobj);
MtxPtr HSD_CObjGetInvViewingMtxPtr(HSD_CObj* cobj);
void HSD_CObjSetRoll(HSD_CObj* cobj, f32);
f32 HSD_CObjGetFov(HSD_CObj* cobj);
void HSD_CObjSetFov(HSD_CObj*, f32);
f32 HSD_CObjGetAspect(HSD_CObj* cobj);
void HSD_CObjSetAspect(HSD_CObj* cobj, f32 aspect);
f32 HSD_CObjGetTop(HSD_CObj* cobj);
void HSD_CObjSetTop(HSD_CObj* cobj, f32 top);
f32 HSD_CObjGetBottom(HSD_CObj* cobj);
void HSD_CObjSetBottom(HSD_CObj* cobj, f32 bottom);
f32 HSD_CObjGetLeft(HSD_CObj* cobj);
void HSD_CObjSetLeft(HSD_CObj* cobj, f32 left);
f32 HSD_CObjGetRight(HSD_CObj* cobj);
void HSD_CObjSetRight(HSD_CObj* cobj, f32 right);
f32 HSD_CObjGetNear(HSD_CObj*);
void HSD_CObjSetNear(HSD_CObj* cobj, f32 near);
f32 HSD_CObjGetFar(HSD_CObj*);
void HSD_CObjSetFar(HSD_CObj* cobj, f32 far);
void HSD_CObjGetScissor(HSD_CObj* cobj, Scissor*);
void HSD_CObjSetScissor(HSD_CObj* cobj, Scissor*);
void HSD_CObjSetScissorx4(HSD_CObj*, u16 left, u16 right, u16 top, u16 bottom);
void HSD_CObjGetViewportf(HSD_CObj* cobj, HSD_RectF32*);
void HSD_CObjSetViewport(HSD_CObj* cobj, HSD_RectS16* viewport);
void HSD_CObjSetViewportf(HSD_CObj* cobj, HSD_RectF32*);
int HSD_CObjGetProjectionType(HSD_CObj*);
void HSD_CObjSetProjectionType(HSD_CObj*, u32);
void HSD_CObjSetPerspective(HSD_CObj* cobj, f32 fov, f32 aspect);
void HSD_CObjSetFrustum(HSD_CObj*, f32 top, f32 bottom, f32 left, f32 right);
void HSD_CObjSetOrtho(HSD_CObj*, f32 top, f32 bottom, f32 left, f32 right);
void HSD_CObjGetPerspective(HSD_CObj* cobj, f32* top, f32* bottom);
void HSD_CObjGetOrtho(HSD_CObj*, f32* top, f32* bottom, f32* left, f32* right);
u32 HSD_CObjGetFlags(HSD_CObj* cobj);
void HSD_CObjSetFlags(HSD_CObj*, u32);
void HSD_CObjClearFlags(HSD_CObj*, u32);
HSD_CObj* HSD_CObjGetCurrent(void);
void HSD_CObjInit(HSD_CObj* cobj, HSD_CObjDesc* desc);
HSD_CObj* HSD_CObjLoadDesc(HSD_CObjDesc* desc);
void HSD_CObjSetDefaultClass(HSD_ClassInfo* info);

static inline MtxPtr HSD_CObjGetViewingMtxPtrDirect(HSD_CObj* cobj)
{
    return cobj->view_mtx;
}
# 6 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\fog.h" 1







# 1 "extern/dolphin/include\\dolphin/gx.h" 1 3




# 1 "extern/dolphin/include\\dolphin/gx/GXBump.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXBump.h" 3
void GXSetTevIndirect(GXTevStageID tev_stage, GXIndTexStageID ind_stage, GXIndTexFormat format, GXIndTexBiasSel bias_sel, GXIndTexMtxID matrix_sel, GXIndTexWrap wrap_s, GXIndTexWrap wrap_t, GXBool add_prev, GXBool utc_lod, GXIndTexAlphaSel alpha_sel);
void GXSetIndTexMtx(GXIndTexMtxID mtx_id, f32 offset[2][3], s8 scale_exp);
void GXSetIndTexCoordScale(GXIndTexStageID ind_state, GXIndTexScale scale_s, GXIndTexScale scale_t);
void GXSetIndTexOrder(GXIndTexStageID ind_stage, GXTexCoordID tex_coord, GXTexMapID tex_map);
void GXSetNumIndStages(u8 nIndStages);
void GXSetTevDirect(GXTevStageID tev_stage);
void GXSetTevIndWarp(GXTevStageID tev_stage, GXIndTexStageID ind_stage, u8 signed_offset, u8 replace_mode, GXIndTexMtxID matrix_sel);
void GXSetTevIndTile(GXTevStageID tev_stage, GXIndTexStageID ind_stage, u16 tilesize_s,
    u16 tilesize_t, u16 tilespacing_s, u16 tilespacing_t, GXIndTexFormat format,
    GXIndTexMtxID matrix_sel, GXIndTexBiasSel bias_sel, GXIndTexAlphaSel alpha_sel);
void GXSetTevIndBumpST(GXTevStageID tev_stage, GXIndTexStageID ind_stage, GXIndTexMtxID matrix_sel);
void GXSetTevIndBumpXYZ(GXTevStageID tev_stage, GXIndTexStageID ind_stage, GXIndTexMtxID matrix_sel);
void GXSetTevIndRepeat(GXTevStageID tev_stage);
# 6 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXCommandList.h" 1 3
# 26 "extern/dolphin/include\\dolphin/gx/GXCommandList.h" 3
extern u8 GXTexMode0Ids[8];
extern u8 GXTexMode1Ids[8];
extern u8 GXTexImage0Ids[8];
extern u8 GXTexImage1Ids[8];
extern u8 GXTexImage2Ids[8];
extern u8 GXTexImage3Ids[8];
extern u8 GXTexTlutIds[8];
# 7 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXCpu2Efb.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXCpu2Efb.h" 3
void GXPokeAlphaMode(GXCompare func, u8 threshold);
void GXPokeAlphaRead(GXAlphaReadMode mode);
void GXPokeAlphaUpdate(GXBool update_enable);
void GXPokeBlendMode(GXBlendMode type, GXBlendFactor src_factor, GXBlendFactor dst_factor, GXLogicOp op);
void GXPokeColorUpdate(GXBool update_enable);
void GXPokeDstAlpha(GXBool enable, u8 alpha);
void GXPokeDither(GXBool dither);
void GXPokeZMode(GXBool compare_enable, GXCompare func, GXBool update_enable);
void GXPeekARGB(u16 x, u16 y, u32 *color);
void GXPokeARGB(u16 x, u16 y, u32 color);
void GXPeekZ(u16 x, u16 y, u32 *z);
void GXPokeZ(u16 x, u16 y, u32 z);
u32 GXCompressZ16(u32 z24, GXZFmt16 zfmt);
u32 GXDecompressZ16(u32 z16, GXZFmt16 zfmt);
# 8 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXCull.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXCull.h" 3
void GXSetScissor(u32 left, u32 top, u32 wd, u32 ht);
void GXSetCullMode(GXCullMode mode);
void GXSetCoPlanar(GXBool enable);
# 9 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXDispList.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXDispList.h" 3
void GXBeginDisplayList(void *list, u32 size);
u32 GXEndDisplayList(void);
void GXCallDisplayList( void *list, u32 nbytes);
# 10 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXDraw.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXDraw.h" 3
void GXDrawCylinder(u8 numEdges);
void GXDrawTorus(f32 rc, u8 numc, u8 numt);
void GXDrawSphere(u8 numMajor, u8 numMinor);
void GXDrawCube(void);
void GXDrawDodeca(void);
void GXDrawOctahedron(void);
void GXDrawIcosahedron(void);
void GXDrawSphere1(u8 depth);
u32 GXGenNormalTable(u8 depth, f32 *table);
# 11 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXFifo.h" 1 3
# 11 "extern/dolphin/include\\dolphin/gx/GXFifo.h" 3
typedef struct
{
    u8 pad[128];
} GXFifoObj;

typedef void (*GXBreakPtCallback)(void);

void GXInitFifoBase(GXFifoObj *fifo, void *base, u32 size);
void GXInitFifoPtrs(GXFifoObj *fifo, void *readPtr, void *writePtr);
void GXInitFifoLimits(GXFifoObj *fifo, u32 hiWatermark, u32 loWatermark);
void GXSetCPUFifo(GXFifoObj *fifo);
void GXSetGPFifo(GXFifoObj *fifo);
void GXSaveCPUFifo(GXFifoObj *fifo);
void GXSaveGPFifo(GXFifoObj *fifo);
void GXGetGPStatus(GXBool *overhi, GXBool *underlow, GXBool *readIdle, GXBool *cmdIdle, GXBool *brkpt);
void GXGetFifoStatus(GXFifoObj *fifo, GXBool *overhi, GXBool *underflow, u32 *fifoCount, GXBool *cpuWrite, GXBool *gpRead, GXBool *fifowrap);
void GXGetFifoPtrs(GXFifoObj *fifo, void **readPtr, void **writePtr);
void *GXGetFifoBase(GXFifoObj *fifo);
u32 GXGetFifoSize(GXFifoObj *fifo);
void GXGetFifoLimits(GXFifoObj *fifo, u32 *hi, u32 *lo);
GXBreakPtCallback GXSetBreakPtCallback(GXBreakPtCallback cb);
void GXEnableBreakPt(void *break_pt);
void GXDisableBreakPt(void);
OSThread *GXSetCurrentGXThread(void);
OSThread *GXGetCurrentGXThread(void);
GXFifoObj *GXGetCPUFifo(void);
GXFifoObj *GXGetGPFifo(void);
u32 GXGetOverflowCount(void);
u32 GXResetOverflowCount(void);
volatile void *GXRedirectWriteGatherPipe(void *ptr);
void GXRestoreWriteGatherPipe(void);
# 12 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXFrameBuffer.h" 1 3



# 1 "extern/dolphin/include\\dolphin/gx/GXStruct.h" 1 3




# 1 "extern/dolphin/include\\dolphin/vi/vitypes.h" 1 3
# 19 "extern/dolphin/include\\dolphin/vi/vitypes.h" 3
typedef enum
{
    VI_TVMODE_NTSC_INT = (((0) << 2) + (0)),
    VI_TVMODE_NTSC_DS = (((0) << 2) + (1)),
    VI_TVMODE_NTSC_PROG = (((0) << 2) + (2)),
    VI_TVMODE_PAL_INT = (((1) << 2) + (0)),
    VI_TVMODE_PAL_DS = (((1) << 2) + (1)),
    VI_TVMODE_EURGB60_INT = (((5) << 2) + (0)),
    VI_TVMODE_EURGB60_DS = (((5) << 2) + (1)),
    VI_TVMODE_MPAL_INT = (((2) << 2) + (0)),
    VI_TVMODE_MPAL_DS = (((2) << 2) + (1)),
    VI_TVMODE_DEBUG_INT = (((3) << 2) + (0)),
    VI_TVMODE_DEBUG_PAL_INT = (((4) << 2) + (0)),
    VI_TVMODE_DEBUG_PAL_DS = (((4) << 2) + (1)),
    VI_TVMODE_3 = 3,
} VITVMode;

typedef enum
{
    VI_XFBMODE_SF = 0,
    VI_XFBMODE_DF
} VIXFBMode;

typedef void (*VIRetraceCallback)(u32 retraceCount);
# 6 "extern/dolphin/include\\dolphin/gx/GXStruct.h" 2 3





typedef struct _GXRenderModeObj
{
             VITVMode viTVmode;
             u16 fbWidth;
             u16 efbHeight;
             u16 xfbHeight;
             u16 viXOrigin;
             u16 viYOrigin;
             u16 viWidth;
             u16 viHeight;
             VIXFBMode xFBmode;
             u8 field_rendering;
             u8 aa;
             u8 sample_pattern[12][2];
             u8 vfilter[7];
} GXRenderModeObj;

typedef struct _GXColor
{
    u8 r, g, b, a;
} GXColor;

typedef struct _GXColorS10
{
    s16 r, g, b, a;
} GXColorS10;

typedef struct _GXTexObj
{
    u32 dummy[8];
} GXTexObj;

typedef struct _GXLightObj
{
    u32 dummy[16];
} GXLightObj;

typedef struct _GXTexRegion
{
    u32 dummy[4];
} GXTexRegion;

typedef struct _GXTlutObj
{
    u32 dummy[3];
} GXTlutObj;

typedef struct _GXTlutRegion
{
    u32 dummy[4];
} GXTlutRegion;

typedef struct _GXFogAdjTable
{
    u16 r[10];
} GXFogAdjTable;

typedef struct _GXVtxDescList {
    GXAttr attr;
    GXAttrType type;
} GXVtxDescList;

typedef struct _GXVtxAttrFmtList {
    GXAttr attr;
    GXCompCnt cnt;
    GXCompType type;
    u8 frac;
} GXVtxAttrFmtList;
# 5 "extern/dolphin/include\\dolphin/gx/GXFrameBuffer.h" 2 3








extern GXRenderModeObj GXNtsc240Ds;
extern GXRenderModeObj GXNtsc240DsAa;
extern GXRenderModeObj GXNtsc240Int;
extern GXRenderModeObj GXNtsc240IntAa;
extern GXRenderModeObj GXNtsc480IntDf;
extern GXRenderModeObj GXNtsc480Int;
extern GXRenderModeObj GXNtsc480IntAa;
extern GXRenderModeObj GXNtsc480Prog;
extern GXRenderModeObj GXNtsc480ProgAa;
extern GXRenderModeObj GXMpal240Ds;
extern GXRenderModeObj GXMpal240DsAa;
extern GXRenderModeObj GXMpal240Int;
extern GXRenderModeObj GXMpal240IntAa;
extern GXRenderModeObj GXMpal480IntDf;
extern GXRenderModeObj GXMpal480Int;
extern GXRenderModeObj GXMpal480IntAa;
extern GXRenderModeObj GXPal264Ds;
extern GXRenderModeObj GXPal264DsAa;
extern GXRenderModeObj GXPal264Int;
extern GXRenderModeObj GXPal264IntAa;
extern GXRenderModeObj GXPal528IntDf;
extern GXRenderModeObj GXPal528Int;
extern GXRenderModeObj GXPal528IntAa;

void GXAdjustForOverscan(GXRenderModeObj *rmin, GXRenderModeObj *rmout, u16 hor, u16 ver);
void GXSetDispCopySrc(u16 left, u16 top, u16 wd, u16 ht);
void GXSetTexCopySrc(u16 left, u16 top, u16 wd, u16 ht);
void GXSetDispCopyDst(u16 wd, u16 ht);
void GXSetTexCopyDst(u16 wd, u16 ht, GXTexFmt fmt, GXBool mipmap);
void GXSetDispCopyFrame2Field(GXCopyMode mode);
void GXSetCopyClamp(GXFBClamp clamp);
u32 GXSetDispCopyYScale(f32 vscale);
void GXSetCopyClear(GXColor clear_clr, u32 clear_z);
void GXSetCopyFilter(GXBool aa, const u8 sample_pattern[12][2], GXBool vf, const u8 vfilter[7]);
void GXSetDispCopyGamma(GXGamma gamma);
void GXCopyDisp(void *dest, GXBool clear);
void GXCopyTex(void *dest, GXBool clear);
void GXClearBoundingBox(void);
void GXReadBoundingBox(u16 *left, u16 *top, u16 *right, u16 *bottom);
# 13 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXGeometry.h" 1 3
# 13 "extern/dolphin/include\\dolphin/gx/GXGeometry.h" 3
void GXSetVtxDesc(GXAttr attr, GXAttrType type);
void GXSetVtxDescv(const GXVtxDescList *attrPtr);
void GXClearVtxDesc(void);
void GXSetVtxAttrFmt(GXVtxFmt vtxfmt, GXAttr attr, GXCompCnt cnt, GXCompType type, u8 frac);
void GXSetVtxAttrFmtv(GXVtxFmt vtxfmt, const GXVtxAttrFmtList *list);
void GXSetArray(GXAttr attr, const void *base_ptr, u8 stride);
void GXInvalidateVtxCache(void);
void GXSetTexCoordGen2(GXTexCoordID dst_coord, GXTexGenType func, GXTexGenSrc src_param, u32 mtx, GXBool normalize, u32 pt_texmtx);
void GXSetNumTexGens(u8 nTexGens);

static inline void GXSetTexCoordGen(GXTexCoordID dst_coord, GXTexGenType func,
    GXTexGenSrc src_param, u32 mtx)
{
    GXSetTexCoordGen2(dst_coord, func, src_param, mtx, ((GXBool)0), GX_PTIDENTITY);
}

void GXBegin(GXPrimitive type, GXVtxFmt vtxfmt, u16 nverts);
static inline void GXEnd(void)
{
# 40 "extern/dolphin/include\\dolphin/gx/GXGeometry.h" 3
}
void GXSetLineWidth(u8 width, GXTexOffset texOffsets);
void GXSetPointSize(u8 pointSize, GXTexOffset texOffsets);
void GXEnableTexOffsets(GXTexCoordID coord, u8 line_enable, u8 point_enable);
# 14 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXGet.h" 1 3
# 12 "extern/dolphin/include\\dolphin/gx/GXGet.h" 3
void GXGetVtxDesc(GXAttr attr, GXAttrType *type);
void GXGetVtxDescv(GXVtxDescList *vcd);
void GXGetVtxAttrFmt(GXVtxFmt fmt, GXAttr attr, GXCompCnt *cnt, GXCompType *type, u8 *frac);
void GXGetVtxAttrFmtv(GXVtxFmt fmt, GXVtxAttrFmtList *vat);


void GXGetLineWidth(u8 *width, GXTexOffset *texOffsets);
void GXGetPointSize(u8 *pointSize, GXTexOffset *texOffsets);
void GXGetCullMode(GXCullMode *mode);


void GXGetLightAttnA(GXLightObj *lt_obj, f32 *a0, f32 *a1, f32 *a2);
void GXGetLightAttnK(GXLightObj *lt_obj, f32 *k0, f32 *k1, f32 *k2);
void GXGetLightPos(GXLightObj *lt_obj, f32 *x, f32 *y, f32 *z);
void GXGetLightDir(GXLightObj *lt_obj, f32 *nx, f32 *ny, f32 *nz);
void GXGetLightColor(GXLightObj *lt_obj, GXColor *color);


GXBool GXGetTexObjMipMap(const GXTexObj *to);
GXTexFmt GXGetTexObjFmt(const GXTexObj *to);
u16 GXGetTexObjWidth(const GXTexObj *to);
u16 GXGetTexObjHeight(const GXTexObj *to);
GXTexWrapMode GXGetTexObjWrapS(const GXTexObj *to);
GXTexWrapMode GXGetTexObjWrapT(const GXTexObj *to);
void *GXGetTexObjData(const GXTexObj *to);;
void GXGetTexObjAll(const GXTexObj *obj, void **image_ptr, u16 *width, u16 *height, GXTexFmt *format, GXTexWrapMode *wrap_s, GXTexWrapMode *wrap_t, u8 *mipmap);
void GXGetTexObjLODAll(const GXTexObj *tex_obj, GXTexFilter *min_filt, GXTexFilter *mag_filt, f32 *min_lod, f32 *max_lod, f32 *lod_bias, u8 *bias_clamp, u8 *do_edge_lod, GXAnisotropy *max_aniso);
GXTexFilter GXGetTexObjMinFilt(const GXTexObj *tex_obj);
GXTexFilter GXGetTexObjMagFilt(const GXTexObj *tex_obj);
f32 GXGetTexObjMinLOD(const GXTexObj *tex_obj);
f32 GXGetTexObjMaxLOD(const GXTexObj *tex_obj);
f32 GXGetTexObjLODBias(const GXTexObj *tex_obj);
GXBool GXGetTexObjBiasClamp(const GXTexObj *tex_obj);
GXBool GXGetTexObjEdgeLOD(const GXTexObj *tex_obj);
GXAnisotropy GXGetTexObjMaxAniso(const GXTexObj *tex_obj);
u32 GXGetTexObjTlut(const GXTexObj *tex_obj);
void GXGetTlutObjAll(const GXTlutObj *tlut_obj, void **data, GXTlutFmt *format, u16 *numEntries);
void *GXGetTlutObjData(const GXTlutObj *tlut_obj);
GXTlutFmt GXGetTlutObjFmt(const GXTlutObj *tlut_obj);
u16 GXGetTlutObjNumEntries(const GXTlutObj *tlut_obj);
void GXGetTexRegionAll(const GXTexRegion *region, u8 *is_cached, u8 *is_32b_mipmap, u32 *tmem_even, u32 *size_even, u32 *tmem_odd, u32 *size_odd);
void GXGetTlutRegionAll(const GXTlutRegion *region, u32 *tmem_addr, GXTlutSize *tlut_size);


void GXGetProjectionv(f32 *ptr);
void GXGetViewportv(f32 *vp);
void GXGetScissor(u32 *left, u32 *top, u32 *wd, u32 *ht);
# 15 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXLighting.h" 1 3
# 11 "extern/dolphin/include\\dolphin/gx/GXLighting.h" 3
void GXInitLightAttn(GXLightObj *lt_obj, f32 a0, f32 a1, f32 a2, f32 k0, f32 k1, f32 k2);
void GXInitLightAttnA(GXLightObj *lt_obj, f32 a0, f32 a1, f32 a2);
void GXInitLightAttnK(GXLightObj *lt_obj, f32 k0, f32 k1, f32 k2);
void GXInitLightSpot(GXLightObj *lt_obj, f32 cutoff, GXSpotFn spot_func);
void GXInitLightDistAttn(GXLightObj *lt_obj, f32 ref_dist, f32 ref_br, GXDistAttnFn dist_func);
void GXInitLightPos(GXLightObj *lt_obj, f32 x, f32 y, f32 z);
void GXInitLightDir(GXLightObj *lt_obj, f32 nx, f32 ny, f32 nz);
void GXInitSpecularDir(GXLightObj *lt_obj, f32 nx, f32 ny, f32 nz);
void GXInitSpecularDirHA(GXLightObj *lt_obj, f32 nx, f32 ny, f32 nz, f32 hx, f32 hy, f32 hz);
void GXInitLightColor(GXLightObj *lt_obj, GXColor color);
void GXLoadLightObjImm(GXLightObj *lt_obj, GXLightID light);
void GXLoadLightObjIndx(u32 lt_obj_indx, GXLightID light);
void GXSetChanAmbColor(GXChannelID chan, GXColor amb_color);
void GXSetChanMatColor(GXChannelID chan, GXColor mat_color);
void GXSetNumChans(u8 nChans);
void GXSetChanCtrl(GXChannelID chan, GXBool enable, GXColorSrc amb_src,
    GXColorSrc mat_src, u32 light_mask, GXDiffuseFn diff_fn, GXAttnFn attn_fn);
# 16 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXManage.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXManage.h" 3
typedef void (*GXDrawSyncCallback)(u16 token);
typedef void (*GXDrawDoneCallback)(void);


BOOL IsWriteGatherBufferEmpty(void);
GXFifoObj *GXInit(void *base, u32 size);


void GXSetMisc(GXMiscToken token, u32 val);
void GXFlush(void);
void GXResetWriteGatherPipe(void);
void GXAbortFrame(void);
void GXSetDrawSync(u16 token);
u16 GXReadDrawSync(void);
void GXSetDrawDone(void);
void GXWaitDrawDone(void);
void GXDrawDone(void);
void GXPixModeSync(void);
void GXTexModeSync(void);
GXDrawSyncCallback GXSetDrawSyncCallback(GXDrawSyncCallback cb);
GXDrawDoneCallback GXSetDrawDoneCallback(GXDrawDoneCallback cb);
# 17 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXPerf.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXPerf.h" 3
void GXSetGPMetric(GXPerf0 perf0, GXPerf1 perf1);
void GXReadGPMetric(u32 *cnt0, u32 *cnt1);
void GXClearGPMetric(void);
u32 GXReadGP0Metric(void);
u32 GXReadGP1Metric(void);
void GXReadMemMetric(u32 *cp_req, u32 *tc_req, u32 *cpu_rd_req, u32 *cpu_wr_req, u32 *dsp_req, u32 *io_req, u32 *vi_req, u32 *pe_req, u32 *rf_req, u32 *fi_req);
void GXClearMemMetric(void);
void GXReadPixMetric(u32 *top_pixels_in, u32 *top_pixels_out, u32 *bot_pixels_in, u32 *bot_pixels_out, u32 *clr_pixels_in, u32 *copy_clks);
void GXClearPixMetric(void);
void GXSetVCacheMetric(GXVCachePerf attr);
void GXReadVCacheMetric(u32 *check, u32 *miss, u32 *stall);
void GXClearVCacheMetric(void);
void GXInitXfRasMetric(void);
void GXReadXfRasMetric(u32 *xf_wait_in, u32 *xf_wait_out, u32 *ras_busy, u32 *clocks);
u32 GXReadClksPerVtx(void);
# 18 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXPixel.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXPixel.h" 3
void GXSetFog(GXFogType type, f32 startz, f32 endz, f32 nearz, f32 farz, GXColor color);
void GXInitFogAdjTable(GXFogAdjTable *table, u16 width, f32 projmtx[4][4]);
void GXSetFogRangeAdj(GXBool enable, u16 center, GXFogAdjTable *table);
void GXSetBlendMode(GXBlendMode type, GXBlendFactor src_factor, GXBlendFactor dst_factor, GXLogicOp op);
void GXSetColorUpdate(GXBool update_enable);
void GXSetAlphaUpdate(GXBool update_enable);
void GXSetZMode(GXBool compare_enable, GXCompare func, GXBool update_enable);
void GXSetZCompLoc(GXBool before_tex);
void GXSetPixelFmt(GXPixelFmt pix_fmt, GXZFmt16 z_fmt);
void GXSetDither(GXBool dither);
void GXSetDstAlpha(GXBool enable, u8 alpha);
void GXSetFieldMask(GXBool odd_mask, GXBool even_mask);
void GXSetFieldMode(GXBool field_mode, GXBool half_aspect_ratio);
# 19 "extern/dolphin/include\\dolphin/gx.h" 2 3

# 1 "extern/dolphin/include\\dolphin/gx/GXTev.h" 1 3
# 10 "extern/dolphin/include\\dolphin/gx/GXTev.h" 3
void GXSetTevOp(GXTevStageID id, GXTevMode mode);
void GXSetTevColorIn(GXTevStageID stage, GXTevColorArg a, GXTevColorArg b,
                     GXTevColorArg c, GXTevColorArg d);
void GXSetTevAlphaIn(GXTevStageID stage, GXTevAlphaArg a, GXTevAlphaArg b,
                     GXTevAlphaArg c, GXTevAlphaArg d);
void GXSetTevColorOp(GXTevStageID stage, GXTevOp op, GXTevBias bias,
                     GXTevScale scale, GXBool clamp, GXTevRegID out_reg);
void GXSetTevAlphaOp(GXTevStageID stage, GXTevOp op, GXTevBias bias,
                     GXTevScale scale, GXBool clamp, GXTevRegID out_reg);
void GXSetTevColor(GXTevRegID id, GXColor color);
void GXSetTevColorS10(GXTevRegID id, GXColorS10 color);
void GXSetTevKColor(GXTevKColorID id, GXColor color);
void GXSetTevKColorSel(GXTevStageID stage, GXTevKColorSel sel);
void GXSetTevKAlphaSel(GXTevStageID stage, GXTevKAlphaSel sel);
void GXSetTevSwapMode(GXTevStageID stage, GXTevSwapSel ras_sel,
                      GXTevSwapSel tex_sel);
void GXSetTevSwapModeTable(GXTevSwapSel table, GXTevColorChan red,
                           GXTevColorChan green, GXTevColorChan blue,
                           GXTevColorChan alpha);
void GXSetTevClampMode(int, int);
void GXSetAlphaCompare(GXCompare comp0, u8 ref0, GXAlphaOp op, GXCompare comp1,
                       u8 ref1);
void GXSetZTexture(GXZTexOp op, GXTexFmt fmt, u32 bias);
void GXSetTevOrder(GXTevStageID stage, GXTexCoordID coord, GXTexMapID map,
                   GXChannelID color);
void GXSetNumTevStages(u8 nStages);
# 21 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXTexture.h" 1 3
# 11 "extern/dolphin/include\\dolphin/gx/GXTexture.h" 3
typedef GXTexRegion *(*GXTexRegionCallback)(GXTexObj *t_obj, GXTexMapID id);
typedef GXTlutRegion *(*GXTlutRegionCallback)(u32 idx);

u32 GXGetTexBufferSize(u16 width, u16 height, u32 format, u8 mipmap, u8 max_lod);
void GXInitTexObj(GXTexObj *obj, void *image_ptr, u16 width, u16 height, GXTexFmt format, GXTexWrapMode wrap_s, GXTexWrapMode wrap_t, u8 mipmap);
void GXInitTexObjCI(GXTexObj *obj, void *image_ptr, u16 width, u16 height, GXTexFmt format, GXTexWrapMode wrap_s, GXTexWrapMode wrap_t, u8 mipmap, u32 tlut_name);
void GXInitTexObjLOD(GXTexObj *obj, GXTexFilter min_filt, GXTexFilter mag_filt,
    f32 min_lod, f32 max_lod, f32 lod_bias, GXBool bias_clamp,
    GXBool do_edge_lod, GXAnisotropy max_aniso);
void GXInitTexObjData(GXTexObj *obj, void *image_ptr);
void GXInitTexObjWrapMode(GXTexObj *obj, GXTexWrapMode s, GXTexWrapMode t);
void GXInitTexObjTlut(GXTexObj *obj, u32 tlut_name);
void GXInitTexObjUserData(GXTexObj *obj, void *user_data);
void *GXGetTexObjUserData(const GXTexObj *obj);
void GXLoadTexObjPreLoaded(GXTexObj *obj, GXTexRegion *region, GXTexMapID id);
void GXLoadTexObj(GXTexObj *obj, GXTexMapID id);
void GXInitTlutObj(GXTlutObj *tlut_obj, void *lut, GXTlutFmt fmt, u16 n_entries);
void GXLoadTlut(GXTlutObj *tlut_obj, u32 tlut_name);
void GXInitTexCacheRegion(GXTexRegion *region, u8 is_32b_mipmap, u32 tmem_even, GXTexCacheSize size_even, u32 tmem_odd, GXTexCacheSize size_odd);
void GXInitTexPreLoadRegion(GXTexRegion *region, u32 tmem_even, u32 size_even, u32 tmem_odd, u32 size_odd);
void GXInitTlutRegion(GXTlutRegion *region, u32 tmem_addr, GXTlutSize tlut_size);
void GXInvalidateTexRegion(GXTexRegion *region);
void GXInvalidateTexAll(void);
GXTexRegionCallback GXSetTexRegionCallback(GXTexRegionCallback f);
GXTlutRegionCallback GXSetTlutRegionCallback(GXTlutRegionCallback f);
void GXPreLoadEntireTexture(GXTexObj *tex_obj, GXTexRegion *region);
void GXSetTexCoordScaleManually(GXTexCoordID coord, u8 enable, u16 ss, u16 ts);
void GXSetTexCoordCylWrap(GXTexCoordID coord, u8 s_enable, u8 t_enable);
void GXSetTexCoordBias(GXTexCoordID coord, u8 s_enable, u8 t_enable);
# 22 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXTransform.h" 1 3
# 13 "extern/dolphin/include\\dolphin/gx/GXTransform.h" 3
void GXProject(f32 x, f32 y, f32 z, f32 mtx[3][4], f32 *pm, f32 *vp, f32 *sx, f32 *sy, f32 *sz);
void GXSetProjection(f32 mtx[4][4], GXProjectionType type);
void GXSetProjectionv(f32 *ptr);
void GXLoadPosMtxImm(f32 mtx[3][4], u32 id);
void GXLoadPosMtxIndx(u16 mtx_indx, u32 id);
void GXLoadNrmMtxImm(f32 mtx[3][4], u32 id);
void GXLoadNrmMtxImm3x3(f32 mtx[3][3], u32 id);
void GXLoadNrmMtxIndx3x3(u16 mtx_indx, u32 id);
void GXSetCurrentMtx(u32 id);
void GXLoadTexMtxImm(f32 mtx[][4], u32 id, GXTexMtxType type);
void GXLoadTexMtxIndx(u16 mtx_indx, u32 id, GXTexMtxType type);
void GXSetViewportJitter(f32 left, f32 top, f32 wd, f32 ht, f32 nearz, f32 farz, u32 field);
void GXSetViewport(f32 left, f32 top, f32 wd, f32 ht, f32 nearz, f32 farz);
void GXSetScissorBoxOffset(s32 x_off, s32 y_off);
void GXSetClipMode(GXClipMode mode);
# 23 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXVerify.h" 1 3



typedef enum {
    GX_WARN_NONE,
    GX_WARN_SEVERE,
    GX_WARN_MEDIUM,
    GX_WARN_ALL
} GXWarningLevel;

typedef void (*GXVerifyCallback)(GXWarningLevel level, u32 id, char *msg);

void GXSetVerifyLevel(GXWarningLevel level);
GXVerifyCallback GXSetVerifyCallback(GXVerifyCallback cb);
# 24 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 1 "extern/dolphin/include\\dolphin/gx/GXVert.h" 1 3
# 12 "extern/dolphin/include\\dolphin/gx/GXVert.h" 3
typedef union
{
    u8 u8;
    u16 u16;
    u32 u32;
    u64 u64;
    s8 s8;
    s16 s16;
    s32 s32;
    s64 s64;
    f32 f32;
    f64 f64;
} PPCWGPipe;
# 68 "extern/dolphin/include\\dolphin/gx/GXVert.h" 3
static inline void GXCmd1u8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }
static inline void GXCmd1u16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXCmd1u32(u32 x) { (*(volatile PPCWGPipe *)0xCC008000).u32 = x; }


static inline void GXParam1u8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }
static inline void GXParam1u16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXParam1u32(u32 x) { (*(volatile PPCWGPipe *)0xCC008000).u32 = x; }
static inline void GXParam1s8(s8 x) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; }
static inline void GXParam1s16(s16 x) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; }
static inline void GXParam1s32(s32 x) { (*(volatile PPCWGPipe *)0xCC008000).s32 = x; }
static inline void GXParam1f32(f32 x) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; }
static inline void GXParam3f32(f32 x, f32 y, f32 z) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; (*(volatile PPCWGPipe *)0xCC008000).f32 = z; }
static inline void GXParam4f32(f32 x, f32 y, f32 z, f32 w) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; (*(volatile PPCWGPipe *)0xCC008000).f32 = z; (*(volatile PPCWGPipe *)0xCC008000).f32 = w; }


static inline void GXPosition3f32(f32 x, f32 y, f32 z) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; (*(volatile PPCWGPipe *)0xCC008000).f32 = z; }
static inline void GXPosition3u8(u8 x, u8 y, u8 z) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; (*(volatile PPCWGPipe *)0xCC008000).u8 = y; (*(volatile PPCWGPipe *)0xCC008000).u8 = z; }
static inline void GXPosition3s8(s8 x, s8 y, s8 z) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; (*(volatile PPCWGPipe *)0xCC008000).s8 = y; (*(volatile PPCWGPipe *)0xCC008000).s8 = z; }
static inline void GXPosition3u16(u16 x, u16 y, u16 z) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; (*(volatile PPCWGPipe *)0xCC008000).u16 = y; (*(volatile PPCWGPipe *)0xCC008000).u16 = z; }
static inline void GXPosition3s16(s16 x, s16 y, s16 z) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; (*(volatile PPCWGPipe *)0xCC008000).s16 = y; (*(volatile PPCWGPipe *)0xCC008000).s16 = z; }
static inline void GXPosition2f32(f32 x, f32 y) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; }
static inline void GXPosition2u8(u8 x, u8 y) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; (*(volatile PPCWGPipe *)0xCC008000).u8 = y; }
static inline void GXPosition2s8(s8 x, s8 y) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; (*(volatile PPCWGPipe *)0xCC008000).s8 = y; }
static inline void GXPosition2u16(u16 x, u16 y) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; (*(volatile PPCWGPipe *)0xCC008000).u16 = y; }
static inline void GXPosition2s16(s16 x, s16 y) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; (*(volatile PPCWGPipe *)0xCC008000).s16 = y; }
static inline void GXPosition1x16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXPosition1x8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }


static inline void GXNormal3f32(f32 x, f32 y, f32 z) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; (*(volatile PPCWGPipe *)0xCC008000).f32 = z; }
static inline void GXNormal3s16(s16 x, s16 y, s16 z) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; (*(volatile PPCWGPipe *)0xCC008000).s16 = y; (*(volatile PPCWGPipe *)0xCC008000).s16 = z; }
static inline void GXNormal3s8(s8 x, s8 y, s8 z) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; (*(volatile PPCWGPipe *)0xCC008000).s8 = y; (*(volatile PPCWGPipe *)0xCC008000).s8 = z; }
static inline void GXNormal1x16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXNormal1x8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }


static inline void GXColor4u8(u8 x, u8 y, u8 z, u8 w) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; (*(volatile PPCWGPipe *)0xCC008000).u8 = y; (*(volatile PPCWGPipe *)0xCC008000).u8 = z; (*(volatile PPCWGPipe *)0xCC008000).u8 = w; }
static inline void GXColor1u32(u32 x) { (*(volatile PPCWGPipe *)0xCC008000).u32 = x; }
static inline void GXColor3u8(u8 x, u8 y, u8 z) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; (*(volatile PPCWGPipe *)0xCC008000).u8 = y; (*(volatile PPCWGPipe *)0xCC008000).u8 = z; }
static inline void GXColor1u16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXColor1x16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXColor1x8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }


static inline void GXTexCoord2f32(f32 x, f32 y) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; (*(volatile PPCWGPipe *)0xCC008000).f32 = y; }
static inline void GXTexCoord2s16(s16 x, s16 y) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; (*(volatile PPCWGPipe *)0xCC008000).s16 = y; }
static inline void GXTexCoord2u16(u16 x, u16 y) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; (*(volatile PPCWGPipe *)0xCC008000).u16 = y; }
static inline void GXTexCoord2s8(s8 x, s8 y) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; (*(volatile PPCWGPipe *)0xCC008000).s8 = y; }
static inline void GXTexCoord2u8(u8 x, u8 y) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; (*(volatile PPCWGPipe *)0xCC008000).u8 = y; }
static inline void GXTexCoord1f32(f32 x) { (*(volatile PPCWGPipe *)0xCC008000).f32 = x; }
static inline void GXTexCoord1s16(s16 x) { (*(volatile PPCWGPipe *)0xCC008000).s16 = x; }
static inline void GXTexCoord1u16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXTexCoord1s8(s8 x) { (*(volatile PPCWGPipe *)0xCC008000).s8 = x; }
static inline void GXTexCoord1u8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }
static inline void GXTexCoord1x16(u16 x) { (*(volatile PPCWGPipe *)0xCC008000).u16 = x; }
static inline void GXTexCoord1x8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }


static inline void GXMatrixIndex1u8(u8 x) { (*(volatile PPCWGPipe *)0xCC008000).u8 = x; }
# 25 "extern/dolphin/include\\dolphin/gx.h" 2 3
# 34 "extern/dolphin/include\\dolphin/gx.h" 3
void (*GXSetDrawSyncCallback(void (*cb)(unsigned short)))(unsigned short);
void GXSetDrawSync(unsigned short token);
# 9 "src/sysdolphin/baselib\\fog.h" 2



struct HSD_FogAdj {
               HSD_Obj parent;
               s16 center;
               u16 width;
               Mtx44 mtx;
               HSD_AObj* aobj;
};

struct HSD_Fog {
               HSD_Obj parent;
               u32 type;
               HSD_FogAdj* fog_adj;
               f32 start;
               f32 end;
               GXColor color;
               HSD_AObj* aobj;
};

struct HSD_FogAdjDesc {
               u16 center;
               u16 width;
               Mtx44 mtx;
};

struct HSD_FogInfo {
    HSD_ObjInfo parent;
};

struct HSD_FogAdjInfo {
    HSD_ObjInfo parent;
};

struct HSD_FogDesc {
               u32 type;
               HSD_FogAdjDesc* fogadjdesc;
               f32 start;
               f32 end;
               GXColor color;
};

void HSD_FogSet(HSD_Fog*);
HSD_FogAdj* HSD_FogAdjLoadDesc(HSD_FogAdjDesc*);
void HSD_FogInit(HSD_Fog*, HSD_FogDesc*);
void HSD_FogAdjInit(HSD_FogAdj*, HSD_FogAdjDesc*);
void HSD_FogReqAnimByFlags(HSD_Fog*, u32 flags, f32 frame);
void FogUpdateFunc(void* obj, enum_t type, HSD_ObjData* fval);
HSD_Fog* HSD_FogLoadDesc(HSD_FogDesc* desc);

HSD_Fog* HSD_FogAlloc(void);
HSD_FogAdj* HSD_FogAdjAlloc(void);
void HSD_Fog_8037DE7C(HSD_Fog* fog, HSD_AObjDesc* desc);
void HSD_FogReqAnim(HSD_Fog* fog, f32 frame);
void HSD_FogInterpretAnim(HSD_Fog* fog);
# 7 "src/sysdolphin/baselib/psdisp.c" 2

# 1 "src/sysdolphin/baselib\\lobj.h" 1
# 16 "src/sysdolphin/baselib\\lobj.h"
struct HSD_LightPoint {
    f32 cutoff;
    u32 point_func;
    f32 ref_br;
    f32 ref_dist;
    u32 dist_func;
};

struct HSD_LightPointDesc {
    f32 ref_br;
    f32 ref_dist;
    u32 dist_func;
};

struct HSD_LightSpot {
    f32 cutoff;
    u32 spot_func;
    f32 ref_br;
    f32 ref_dist;
    u32 dist_func;
};

struct HSD_LightSpotDesc {
    f32 cutoff;
    u32 spot_func;
    f32 ref_br;
    f32 ref_dist;
    u32 dist_func;
};

struct HSD_LightAttn {
    f32 a0;
    f32 a1;
    f32 a2;
    f32 k0;
    f32 k1;
    f32 k2;
};

struct HSD_LObj {
                      HSD_Obj parent;
               u16 flags;
               u16 priority;
               HSD_LObj* next;
               GXColor color;
               GXColor hw_color;
               HSD_WObj* position;
               HSD_WObj* interest;
                      union {
        HSD_LightPoint point;
        HSD_LightSpot spot;
        HSD_LightAttn attn;
    } u;
               f32 shininess;
                      Vec3 lvec;
               HSD_AObj* aobj;
               GXLightID id;
               GXLightObj lightobj;
               GXLightID spec_id;
               GXLightObj spec_lightobj;
};

struct HSD_LightDesc {
               char* class_name;
               HSD_LightDesc* next;
               u16 flags;
               u16 attnflags;
               GXColor color;
               HSD_WObjDesc* position;
               HSD_WObjDesc* interest;
    union {
        void* p;
        f32* shininess;
        HSD_LightPointDesc* point;
        HSD_LightSpotDesc* spot;
        HSD_LightAttn* attn;
    } u;
};

struct HSD_LightAnim {
    HSD_LightAnim* next;
    HSD_AObjDesc* aobjdesc;
    HSD_WObjAnim* position_anim;
    HSD_WObjAnim* interest_anim;
};

struct HSD_LObjInfo {
    HSD_ObjInfo parent;
    int (*load)(HSD_LObj* lobj, HSD_LightDesc* ldesc);
};





static inline u8 HSD_LObjGetPriority(HSD_LObj* lobj)
{
    ((lobj) ? ((void) 0) : __assert("src/sysdolphin/baselib\\lobj.h", 113, "lobj"));
    return lobj->priority;
}

extern HSD_LObjInfo hsdLobj;

u32 HSD_LObjGetFlags(HSD_LObj* lobj);
void HSD_LObjSetFlags(HSD_LObj* lobj, u32 flags);
void HSD_LObjClearFlags(HSD_LObj* lobj, u32 flags);
GXLightID HSD_LObjGetLightMaskDiffuse(void);
s32 HSD_LObjGetLightMaskAttnFunc(void);
s32 HSD_LObjGetLightMaskAlpha(void);
s32 HSD_LObjGetLightMaskSpecular(void);
void HSD_LObjSetActive(HSD_LObj* lobj);
s32 HSD_LObjGetNbActive(void);
HSD_LObj* HSD_LObjGetActiveByID(GXLightID id);
HSD_LObj* HSD_LObjGetActiveByIndex(s32 idx);
void HSD_LObjClearActive(void);

void LObjUpdateFunc(void* obj, enum_t type, HSD_ObjData* val);

void HSD_LObjAddAnim(HSD_LObj* lobj, HSD_LightAnim* lanim);
void HSD_LObjAddAnimAll(HSD_LObj* lobj, HSD_LightAnim* lanim);
void HSD_LObjAnim(HSD_LObj* lobj);
void HSD_LObjAnimAll(HSD_LObj* lobj);
void HSD_LObjReqAnim(HSD_LObj* lobj, f32 startframe);
void HSD_LObjReqAnimAll(HSD_LObj* lobj, f32 startframe);
void HSD_LObjGetLightVector(HSD_LObj* lobj, Vec3* dir);
void HSD_LObjSetup(HSD_LObj* lobj, GXColor color, f32 shininess);

bool HSD_LObjGetPosition(HSD_LObj*, Vec3*);
bool HSD_LObjGetInterest(HSD_LObj*, Vec3*);

HSD_WObj* HSD_LObjGetPositionWObj(HSD_LObj* lobj);
HSD_WObj* HSD_LObjGetInterestWObj(HSD_LObj* lobj);
void HSD_LObjSetPositionWObj(HSD_LObj* lobj, HSD_WObj* wobj);
void HSD_LObjSetInterestWObj(HSD_LObj* lobj, HSD_WObj* wobj);

u32 HSD_LightID2Index(GXLightID);
void HSD_LObjDeleteCurrent(HSD_LObj* lobj);
s32 HSD_Index2LightID(u32);
void HSD_LObjRemoveAll(HSD_LObj* lobj);
void HSD_LObjSetPosition(HSD_LObj* lobj, Vec3* position);
void HSD_LObjSetInterest(HSD_LObj* lobj, Vec3* interest);
void HSD_LObj_803668EC(HSD_LObj* lobj);
void HSD_LObjSetupInit(HSD_CObj* arg0);

void HSD_LObjSetColor(HSD_LObj* lobj, GXColor color);
void HSD_LObjGetColor(HSD_LObj* lobj, GXColor* color);
void HSD_LObjSetSpot(HSD_LObj* lobj, f32 cutoff, s32 point_func);
void HSD_LObjSetDistAttn(HSD_LObj* lobj, f32 ref_dist, f32 ref_br,
                         s32 dist_func);
void HSD_LObjSetAttnA(HSD_LObj* lobj, f32 a0, f32 a1, f32 a2);
void HSD_LObjSetAttnK(HSD_LObj* lobj, f32 k0, f32 k1, f32 k2);
void HSD_LObjSetAttn(HSD_LObj* lobj, f32 a0, f32 a1, f32 a2, f32 k0, f32 k1,
                     f32 k2);

void HSD_LObjSetupSpecularInit(Mtx pmtx);
u32 HSD_LObjGetType(HSD_LObj* lobj);
void HSD_LObjAddCurrent(HSD_LObj* lobj);
void HSD_LObjUnrefThis(HSD_LObj* lobj);
void HSD_LObjDeleteCurrentAll(HSD_LObj* lobj);
void HSD_LObjSetCurrentAll(HSD_LObj* lobj);
HSD_LObj* HSD_LObjGetCurrentByType(u16 type);

void HSD_LObjSetDefaultClass(HSD_LObjInfo* info);
HSD_LObjInfo* HSD_LObjGetDefaultClass(void);
HSD_LObj* HSD_LObjAlloc(void);
HSD_LObj* HSD_LObjLoadDesc(HSD_LightDesc* ldesc);

static inline HSD_LObj* HSD_LObjGetNext(HSD_LObj* lobj)
{
    if (lobj == 0L) {
        return 0L;
    } else {
        return lobj->next;
    }
}

static inline void HSD_LObjSetNext(HSD_LObj* lobj, HSD_LObj* next)
{
    ((lobj) ? ((void) 0) : __assert("src/sysdolphin/baselib\\lobj.h", 194, "lobj"));
    lobj->next = next;
}
# 9 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\mtx.h" 1





# 1 "src/MSL\\math.h" 1 3
# 18 "src/MSL\\math.h" 3
enum FloatType {
    FP_NAN = 1,
    FP_INFINITE = 2,
    FP_ZERO = 3,
    FP_NORMAL = 4,
    FP_SUBNORMAL = 5
};

static inline s32 __fpclassifyf(float x)
{
    const s32 exp_mask = 0x7F800000;
    const s32 mantissa_mask = 0x007FFFFF;
    switch ((*(s32*) &x) & exp_mask) {
    case exp_mask:
        return ((*(s32*) &x) & mantissa_mask) ? FP_NAN : FP_INFINITE;
    case 0:
        return ((*(s32*) &x) & mantissa_mask) ? FP_SUBNORMAL : FP_ZERO;
    default:
        return FP_NORMAL;
    }
}

extern int __HI(double);
extern int __LO(double);

static inline s32 __fpclassifyd(double x)
{
    switch (__HI(x) & 0x7ff00000) {
    case 0x7ff00000:
        return ((__HI(x) & 0x000fffff) || (__LO(x) & 0xffffffff))
                   ? FP_NAN
                   : FP_INFINITE;
    case 0:
        return ((__HI(x) & 0x000fffff) || (__LO(x) & 0xffffffff))
                   ? FP_SUBNORMAL
                   : FP_ZERO;
    default:
        return FP_NORMAL;
    }
}
# 71 "src/MSL\\math.h" 3
double fabs(double);
double frexp(double x, int* exponent);
float acosf(float);
float asinf(float);
float atan2f(float y, float x);
float atanf(float);
float cos__Ff(float x);
float cosf(float);
float expf(float);
float fabsf(float);
float fabsf__Ff(float);
float logf(float);
float sin__Ff(float x);
float sinf(float);
float sqrt(double);
float sqrtf(float);
void __sinit_trigf_c(void);

static inline float fmodf(float a, float b)
{
    long long quotient;

    if (fabsf(b) > fabsf(a)) {
        return a;
    }
    quotient = a / b;
    return a - b * quotient;
}
# 7 "src/sysdolphin/baselib\\mtx.h" 2


# 1 "src\\sysdolphin/baselib/objalloc.h" 1







typedef struct _objheap {
    u32 top;
    u32 curr;
    u32 size;
    u32 remain;
} objheap;

typedef struct _HSD_ObjAllocLink {
    struct _HSD_ObjAllocLink* next;
} HSD_ObjAllocLink;

typedef struct _HSD_ObjAllocData {
    u32 num_limit_flag : 1;
    u32 heap_limit_flag : 1;
    HSD_ObjAllocLink* freehead;
    u32 used;
    u32 free;
    u32 peak;
    u32 num_limit;
    u32 heap_limit_size;
    u32 heap_limit_num;
    u32 size;
    u32 align;
    struct _HSD_ObjAllocData* next;
} HSD_ObjAllocData;
_Static_assert((sizeof(struct _HSD_ObjAllocData) == 0x2C), "(" "sizeof(struct _HSD_ObjAllocData) == 0x2C" ") failed");

static inline u32 HSD_ObjAllocGetUsing(HSD_ObjAllocData* data)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 37, "data"));
    return data->used;
}

static inline u32 HSD_ObjAllocGetFreed(HSD_ObjAllocData* data)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 43, "data"));
    return data->free;
}

static inline u32 HSD_ObjAllocGetPeak(HSD_ObjAllocData* data)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 49, "data"));
    return data->peak;
}

static inline void HSD_ObjAllocSetNumLimit(HSD_ObjAllocData* data,
                                           u32 num_limit)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 56, "data"));
    data->num_limit = num_limit;
}

static inline void HSD_ObjAllocEnableNumLimit(HSD_ObjAllocData* data)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 62, "data"));
    data->num_limit_flag = 1;
}

static inline void HSD_ObjAllocDisableNumLimit(HSD_ObjAllocData* data)
{
    ((data) ? ((void) 0) : __assert("src\\sysdolphin/baselib/objalloc.h", 68, "data"));
    data->num_limit_flag = 0;
}

void HSD_ObjSetHeap(u32 size, void* ptr);
s32 HSD_ObjAllocAddFree(HSD_ObjAllocData* data, u32 num);
void* HSD_ObjAlloc(HSD_ObjAllocData* data);
void HSD_ObjFree(HSD_ObjAllocData* data, void* obj);
void _HSD_ObjAllocForgetMemory(void* low, void* high);
void HSD_ObjAllocInit(HSD_ObjAllocData* data, size_t size, u32 align);
# 10 "src/sysdolphin/baselib\\mtx.h" 2




typedef Vec3 VecMtx[4];
typedef Vec3* VecMtxPtr;

void HSD_MtxInverse(Mtx src, Mtx dest);
void HSD_MtxInverseConcat(Mtx inv, Mtx src, Mtx dest);
void HSD_MtxInverseTranspose(Mtx src, Mtx dest);
void HSD_MtxGetRotation(Mtx m, Vec3* vec);
void HSD_MtxGetTranslate(Mtx mat, Vec3* vec);
void HSD_MtxGetScale(Mtx arg0, Vec3* arg1);
void HSD_MkRotationMtx(Mtx arg0, Vec3* arg1);
void HSD_MtxQuat(Mtx arg0, Quaternion* arg1);
void HSD_MtxSRT(Mtx m, Vec3* vec1, Vec3* vec2, Vec3* vec3, Vec3* vec4);
void HSD_MtxSRTQuat(Mtx arg0, Vec3* arg1, Quaternion* arg2, Vec3* arg3,
                    Vec3* arg4);
void HSD_MtxScaledAdd(Mtx arg0, Mtx arg1, Mtx arg2, f32 arg3);
void* HSD_VecAlloc(void);
void HSD_VecFree(void* arg0);
void* HSD_MtxAlloc(void);
void HSD_MtxFree(void* arg0);
HSD_ObjAllocData* HSD_VecGetAllocData(void);
void HSD_VecInitAllocData(void);
HSD_ObjAllocData* HSD_MtxGetAllocData(void);
void HSD_MtxInitAllocData(void);

static inline f32 fabsf_bitwise(f32 v)
{
    *(u32*) &v &= ~0x80000000;
    return v;
}

static inline void HSD_MtxColVec(MtxPtr mtx, int col, Vec3* vec)
{
    vec->x = mtx[0][col];
    vec->y = mtx[1][col];
    vec->z = mtx[2][col];
}

static inline void HSD_MtxSetColVec(MtxPtr mtx, int col, Vec3* vec)
{
    mtx[0][col] = vec->x;
    mtx[1][col] = vec->y;
    mtx[2][col] = vec->z;
}

static inline f32 HSD_MtxColMag(MtxPtr mtx, int col)
{
    return sqrtf((mtx[0][col] * mtx[0][col]) + (mtx[1][col] * mtx[1][col]) +
                 (mtx[2][col] * mtx[2][col]));
}
# 10 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\particle.h" 1







# 1 "src\\sysdolphin/baselib/jobj.h" 1
# 11 "src\\sysdolphin/baselib/jobj.h"
# 1 "src\\sysdolphin/baselib/list.h" 1





typedef struct _HSD_SList {
    struct _HSD_SList* next;
    void* data;
} HSD_SList;

typedef struct _HSD_DList {
    struct _HSD_DList* next;
    struct _HSD_DList* prev;
    void* data;
} HSD_DList;

void HSD_ListInitAllocData(void);
HSD_ObjAllocData* HSD_SListGetAllocData(void);
HSD_ObjAllocData* HSD_DListGetAllocData(void);
HSD_SList* HSD_SListAlloc(void);
HSD_SList* HSD_SListAllocAndAppend(HSD_SList* next, void* data);
HSD_SList* HSD_SListAllocAndPrepend(HSD_SList* prev, void* data);
HSD_SList* HSD_SListAppendList(HSD_SList* list, HSD_SList* next);
HSD_SList* HSD_SListPrependList(HSD_SList* list, HSD_SList* prev);
HSD_SList* HSD_SListRemove(HSD_SList* list);
# 12 "src\\sysdolphin/baselib/jobj.h" 2

# 1 "src\\sysdolphin/baselib/pobj.h" 1
# 10 "src\\sysdolphin/baselib/pobj.h"
# 1 "src\\sysdolphin/baselib/aobj.h" 1








# 1 "src\\sysdolphin/baselib/fobj.h" 1
# 32 "src\\sysdolphin/baselib/fobj.h"
struct HSD_FObj {
    struct HSD_FObj* next;
    u8* ad;
    u8* ad_head;
    u32 length;
    u8 flags;
    u8 op;
    u8 op_intrp;
    u8 obj_type;
    u8 frac_value;
    u8 frac_slope;
    u16 nb_pack;
    s16 startframe;
    u16 fterm;
    f32 time;
    f32 p0;
    f32 p1;
    f32 d0;
    f32 d1;
};

typedef struct _HSD_FObjDesc {
    struct _HSD_FObjDesc* next;
    u32 length;
    f32 startframe;
    u8 type;
    u8 frac_value;
    u8 frac_slope;
    u8 dummy0;
    u8* ad;
} HSD_FObjDesc;

union HSD_ObjData {
    f32 fv;
    s32 iv;
    Vec3 p;
};

HSD_ObjAllocData* HSD_FObjGetAllocData(void);
void HSD_FObjInitAllocData(void);
void HSD_FObjRemove(HSD_FObj* fobj);
void HSD_FObjRemoveAll(HSD_FObj* fobj);
u32 HSD_FObjSetState(HSD_FObj* fobj, u32 state);
u32 HSD_FObjGetState(HSD_FObj* fobj);
void HSD_FObjReqAnimAll(HSD_FObj* fobj, f32 startframe);
void HSD_FObjStopAnim(HSD_FObj* fobj, void* obj, HSD_ObjUpdateFunc obj_update,
                      f32 rate);
void HSD_FObjStopAnimAll(HSD_FObj* fobj, void* obj,
                         HSD_ObjUpdateFunc obj_update, f32 rate);
void FObjUpdateAnim(HSD_FObj* fobj, void* obj, HSD_ObjUpdateFunc update_func);
void HSD_FObjInterpretAnim(HSD_FObj* fobj, void* obj,
                           HSD_ObjUpdateFunc obj_update, f32 rate);
void HSD_FObjInterpretAnimAll(void* fobj, void* obj,
                              HSD_ObjUpdateFunc obj_update, f32 rate);
HSD_FObj* HSD_FObjLoadDesc(HSD_FObjDesc* desc);
HSD_FObj* HSD_FObjAlloc(void);
void HSD_FObjFree(HSD_FObj* fobj);
# 10 "src\\sysdolphin/baselib/aobj.h" 2
# 19 "src\\sysdolphin/baselib/aobj.h"
typedef enum _AObj_Arg_Type {
    AOBJ_ARG_A,
    AOBJ_ARG_AF,
    AOBJ_ARG_AV,
    AOBJ_ARG_AU,
    AOBJ_ARG_AO,
    AOBJ_ARG_AOF,
    AOBJ_ARG_AOV,
    AOBJ_ARG_AOU,
    AOBJ_ARG_AOT,
    AOBJ_ARG_AOTF,
    AOBJ_ARG_AOTV,
    AOBJ_ARG_AOTU,
} AObj_Arg_Type;

typedef union _callbackArg {
    f32 f;
    u32 d;
    void* v;
} callbackArg;

struct HSD_AObj {
    u32 flags;
    f32 curr_frame;
    f32 rewind_frame;
    f32 end_frame;
    f32 framerate;
    HSD_FObj* fobj;
    struct HSD_Obj* hsd_obj;
};

struct HSD_AObjDesc {
    u32 flags;
    f32 end_frame;
    HSD_FObjDesc* fobjdesc;
    u32 obj_id;
};

struct HSD_AnimJoint {
    HSD_AnimJoint* child;
    HSD_AnimJoint* next;
    HSD_AObjDesc* aobjdesc;
    HSD_RObjAnimJoint* robj_anim;
    u32 flags;
};

void HSD_AObjInitAllocData(void);
HSD_ObjAllocData* HSD_AObjGetAllocData(void);
u32 HSD_AObjGetFlags(HSD_AObj* aobj);
void HSD_AObjSetFlags(HSD_AObj* aobj, u32 flags);
void HSD_AObjClearFlags(HSD_AObj* aobj, u32 flags);
void HSD_AObjSetFObj(HSD_AObj* aobj, HSD_FObj* fobj);
void HSD_AObjInitEndCallBack(void);
void HSD_AObjInvokeCallBacks(void);
void HSD_AObjReqAnim(HSD_AObj* aobj, f32 frame);
void HSD_AObjStopAnim(HSD_AObj* aobj, void* obj, HSD_ObjUpdateFunc func);

void HSD_AObjInterpretAnim(HSD_AObj* aobj, void* obj,
                           HSD_ObjUpdateFunc update_func);

HSD_AObj* HSD_AObjLoadDesc(HSD_AObjDesc* aobjdesc);
void HSD_AObjRemove(HSD_AObj* aobj);
HSD_AObj* HSD_AObjAlloc(void);
void HSD_AObjFree(HSD_AObj* aobj);
void HSD_ForeachAnim(void* obj, HSD_Type type, HSD_TypeMask mask, void* func,
                     AObj_Arg_Type arg_type, ...);
void HSD_AObjSetRate(HSD_AObj* aobj, f32 rate);
void HSD_AObjSetRewindFrame(HSD_AObj* aobj, f32 frame);
void HSD_AObjSetEndFrame(HSD_AObj* aobj, f32 frame);
void HSD_AObjSetCurrentFrame(HSD_AObj* aobj, f32 frame);
void _HSD_AObjForgetMemory(void* low, void* high);

static inline f32 HSD_AObjGetCurrFrame(HSD_AObj* aobj)
{
    ((aobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/aobj.h", 93, "aobj"));
    return aobj->curr_frame;
}

static inline f32 HSD_AObjGetEndFrame(HSD_AObj* aobj)
{
    ((aobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/aobj.h", 99, "aobj"));
    return aobj->end_frame;
}
# 11 "src\\sysdolphin/baselib/pobj.h" 2






struct _unk_struct_pobj {
    u32 data[8];
    HSD_AObj* aobj;
};

struct HSD_PObj {
    HSD_Class parent;
    HSD_PObj* next;
    HSD_VtxDescList* verts;
    u16 flags;
    u16 n_display;

    u8* display;
    union HSD_PObjUnion {
        HSD_JObj* jobj;
        HSD_ShapeSet* shape_set;
        HSD_SList* envelope_list;
        struct _unk_struct_pobj* unk;
    } u;
};

struct HSD_PObjDesc {
    char* class_name;
    HSD_PObjDesc* next;
    HSD_VtxDescList* verts;
    u16 flags;
    u16 n_display;
    u8* display;
    union {
        HSD_Joint* joint;
        HSD_ShapeSetDesc* shape_set;
        HSD_EnvelopeDesc** envelope_p;
    } u;
};

struct HSD_VtxDescList {
    GXAttr attr;
    GXAttrType attr_type;
    GXCompCnt comp_cnt;
    GXCompType comp_type;
    u8 frac;
    u16 stride;
    void* vertex;
};

struct HSD_Envelope {
    HSD_Envelope* next;
    HSD_JObj* jobj;
    f32 weight;
};

struct HSD_EnvelopeDesc {
    HSD_Joint* joint;
    f32 weight;
};

struct HSD_ShapeSet {
    u16 flags;
    u16 nb_shape;
    int nb_vertex_index;
    HSD_VtxDescList* vertex_desc;
    u8** vertex_idx_list;
    s32 nb_normal_index;
    HSD_VtxDescList* normal_desc;
    u8** normal_idx_list;
    union {
        f32* bp;
        f32 bl;
    } blend;
    HSD_AObj* aobj;
};

struct HSD_ShapeSetDesc {
    u16 flags;
    u16 nb_shape;
    s32 nb_vertex_index;
    HSD_VtxDescList* vertex_desc;
    u8** vertex_idx_list;
    s32 nb_normal_index;
    HSD_VtxDescList* normal_desc;
    u8** normal_idx_list;
};

struct HSD_ShapeAnim {
    HSD_ShapeAnim* next;
    HSD_AObjDesc* aobjdesc;
};

struct HSD_ShapeAnimJoint {
    HSD_ShapeAnimJoint* child;
    HSD_ShapeAnimJoint* next;
    HSD_ShapeAnimDObj* shapeanimdobj;
};

struct HSD_PObjInfo {
    HSD_ClassInfo parent;
    void (*disp)(HSD_PObj* pobj, Mtx vmtx, Mtx pmtx, u32 rendermode);
    void (*setup_mtx)(HSD_PObj* pobj, Mtx vmtx, Mtx pmtx, u32 rendermode);
    s32 (*load)(HSD_PObj* pobj, HSD_PObjDesc* desc);
};

extern HSD_PObjInfo hsdPObj;





HSD_PObjInfo* HSD_PObjGetDefaultClass(void);
void HSD_PObjSetDefaultClass(HSD_PObjInfo* info);
HSD_PObj* HSD_PObjAlloc(void);
void HSD_PObjFree(HSD_PObj*);

u32 HSD_PObjGetFlags(HSD_PObj* pobj);
void HSD_PObjRemoveAnimAllByFlags(HSD_PObj* pobj, u32 flags);
void HSD_PObjReqAnimByFlags(HSD_PObj* pobj, f32 startframe, u32 flags);
void HSD_PObjReqAnimAllByFlags(HSD_PObj* pobj, f32 startframe, u32 flags);
void HSD_ClearVtxDesc(void);
HSD_PObj* HSD_PObjLoadDesc(HSD_PObjDesc*);

void HSD_PObjClearMtxMark(void* obj, u32 mark);
void HSD_PObjSetMtxMark(int idx, void* obj, u32 mark);
void HSD_PObjGetMtxMark(int idx, void** obj, u32* mark);
void HSD_PObjAddAnim(HSD_PObj*, HSD_ShapeAnim*);
void HSD_PObjAddAnimAll(HSD_PObj*, HSD_ShapeAnim*);
void HSD_PObjAnim(HSD_PObj* pobj);
void HSD_PObjAnimAll(HSD_PObj*);
void HSD_PObjResolveRefs(HSD_PObj*, HSD_PObjDesc*);
void HSD_PObjResolveRefsAll(HSD_PObj*, HSD_PObjDesc*);
void HSD_PObjRemove(HSD_PObj*);
void HSD_PObjRemoveAll(HSD_PObj*);

void HSD_PObjRemoveAnimByFlags(HSD_PObj* pobj, u32 flags);

void HSD_PObjDisp(HSD_PObj* pobj, Mtx vmtx, Mtx pmtx, u32 rendermode);
# 14 "src\\sysdolphin/baselib/jobj.h" 2
# 1 "src\\sysdolphin/baselib/spline.h" 1





typedef struct HSD_Spline {
              u8 type;
              s16 numcv;
              f32 tension;
              Vec3* cv;
              f32 totalLength;
              f32* segLength;
              f32 (*segPoly)[5];
} HSD_Spline;

f32 splGetHelmite(f32, f32, f32, f32, f32, f32);
void splGetSplinePoint(Vec3*, HSD_Spline*, f32);
f32 splArcLengthGetParameter(HSD_Spline*, f32);
void splArcLengthPoint(Vec3*, HSD_Spline*, f32);
# 15 "src\\sysdolphin/baselib/jobj.h" 2
# 104 "src\\sysdolphin/baselib/jobj.h"
typedef struct HSD_JObj {
              HSD_Obj object;
              HSD_JObj* next;
              HSD_JObj* parent;
              HSD_JObj* child;
              u32 flags;
              union {
        HSD_SList* ptcl;
        struct HSD_DObj* dobj;
        HSD_Spline* spline;
    } u;
              Quaternion rotate;
              Vec3 scale;
              Vec3 translate;
              Mtx mtx;
              Vec3* scl;
              MtxPtr envelopemtx;
              HSD_AObj* aobj;
              HSD_RObj* robj;
              u32 id;
} HSD_JObj;
_Static_assert((sizeof(struct HSD_JObj) == 0x88), "(" "sizeof(struct HSD_JObj) == 0x88" ") failed");

typedef struct HSD_Joint {
             char* class_name;
             u32 flags;
             HSD_Joint* child;
             HSD_Joint* next;
              union {
        HSD_DObjDesc* dobjdesc;
        HSD_Spline* spline;
        HSD_SList* ptcl;
    } u;
              Vec3 rotation;
              Vec3 scale;
              Vec3 position;
              MtxPtr mtx;
              HSD_RObjDesc* robjdesc;
} HSD_Joint;

typedef struct HSD_JObjInfo {
    HSD_ObjInfo parent;
    s32 (*load)(HSD_JObj* jobj, HSD_Joint* joint, HSD_JObj* jobj_2);
    void (*make_mtx)(HSD_JObj* jobj);
    void (*make_pmtx)(HSD_JObj* jobj, Mtx mtx, Mtx rmtx);
    void (*disp)(HSD_JObj* jobj, Mtx vmtx, Mtx pmtx, HSD_TrspMask trsp_mask,
                 u32 rendermode);
    void (*release_child)(HSD_JObj* jobj);
} HSD_JObjInfo;

extern HSD_JObjInfo hsdJObj;
typedef void (*HSD_JObjWalkTreeCallback)(HSD_JObj*, f32**, s32);
typedef void (*DPCtlCallback)(int, int lo, int hi, HSD_JObj* jobj);

void HSD_JObjSetDefaultClass(HSD_ClassInfo* info);

void HSD_JObjCheckDepend(HSD_JObj* jobj);
u32 HSD_JObjGetFlags(HSD_JObj* jobj);
void HSD_JObjReqAnimAll(HSD_JObj*, f32);
void HSD_JObjResetRST(HSD_JObj* jobj, HSD_Joint* joint);
void HSD_JObjSetupMatrixSub(HSD_JObj*);
void HSD_JObjSetMtxDirtySub(HSD_JObj*);
void(HSD_JObjSetMtxDirty)(HSD_JObj* jobj);
void HSD_JObjUnref(HSD_JObj* jobj);
HSD_JObj* HSD_JObjRemove(HSD_JObj* jobj);
void HSD_JObjRemoveAll(HSD_JObj*);
struct HSD_DObj* HSD_JObjGetDObj(HSD_JObj* jobj);
HSD_JObj* HSD_JObjLoadJoint(HSD_Joint*);
void HSD_JObjAddAnimAll(HSD_JObj*, HSD_AnimJoint*, HSD_MatAnimJoint*,
                        HSD_ShapeAnimJoint*);
void HSD_JObjAnimAll(HSD_JObj*);
void HSD_JObjSetFlags(HSD_JObj*, u32 flags);
void HSD_JObjSetFlagsAll(HSD_JObj*, u32 flags);
void HSD_JObjClearFlags(HSD_JObj*, u32 flags);
void HSD_JObjClearFlagsAll(HSD_JObj*, u32 flags);
HSD_JObj* HSD_JObjAlloc(void);
void HSD_JObjSetCurrent(HSD_JObj* jobj);
HSD_JObj* HSD_JObjGetCurrent(void);
void HSD_JObjResolveRefsAll(HSD_JObj*, HSD_Joint*);
void HSD_JObjDispAll(HSD_JObj* jobj, Mtx vmtx, u32 flags, u32 rendermode);
void HSD_JObjRemoveAnim(HSD_JObj* jobj);
void HSD_JObjAddNext(HSD_JObj* jobj, HSD_JObj* next);
void HSD_JObjRemoveAnimAll(HSD_JObj* jobj);
void HSD_JObjWalkTree(HSD_JObj* jobj, HSD_JObjWalkTreeCallback cb,
                      f32** cb_args);
void HSD_JObjPrependRObj(HSD_JObj* jobj, HSD_RObj* robj);
void HSD_JObjDeleteRObj(HSD_JObj* jobj, HSD_RObj* robj);

static inline HSD_JObj* HSD_JObjGetChild(HSD_JObj* jobj)
{
    if (jobj == 0L) {
        return 0L;
    } else {
        return jobj->child;
    }
}

static inline HSD_JObj* HSD_JObjGetNext(HSD_JObj* jobj)
{
    if (jobj == 0L) {
        return 0L;
    } else {
        return jobj->next;
    }
}

static inline HSD_JObj* HSD_JObjGetParent(HSD_JObj* jobj)
{
    if (jobj == 0L) {
        return 0L;
    } else {
        return jobj->parent;
    }
}

static inline HSD_RObj* HSD_JObjGetRObj(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 221, "jobj"));
    return jobj->robj;
}

static inline bool HSD_JObjMtxIsDirty(HSD_JObj* jobj)
{
    bool result;
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 228, "jobj"));
    result = 0;
    if (!(jobj->flags & (1 << 23)) && (jobj->flags & (1 << 6))) {
        result = 1;
    }
    return result;
}

static inline void HSD_JObjSetMtxDirtyOutOfLineLeaf(HSD_JObj* jobj)
{
    (HSD_JObjSetMtxDirty)(jobj);
}

static inline void HSD_JObjSetMtxDirtyOutOfLine(HSD_JObj* jobj)
{
    HSD_JObjSetMtxDirtyOutOfLineLeaf(jobj);
}



static

    inline void HSD_JObjSetupMatrix(HSD_JObj* jobj)
{
    if (!jobj || !HSD_JObjMtxIsDirty(jobj)) {
        return;
    }
    HSD_JObjSetupMatrixSub(jobj);
}
# 267 "src\\sysdolphin/baselib/jobj.h"
static inline void HSD_JObjSetMtxDirtyInline(HSD_JObj* jobj)
{
    if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) {
        HSD_JObjSetMtxDirtySub(jobj);
    }
}

static inline void HSD_JObjSetRotation(HSD_JObj* jobj, Quaternion* rotate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 276, "jobj"));
    ((rotate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 277, "rotate"));
    jobj->rotate = *rotate;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetRotationWithMtxDirty(HSD_JObj* jobj,
                                                   Quaternion* rotate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 287, "jobj"));
    ((rotate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 288, "rotate"));
    jobj->rotate = *rotate;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetRotationX(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 297, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 298, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.x = x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetRotationXWithMtxDirty(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 307, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 308, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.x = x;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetRotationY(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 317, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 318, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.y = y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetRotationYWithMtxDirty(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 327, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 328, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.y = y;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetRotationZ(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 337, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 338, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.z = z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetRotationZWithMtxDirty(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 347, "jobj"));
    ((!(jobj->flags & (1 << 17))) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 348, "!(jobj->flags & JOBJ_USE_QUATERNION)"));
    jobj->rotate.z = z;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjGetRotation(HSD_JObj* jobj, Quaternion* rotate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 357, "jobj"));
    ((rotate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 358, "rotate"));
    *rotate = jobj->rotate;
}

static inline f32 HSD_JObjGetRotationX(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 364, "jobj"));
    return jobj->rotate.x;
}

static inline f32 HSD_JObjGetRotationY(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 370, "jobj"));
    return jobj->rotate.y;
}

static inline f32 HSD_JObjGetRotationZ(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 376, "jobj"));
    return jobj->rotate.z;
}

static inline void HSD_JObjSetScale(HSD_JObj* jobj, Vec3* scale)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 382, "jobj"));
    ((scale) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 383, "scale"));
    jobj->scale = *scale;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetScaleWithMtxDirty(HSD_JObj* jobj, Vec3* scale)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 392, "jobj"));
    ((scale) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 393, "scale"));
    jobj->scale = *scale;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetScaleX(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 402, "jobj"));
    jobj->scale.x = x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetScaleXWithMtxDirty(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 411, "jobj"));
    jobj->scale.x = x;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetScaleY(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 420, "jobj"));
    jobj->scale.y = y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetScaleYWithMtxDirty(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 429, "jobj"));
    jobj->scale.y = y;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetScaleZ(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 438, "jobj"));
    jobj->scale.z = z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetScaleZWithMtxDirty(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 447, "jobj"));
    jobj->scale.z = z;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjGetScale(HSD_JObj* jobj, Vec3* scale)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 456, "jobj"));
    ((scale) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 457, "scale"));
    *scale = jobj->scale;
}

static inline f32 HSD_JObjGetScaleX(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 463, "jobj"));
    return jobj->scale.x;
}

static inline f32 HSD_JObjGetScaleY(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 469, "jobj"));
    return jobj->scale.y;
}

static inline f32 HSD_JObjGetScaleZ(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 475, "jobj"));
    return jobj->scale.z;
}

static inline void HSD_JObjSetTranslate(HSD_JObj* jobj, Vec3* translate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 481, "jobj"));
    ((translate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 482, "translate"));
    jobj->translate = *translate;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetTranslateWithMtxDirty(HSD_JObj* jobj,
                                                    Vec3* translate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 492, "jobj"));
    ((translate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 493, "translate"));
    jobj->translate = *translate;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetTranslateWithMtxDirtyOutOfLine(HSD_JObj* jobj,
                                                             Vec3* translate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 503, "jobj"));
    ((translate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 504, "translate"));
    jobj->translate = *translate;
    if (!(jobj->flags & (1 << 25))) {
        HSD_JObjSetMtxDirtyOutOfLine(jobj);
    }
}

static inline void HSD_JObjSetTranslateX(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 513, "jobj"));
    jobj->translate.x = x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetTranslateXWithMtxDirty(HSD_JObj* jobj, f32 x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 522, "jobj"));
    jobj->translate.x = x;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetTranslateY(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 531, "jobj"));
    jobj->translate.y = y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetTranslateYWithMtxDirty(HSD_JObj* jobj, f32 y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 540, "jobj"));
    jobj->translate.y = y;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjSetTranslateZ(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 549, "jobj"));
    jobj->translate.z = z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjSetTranslateZWithMtxDirty(HSD_JObj* jobj, f32 z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 558, "jobj"));
    jobj->translate.z = z;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjGetTranslation(HSD_JObj* jobj, Vec3* translate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 567, "jobj"));
    ((translate) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 568, "translate"));
    *translate = jobj->translate;
}



static inline void HSD_JObjGetTranslation2(HSD_JObj* jobj, Vec3* translate)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 576, "jobj"));
    *translate = jobj->translate;
}

static inline f32 HSD_JObjGetTranslationX(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 582, "jobj"));
    return jobj->translate.x;
}

static inline f32 HSD_JObjGetTranslationY(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 588, "jobj"));
    return jobj->translate.y;
}

static inline float HSD_JObjGetTranslationZ(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 594, "jobj"));
    return jobj->translate.z;
}

static inline void HSD_JObjAddRotationX(HSD_JObj* jobj, float x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 600, "jobj"));
    jobj->rotate.x += x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddRotationXWithMtxDirty(HSD_JObj* jobj, float x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 609, "jobj"));
    jobj->rotate.x += x;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjAddRotationY(HSD_JObj* jobj, float y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 618, "jobj"));
    jobj->rotate.y += y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddRotationZ(HSD_JObj* jobj, float z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 627, "jobj"));
    jobj->rotate.z += z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddScaleX(HSD_JObj* jobj, float x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 636, "jobj"));
    jobj->scale.x += x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddScaleY(HSD_JObj* jobj, float y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 645, "jobj"));
    jobj->scale.y += y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddScaleZ(HSD_JObj* jobj, float z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 654, "jobj"));
    jobj->scale.z += z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddTranslationX(HSD_JObj* jobj, float x)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 663, "jobj"));
    jobj->translate.x += x;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddTranslationY(HSD_JObj* jobj, float y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 672, "jobj"));
    jobj->translate.y += y;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline void HSD_JObjAddTranslationYWithMtxDirty(HSD_JObj* jobj, float y)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 681, "jobj"));
    jobj->translate.y += y;
    if (!(jobj->flags & (1 << 25))) {
        (HSD_JObjSetMtxDirty)(jobj);
    }
}

static inline void HSD_JObjAddTranslationZ(HSD_JObj* jobj, float z)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 690, "jobj"));
    jobj->translate.z += z;
    if (!(jobj->flags & (1 << 25))) {
        { if (jobj != 0L && !HSD_JObjMtxIsDirty(jobj)) { HSD_JObjSetMtxDirtySub(jobj); } };
    }
}

static inline MtxPtr HSD_JObjGetMtxPtr(HSD_JObj* jobj)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 699, "jobj"));
    HSD_JObjSetupMatrix(jobj);
    return jobj->mtx;
}

static inline void HSD_JObjCopyMtx(HSD_JObj* jobj, Mtx mtx)
{
    ((jobj) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 706, "jobj"));
    ((mtx) ? ((void) 0) : __assert("src\\sysdolphin/baselib/jobj.h", 707, "mtx"));
    PSMTXCopy(mtx, jobj->mtx);
}

static inline void HSD_JObjRef(HSD_JObj* jobj)
{
    ref_INC(jobj);
}

static inline void HSD_JObjRefThis(HSD_JObj* jobj)
{
    if (jobj != 0L) {
        iref_INC(jobj);
    }
}

void HSD_JObjResolveRefs(HSD_JObj* jobj, HSD_Joint* joint);
void HSD_JObjUnrefThis(HSD_JObj* jobj);
void HSD_JObjRefThis(HSD_JObj* jobj);
void HSD_JObjMakeMatrix(HSD_JObj* jobj);
void RecalcParentTrspBits(HSD_JObj* jobj);
void HSD_JObjAddChild(HSD_JObj* jobj, HSD_JObj* child);
HSD_JObj* HSD_JObjReparent(HSD_JObj* jobj, HSD_JObj* parent);
void HSD_JObjAddDObj(HSD_JObj* jobj, HSD_DObj* dobj);
HSD_JObj* jobj_get_effector_checked(HSD_JObj* eff);
void resolveIKJoint1(HSD_JObj* jobj);
void resolveIKJoint2(HSD_JObj* jobj);
void HSD_JObjRemoveAnimByFlags(HSD_JObj* jobj, u32 flags);
void HSD_JObjSetDPtclCallback(DPCtlCallback cb);
int JObjInit(HSD_Class* o);
void JObjReleaseChild(HSD_JObj* jobj);
void JObjRelease(HSD_Class* o);
void HSD_JObjRemoveAnimAllByFlags(HSD_JObj* jobj, u32 flags);
void JObjAmnesia(HSD_ClassInfo* info);
void HSD_JObjReqAnimByFlags(HSD_JObj* jobj, u32 flags, f32 frame);
void HSD_JObjReqAnimAllByFlags(HSD_JObj* jobj, u32 flags, f32 frame);
void HSD_JObjReqAnim(HSD_JObj* jobj, f32 frame);
void JObjSortAnim(HSD_AObj* aobj);
void JObjResetRST(HSD_JObj* jobj, HSD_Joint* joint);
void JObjUpdateFunc(void* obj, enum_t type, HSD_ObjData* val);
void HSD_JObjAnim(HSD_JObj* jobj);
void JObjAnimAll(HSD_JObj* jobj);
s32 JObjLoad(HSD_JObj* jobj, HSD_Joint* joint, HSD_JObj* parent);

void HSD_JObjAddAnim(HSD_JObj*, HSD_AnimJoint* an_joint,
                     HSD_MatAnimJoint* mat_joint,
                     HSD_ShapeAnimJoint* sh_joint);
void HSD_JObjWalkTree0(HSD_JObj* jobj, HSD_JObjWalkTreeCallback cb,
                       f32** cb_args);
# 9 "src/sysdolphin/baselib\\particle.h" 2
# 1 "src\\sysdolphin/baselib/psstructs.h" 1
# 11 "src\\sysdolphin/baselib/psstructs.h"
# 1 "src\\sysdolphin/baselib/archive.h" 1
# 10 "src\\sysdolphin/baselib/archive.h"
struct HSD_ArchiveHeader {
    u32 file_size;
    u32 data_size;
    u32 nb_reloc;
    u32 nb_public;
    u32 nb_extern;
    u8 version[4];
    u32 pad[2];
};
_Static_assert((sizeof(struct HSD_ArchiveHeader) == 0x20), "(" "sizeof(struct HSD_ArchiveHeader) == 0x20" ") failed");

struct HSD_ArchiveRelocationInfo {
    u32 offset;
};

struct HSD_ArchivePublicInfo {
    u32 offset;
    u32 symbol;
};

struct HSD_ArchiveExternInfo {
    u32 offset;
    u32 symbol;
};

struct HSD_Archive {
    HSD_ArchiveHeader header;
    u8* data;
    HSD_ArchiveRelocationInfo* reloc_info;
    HSD_ArchivePublicInfo* public_info;
    HSD_ArchiveExternInfo* extern_info;
    char* symbols;
    HSD_Archive* next;
    char* name;
    u32 flags;
    void* top_ptr;
};
_Static_assert((sizeof(struct HSD_Archive) == 0x44), "(" "sizeof(struct HSD_Archive) == 0x44" ") failed");

s32 HSD_ArchiveParse(HSD_Archive*, u8*, size_t file_size);
void* HSD_ArchiveGetPublicAddress(HSD_Archive*, const char*);
char* HSD_ArchiveGetExtern(HSD_Archive*, int);
void HSD_ArchiveLocateExtern(HSD_Archive*, const char*, void*);
# 12 "src\\sysdolphin/baselib/psstructs.h" 2


struct HSD_Fog;

enum HSD_ParticleKind {
    Tornado = 1 << 2,
    TexEdge = 1 << 3,
    ComTLUT = 1 << 4,
    MirrorS = 1 << 5,
    MirrorT = 1 << 6,
    PrimEnv = 1 << 7,
    TexInterpNear = 1 << 9,
    DispTexture = 1 << 10,
    TexFlipS = 1 << 18,
    TexFlipT = 1 << 19,
    Trail = 1 << 20,
    DirVec = 1 << 21,
    DispFog = 1 << 24,
    NoZComp = 1 << 28,
    DispPoint = 1 << 30,
    DispLighting = 1 << 31
};


typedef struct _HSD_PSTexGroup {
    u32 num;

    u32 fmt;
    u32 tlutfmt;

    u32 width;
    u32 height;

    u16 palnum;
    u16 palflag;

    u8* texTable[1];
} HSD_PSTexGroup;


typedef struct _HSD_PSFormGroup {
    u32 num;
    u8* formTable[1];
} HSD_PSFormGroup;


typedef struct _HSD_PSCmdList {
    u16 type;
    u16 texGroup;

    u16 genLife;
    u16 life;

    u32 kind;

    float grav;
    float fric;

    float vx;
    float vy;
    float vz;

    float radius;
    float angle;
    float random;
    float size;

    float param1;
    float param2;
    float param3;

    u8 cmdList[1];
} HSD_PSCmdList;

enum PS_AppStatus {
    PS_APPSTATUS_ONCE = 1,
    PS_APPSTATUS_STILL = 2,
};

struct HSD_psAppSRT {
    struct HSD_psAppSRT* next;

    struct HSD_Generator* gp;

    Vec3 translate;
    Quaternion rot;
    Vec3 scale;

    u8 status;

    u8 frameNum;
    u16 usedCount;

    Mtx mmtx;
    float ssx;
    float ssy;

    f32 x6C;
    f32 x70;
    f32 x74;
    f32 x78;
    f32 x7C;
    f32 x80;
    f32 x84;
    f32 x88;
    f32 x8C;
    f32 x90;
    f32 x94;
    f32 x98;

    void (*freefunc)(struct HSD_psAppSRT* appSrt);

    u16 idnum;
    u8 xA2;
};


struct HSD_Particle {
    HSD_Particle* next;
    u32 kind;
    u8 bank;
    u8 texGroup;
    u8 poseNum;
    u8 palNum;
    u16 sizeCount;
    u16 primColCount;
    u16 envColCount;
    GXColor primCol;
    GXColor envCol;
    u16 cmdWait;
    u8 loopCount;
    u8 linkNo;
    u16 idnum;
    u8* cmdList;
    u16 cmdPtr;
    u16 cmdMarkPtr;
    u16 cmdLoopPtr;
    u16 life;
    Vec3 vel;
    float grav;
    float fric;
    Vec3 pos;
    float size;
    float rotate;
    u16 aCmpCount;
    u8 aCmpMode;
    u8 aCmpParam1;
    u8 aCmpParam2;
    u8 pJObjOfs;
    u16 matColCount;
    u16 ambColCount;
    u16 rotateCount;
    float sizeTarget;
    float rotateTarget;
    u16 primColRemain;
    u16 envColRemain;
    GXColor primColTarget;
    GXColor envColTarget;
    u16 matColRemain;
    u16 ambColRemain;
    u16 aCmpRemain;
    u8 aCmpParam1Target;
    u8 aCmpParam2Target;
    u8 matRGB;
    u8 matA;
    u8 ambRGB;
    u8 ambA;
    u8 matRGBTarget;
    u8 matATarget;
    u8 ambRGBTarget;
    u8 ambATarget;
    float trail;
    struct HSD_Generator* gen;
    struct HSD_psAppSRT* appsrt;
    float* userdata;
    int (*callback)(HSD_Particle* part);
};


typedef struct _PSUserFunc {
    int (*hookCreate)(HSD_Particle* part);
    int (*hookDelete)(HSD_Particle* part);
    int (*setUserData)(HSD_Particle* part, u8 unknown1,
                       float unknown2);
} HSD_PSUserFunc;

typedef struct _auxDisc {
    f32 minAngle;
    f32 maxAngle;
} auxDisc;

typedef struct _auxLine {
    f32 x2;
    f32 y2;
    f32 z2;
} auxLine;

typedef struct _auxTornado {
    f32 vel;
} auxTornado;

typedef struct _auxRect {
    f32 x;
    f32 y;
    f32 z;
    f32 xx;
    f32 xy;
    f32 xz;
    f32 yx;
    f32 yy;
    f32 yz;
    f32 zx;
    f32 zy;
    f32 zz;
    u16 flag;
} auxRect;

typedef struct _auxCone {
    f32 minAngle;
    f32 maxAngle;
    f32 height;
} auxCone;

typedef struct _auxSphere {
    f32 speed;
    f32 latMid;
    f32 latRange;
    f32 lonMid;
    f32 lonRange;
} auxSphere;

struct HSD_Generator {
    HSD_Generator* next;
    u32 kind;
    f32 random;
    f32 count;
    HSD_JObj* jobj;
    u16 genLife;
    u16 type;
    u8 bank;
    u8 linkNo;
    u8 texGroup;
    u8 dummy;
    u16 idnum;
    u16 life;
    u8* cmdList;
    Vec3 pos;
    Vec3 vel;
    f32 grav;
    f32 fric;
    f32 size;
    f32 radius;
    f32 angle;
    u32 numChild;
    HSD_psAppSRT* appsrt;
    HSD_PSUserFunc* userfunc;
    int (*callback)(HSD_Generator* part);
    union {
        auxDisc disc;
        auxLine line;
        auxTornado tornado;
        auxRect rect;
        auxCone cone;
        auxSphere sphere;
    } aux;
};



extern int texc[4][4];
extern int td;



void psSetFog(struct HSD_Fog* fog);

void psRemoveFog(void);


static inline void setBlendMode(int blendmode);

static inline void setupChanCtrl(HSD_Particle* pp);
static inline void setupChanReg(HSD_Particle* pp);
static inline void getClrTrail(HSD_Particle* pp, GXColor* col);
static inline void setupTevReg(HSD_Particle* pp);
static inline void psSetCurrentMtx(GXPosNrmMtx idx);
static inline HSD_Particle* psDispSubPoint(HSD_Particle* pp);
static inline HSD_Particle* psDispSubPointTrail(HSD_Particle* pp);
static inline void psDispSubMakePolygon(HSD_Particle* pp, u8* texform, f32 x,
                                        f32 y, f32 z, f32 x0, f32 y0, f32 z0,
                                        f32 x1, f32 y1, f32 z1, GXColor* color,
                                        f32* prev_x, f32* prev_y, f32* prev_z);

static inline void psDispSub(HSD_Particle* pp, u8* texform);



static inline void psDispSubAppSRT(HSD_Particle* pp, u8* texform);
static inline void psDispSubAPPSRTPoint(HSD_Particle* pp);


void psInitDataBank(int bank, int* cmdBank, int* texBank, u32* ref,
                    int* formBank);

void psInitParticle(int num);

void psRemoveParticle(void);

HSD_Particle* psGenerateParticleID0(HSD_Particle* p, int linkNo, int bank,
                                    int id, int flgInterpret);

HSD_Particle* psGenerateParticle(int linkNo, int bank, u32 kind, u16 texGroup,
                                 u8* list, int life, float x, float y, float z,
                                 float vx, float vy, float vz, float size,
                                 float grav, float fric, int palflag,
                                 HSD_Generator* gp);

HSD_Particle* psGenerateParticleIDPV(int linkNo, int bank, int id, float px,
                                     float py, float pz, float vx, float vy,
                                     float vz);

HSD_Particle* psGenerateParticleID(int linkNo, int bank, int id);
HSD_Particle* psGenerateParticleIDN(int linkNo, int bank, int id);

void psKillParticle(HSD_Particle* pp);
void psKillAllParticle(void);

void psSetPointJObj(int no, HSD_JObj* jobj);
void psSetPointJObjNodup(HSD_JObj* jobj, int no);

void psClearPointJObj(void);

void psDeletePntJObjwithParticle(HSD_Particle* pp);

void psKillFamily(u16 idnum, int linkNo);
void psKillGeneratorChild(HSD_Generator* gp);

void psAddOffsetAll(float xofs, float yofs, float zofs);

void psPauseFamily(u16 idnum, int linkNo);
void psRestartFamily(u16 idnum, int linkNo);

void psSetCallback(int (**callback)(HSD_Particle* part));

void psSetUserFunc(HSD_Generator* gp, HSD_PSUserFunc* userfunc);

static inline void psRemoveBillboardCamera(void);
# 10 "src/sysdolphin/baselib\\particle.h" 2

             void hsd_803983A4(HSD_Generator*);
             void psInitDataBankLoad(int bank, const int* cmdBank,
                                     const int* texBank, const u32* ref,
                                     const int* formBank);
             void psInitDataBankLocate(HSD_Archive* cmdBank,
                                       HSD_Archive* texBank, int* formBank);
             void psInitDataBankRelocate(int* cmdBank, int* texBank,
                                         int* formBank, int* newCmdBank,
                                         int* newTexBank, int* newFormBank);
             void hsd_80398A08(u32);
             HSD_Particle*
psGenerateParticle0(HSD_Particle** head, int linkNo, int bank, u32 kind,
                    u16 texGroup, u8* list, int life, int palflag, f32 x,
                    f32 y, f32 z, f32 vx, f32 vy, f32 vz, f32 size, f32 grav,
                    f32 fric, HSD_Generator* gp, int flgInterpret);
             void hsd_80398F0C(s32, s32, s32, u16, s32, s32, s32, s32, f32,
                               f32, f32, f32, f32, f32, f32, f32, f32);
             void hsd_80398F8C(HSD_Particle*, f32);
             s32 hsd_803991D8(HSD_Generator*, HSD_JObj*, f32, f32);
             void* hsd_8039930C(HSD_Particle*, HSD_Particle*);
             void hsd_8039CEAC(u32);
             void hsd_8039CF4C(s32, HSD_JObj*);
             void hsd_8039D048(void* particle);
             extern HSD_PSTexGroup** psTexGroupArray[65];
             extern HSD_PSFormGroup** psNumCmdList[65];
             extern int psCmdListArray[65];
             extern HSD_PSCmdList** ptclref_804D0E5C[65];
             extern u16 hsd_804D78D8;
             extern u16 hsd_804D78DA;
             extern u16 hsd_804D78DE;
             extern u16 hsd_804D78E0;
             extern u32 hsd_804D78E8;
             extern u32 hsd_804D78EC;
             extern HSD_CObj* psCamera;
             extern u32 hsd_804D78F4;
# 11 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\psdisptev.h" 1





void psSetupTevCommon(void);
void psSetupTevInvalidState(void);
void psSetupTev(u32*);
# 12 "src/sysdolphin/baselib/psdisp.c" 2

# 1 "src/sysdolphin/baselib\\state.h" 1
# 20 "src/sysdolphin/baselib\\state.h"
typedef struct HSD_Chan {
    struct HSD_Chan* next;
    GXChannelID chan;
    u32 flags;
    GXColor amb_color;
    GXColor mat_color;
    GXBool enable;
    GXColorSrc amb_src;
    GXColorSrc mat_src;
    GXLightID light_mask;
    GXDiffuseFn diff_fn;
    GXAttnFn attn_fn;
    HSD_AObj* aobj;
} HSD_Chan;

void HSD_SetupChannelMode(u32 arg0);
void HSD_SetupPEMode(u32 flags, HSD_PEDesc* pe);
void HSD_SetupRenderModeWithCustomPE(u32 rendermode, HSD_PEDesc* pe);
void HSD_SetupRenderMode(u32);
void HSD_SetMaterialColor(GXColor ambient, GXColor diffuse, GXColor specular,
                          f32 alpha);
void HSD_SetMaterialShininess(f32 shininess);
void HSD_StateSetLineWidth(u8 width, int tex_offsets);
void HSD_StateSetCullMode(int mode);
void HSD_StateSetBlendMode(int type, int src_factor, int dst_factor, int op);
void HSD_StateSetZMode(int, int, int);
void HSD_StateSetPointSize(u8, int);
void HSD_StateSetAlphaCompare(int, u8, int, int, u8);
void HSD_StateSetColorUpdate(int);
void HSD_StateSetAlphaUpdate(int);
void HSD_StateSetDstAlpha(int, u8);
void HSD_StateSetZCompLoc(int);
void HSD_StateSetDither(int);
void _HSD_StateInvalidatePrimitive(void);
void _HSD_StateInvalidateVtxAttr(void);
void _HSD_StateInvalidateRenderMode(void);
void HSD_StateInvalidate(int mask);
# 14 "src/sysdolphin/baselib/psdisp.c" 2
# 1 "src/sysdolphin/baselib\\util.h" 1
# 11 "src/sysdolphin/baselib\\util.h"
void HSD_MulColor(GXColor* arg0, GXColor* arg1, GXColor* dest);
u32 HSD_GetNbBits(u32 arg0);
s32 HSD_Index2PosNrmMtx(u32 arg0);


extern Mtx HSD_identityMtx;






static inline int vec_normalize_check(Vec3* src, Vec3* dst)
{
    if (!src || !dst) {
        return -1;
    }
    if (fabsf_bitwise(src->x) <= 1.17549435e-38f && fabsf_bitwise(src->y) <= 1.17549435e-38f &&
        fabsf_bitwise(src->z) <= 1.17549435e-38f)
    {
        return -1;
    }
    PSVECNormalize(src, dst);
    return 0;
}

static inline f32 atan2f_check(s8 y, s8 x)
{
    if (fabs(x) == 0.0) {
        return y >= 0 ? 1.5707963267948966 : -1.5707963267948966;
    } else {
        return atan2f(y, x);
    }
}
# 15 "src/sysdolphin/baselib/psdisp.c" 2






typedef struct {
    HSD_Particle* head;
    HSD_Particle* tail;
} psdisp_ParticleSortBucket;

typedef struct {
    GXTlutFmt fmt;
    u32 tlut_name;
    u16 n_entries;
} psdisp_Tlut;

typedef struct {
    Mtx mtx;
} psdisp_Mtx;

             static void calcTornadoLastPos(HSD_Particle*, f32*, f32*, f32*);
             static void getColorPrimEnv(HSD_Particle*, GXColor*, GXColor*);
             static void getColorMatAmb(HSD_Particle*, GXColor*, GXColor*);

             static const psdisp_Mtx HSD_PSDisp_803B9628 = {
    { { 1.0F, 0.0F, 0.0F, 0.0F },
      { 0.0F, 1.0F, 0.0F, 0.0F },
      { 0.0F, 0.0F, 1.0F, 0.0F } },
};



             static char HSD_PSDisp_8040C300[] = "object.h";
             static char HSD_PSDisp_8040C30C[] =
    "HSD_OBJ(o)->ref_count != HSD_OBJ_NOREF";
             static u8 HSD_PSDisp_8040C334[0xC] = { 0 };
             static u8 HSD_PSDisp_8040C340[0x20] = {
    0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1,
    0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0,
};
             static u8 HSD_PSDisp_8040C360[0x10] = { 0 };
             static u8 psFrameNum = 0x7B;
             extern HSD_Particle* hsd_804D0908[16];
             static Mtx vmtx;
             static Mtx rvmtx;
             static f32 prj[7];
             static Mtx pvmtx;
             static HSD_Particle* particle_list[17];
             static HSD_Fog* HSD_PSDisp_804D7908;
             static s32 prevPointSize;
             static s32 prevLineWidth;
             static f32 HSD_PSDisp_804D7914;
             static f32 HSD_PSDisp_804D7918;
             static f32 HSD_PSDisp_804D791C;
             static f32 HSD_PSDisp_804D7920;
             static f32 HSD_PSDisp_804D7924;
             static f32 HSD_PSDisp_804D7928;
             static s32 HSD_PSDisp_804D792C;
             static s32 prevChanCtrl;
             static GXColor prevChanMat;
             static GXColor prevChanAmb;
             static GXColor prevColorPrim;
             static GXColor prevColorEnv;
             static GXColor prevColorMat;
             static s32 HSD_PSDisp_804D7948[2];

_Static_assert((sizeof(HSD_PSDisp_8040C340) == 0x20), "(" "sizeof(HSD_PSDisp_8040C340) == 0x20" ") failed");
_Static_assert((sizeof(HSD_PSDisp_8040C360) == 0x10), "(" "sizeof(HSD_PSDisp_8040C360) == 0x10" ") failed");

void setVtxDesc(s32 fmt)
{
    GXClearVtxDesc();
    switch (fmt) {
    case 0:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        GXSetVtxDesc(GX_VA_TEX0, GX_INDEX8);
        return;
    case 1:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        return;
    case 2:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        GXSetVtxDesc(GX_VA_CLR0, GX_DIRECT);
        GXSetVtxDesc(GX_VA_TEX0, GX_INDEX8);
        return;
    case 3:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        GXSetVtxDesc(GX_VA_CLR0, GX_DIRECT);
        return;
    case 4:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        GXSetVtxDesc(GX_VA_TEX0, GX_DIRECT);
        return;
    case 5:
        GXSetVtxDesc(GX_VA_POS, GX_DIRECT);
        GXSetVtxDesc(GX_VA_CLR0, GX_DIRECT);
        GXSetVtxDesc(GX_VA_TEX0, GX_DIRECT);
        return;
    }
}

static void calcTornadoLastPos(HSD_Particle* pp, f32* x, f32* y, f32* z)
{
    f32 radius;
    f32 px, py, pz;
    f32 sina, sinb, cosa, cosb;
    f32 vx0, vz0;
    HSD_Generator* gp;

    gp = pp->gen;

    if (gp == 0L) {
        *x = gp->pos.x;
        *y = gp->pos.y;
        *z = gp->pos.z;
        return;
    }

    sina = sinf(pp->grav);
    sinb = sinf(pp->fric);
    cosa = cosf(pp->grav);
    cosb = cosf(pp->fric);

    vz0 = pp->vel.z - gp->aux.tornado.vel;
    vx0 = pp->vel.x - gp->grav;

    radius = ((gp->radius) < 0 ? -(gp->radius) : (gp->radius));
    radius += vz0 * tanf(((gp->angle) < 0 ? -(gp->angle) : (gp->angle)));
    radius *= pp->vel.y;
    px = radius * cosf(vx0);
    py = radius * sinf(vx0);
    pz = vz0;

    *x = px * cosb + pz * sinb + gp->pos.x;
    *y = -px * sina * sinb + py * cosa + pz * sina * cosb + gp->pos.y;
    *z = -px * cosa * sinb - py * sina + pz * cosa * cosb + gp->pos.z;
}

static void getColorPrimEnv(HSD_Particle* pp, GXColor* primCol,
                            GXColor* envCol)
{
    if (pp->primColCount) {
        int scale = 65536 * pp->primColRemain / pp->primColCount;
        primCol->r = ((pp->primColTarget.r << 16) +
                      (pp->primCol.r - pp->primColTarget.r) * scale) >>
                     16;
        primCol->g = ((pp->primColTarget.g << 16) +
                      (pp->primCol.g - pp->primColTarget.g) * scale) >>
                     16;
        primCol->b = ((pp->primColTarget.b << 16) +
                      (pp->primCol.b - pp->primColTarget.b) * scale) >>
                     16;
        primCol->a = ((pp->primColTarget.a << 16) +
                      (pp->primCol.a - pp->primColTarget.a) * scale) >>
                     16;
    } else {
        *primCol = pp->primCol;
    }
    if (pp->envColCount) {
        int scale = 65536 * pp->envColRemain / pp->envColCount;
        envCol->r = ((pp->envColTarget.r << 16) +
                     (pp->envCol.r - pp->envColTarget.r) * scale) >>
                    16;
        envCol->g = ((pp->envColTarget.g << 16) +
                     (pp->envCol.g - pp->envColTarget.g) * scale) >>
                    16;
        envCol->b = ((pp->envColTarget.b << 16) +
                     (pp->envCol.b - pp->envColTarget.b) * scale) >>
                    16;
        envCol->a = ((pp->envColTarget.a << 16) +
                     (pp->envCol.a - pp->envColTarget.a) * scale) >>
                    16;
    } else {
        *envCol = pp->envCol;
    }
}





static void getColorMatAmb(HSD_Particle* pp, GXColor* matCol, GXColor* ambCol)
{
    if (pp->matColCount) {
        int scale = 65536 * pp->matColRemain / pp->matColCount;
        matCol->r = matCol->g = matCol->b =
            ((pp->matRGBTarget << 16) +
             (pp->matRGB - pp->matRGBTarget) * scale) >>
            16;
        matCol->a =
            ((pp->matATarget << 16) + (pp->matA - pp->matATarget) * scale) >>
            16;
    } else {
        matCol->r = matCol->g = matCol->b = pp->matRGB;
        matCol->a = pp->matA;
    }
    if (pp->ambColCount) {
        int scale = 65536 * pp->ambColRemain / pp->ambColCount;
        ambCol->r = ambCol->g = ambCol->b =
            ((pp->ambRGBTarget << 16) +
             (pp->ambRGB - pp->ambRGBTarget) * scale) >>
            16;
        ambCol->a =
            ((pp->ambATarget << 16) + (pp->ambA - pp->ambATarget) * scale) >>
            16;
    } else {
        ambCol->r = ambCol->g = ambCol->b = pp->ambRGB;
        ambCol->a = pp->ambA;
    }
}




static inline void getClrTrail(HSD_Particle* pp, GXColor* color)
{
    GXColor env_color;

    switch (pp->kind & (DispLighting | PrimEnv)) {
    case 0:
    case DispLighting:
        getColorPrimEnv(pp, color, &env_color);
        break;
    case PrimEnv:
    case DispLighting | PrimEnv:
        color->r = color->g = color->b = color->a = 0xFF;
        break;
    }
}

static inline void psSetColor(GXColor* color, u8 value)
{
    color->r = value;
    color->g = value;
    color->b = value;
    color->a = value;
}

static inline void psSetupVtxFormat(GXVtxFmt format, bool has_color,
                                    bool has_texture, GXCompType texture_type)
{
    GXSetVtxAttrFmt(format, GX_VA_POS, GX_TEX_ST, GX_RGBA6, 0U);
    if (has_color) {
        GXSetVtxAttrFmt(format, GX_VA_CLR0, GX_TEX_ST, GX_RGBA8, 0U);
    }
    if (has_texture) {
        GXSetVtxAttrFmt(format, GX_VA_TEX0, GX_TEX_ST, texture_type, 0U);
    }
}

static inline void setupChanCtrl(HSD_Particle* pp)
{
    u32 chan_state = pp->kind & (DispLighting | Trail);

    if (chan_state != (u32) prevChanCtrl) {
        prevChanCtrl = chan_state;
        GXSetNumChans(1);
        switch (prevChanCtrl) {
        case Trail:
            GXSetChanCtrl(GX_COLOR0A0, ((GXBool)0), GX_SRC_VTX, GX_SRC_VTX, 0,
                          GX_DF_NONE, GX_AF_NONE);
            break;
        case DispLighting:
            GXSetChanCtrl(GX_COLOR0, ((GXBool)1), GX_SRC_REG, GX_SRC_REG,
                          HSD_LObjGetLightMaskDiffuse(), GX_DF_NONE,
                          HSD_LObjGetLightMaskAttnFunc() ? GX_AF_SPOT
                                                         : GX_AF_NONE);
            GXSetChanCtrl(GX_ALPHA0, ((GXBool)0), GX_SRC_REG, GX_SRC_REG, 0,
                          GX_DF_NONE, GX_AF_NONE);
            break;
        case DispLighting | Trail:
            GXSetChanCtrl(GX_COLOR0, ((GXBool)1), GX_SRC_REG, GX_SRC_REG,
                          HSD_LObjGetLightMaskDiffuse(), GX_DF_NONE,
                          HSD_LObjGetLightMaskAttnFunc() ? GX_AF_SPOT
                                                         : GX_AF_NONE);
            GXSetChanCtrl(GX_ALPHA0, ((GXBool)0), GX_SRC_VTX, GX_SRC_VTX, 0,
                          GX_DF_NONE, GX_AF_NONE);
            break;
        default:
            GXSetChanCtrl(GX_COLOR0A0, ((GXBool)0), GX_SRC_REG, GX_SRC_REG, 0,
                          GX_DF_NONE, GX_AF_NONE);
            break;
        }
    }
}

static inline void setupChanReg(HSD_Particle* pp)
{
    GXColor prim_color;
    GXColor amb_color;
    GXColor mat_color;
    HSD_LObj* lobj;

    if (pp->kind & DispLighting) {
        getColorMatAmb(pp, &mat_color, &amb_color);
        if (pp->kind & PrimEnv) {
            prim_color.r = prim_color.g = prim_color.b = 0xFF;
        } else {
            getColorPrimEnv(pp, &prim_color, &mat_color);
            amb_color.r = (u8) ((amb_color.r * prim_color.r) >> 8);
            amb_color.g = (u8) ((amb_color.g * prim_color.g) >> 8);
            amb_color.b = (u8) ((amb_color.b * prim_color.b) >> 8);
        }
        if (prim_color.r != prevChanMat.r || prim_color.g != prevChanMat.g ||
            prim_color.b != prevChanMat.b)
        {
            prevChanMat = prim_color;
            GXSetChanMatColor(GX_COLOR0, prevChanMat);
        }
        lobj = HSD_LObjGetActiveByID(GX_MAX_LIGHT);
        if (lobj != 0L) {
            HSD_MulColor(&amb_color, &lobj->color, &amb_color);
        } else {
            amb_color.r = amb_color.g = amb_color.b = 0;
        }
        if (amb_color.r != prevChanAmb.r || amb_color.g != prevChanAmb.g ||
            amb_color.b != prevChanAmb.b)
        {
            prevChanAmb = amb_color;
            GXSetChanAmbColor(GX_COLOR0, prevChanAmb);
        }
    }
}

static inline void setupTevReg(HSD_Particle* pp)
{
    GXColor prim_color;
    GXColor env_color;
    GXColor mat_color;
    GXColor amb_color;

    getColorPrimEnv(pp, &prim_color, &env_color);
    if ((pp->kind & PrimEnv) ||
        (!(pp->kind & DispLighting) && !(pp->kind & Trail)))
    {
        if (prevColorPrim.r != prim_color.r ||
            prevColorPrim.g != prim_color.g ||
            prevColorPrim.b != prim_color.b || prevColorPrim.a != prim_color.a)
        {
            prevColorPrim = prim_color;
            GXSetTevColor(GX_TEVREG0, prevColorPrim);
        }
        if (pp->kind & PrimEnv) {
            if (prevColorEnv.r != env_color.r ||
                prevColorEnv.g != env_color.g ||
                prevColorEnv.b != env_color.b || prevColorEnv.a != env_color.a)
            {
                prevColorEnv = env_color;
                GXSetTevColor(GX_TEVREG1, prevColorEnv);
            }
        } else if (prevColorEnv.r != 0 || prevColorEnv.g != 0 ||
                   prevColorEnv.b != 0 || prevColorEnv.a != 0)
        {
            prevColorEnv.r = prevColorEnv.g = prevColorEnv.b = prevColorEnv.a =
                0;
            GXSetTevColor(GX_TEVREG1, prevColorEnv);
        }
    }
    if (pp->kind & DispLighting) {
        getColorMatAmb(pp, &mat_color, &amb_color);
        if (pp->kind & PrimEnv) {
            if (prevColorMat.r != mat_color.r ||
                prevColorMat.g != mat_color.g ||
                prevColorMat.b != mat_color.b || prevColorMat.a != mat_color.a)
            {
                prevColorMat = mat_color;
                GXSetTevColor(GX_TEVREG2, prevColorMat);
            }
        } else {
            mat_color.a = (u8) ((mat_color.a * prim_color.a) >> 8);
            if (prevColorMat.r != mat_color.r ||
                prevColorMat.g != mat_color.g ||
                prevColorMat.b != mat_color.b || prevColorMat.a != mat_color.a)
            {
                prevColorMat = mat_color;
                GXSetTevColor(GX_TEVREG2, prevColorMat);
            }
        }
    }
}

HSD_Particle* particleSort(s32 arg0, u8 arg1, HSD_Particle** arg2,
                           HSD_Particle** arg3)
{
    psdisp_ParticleSortBucket buckets[16];
    HSD_Particle** new_var;
    HSD_Particle* var_r28;
    HSD_Particle* var_r3;
    HSD_Particle* var_r4;
    HSD_Particle* var_r5;
    HSD_Particle* var_r7;
    HSD_Particle** temp_r29;
    HSD_Particle** var_r6_2;
    HSD_Particle** var_r7_2;
    s32 i;
    u32 temp_r3;
    u32 temp_r3_2;
    s32 temp_r4;
    s32 var_r0;
    s32 var_r0_2;
    s32 var_r6;
    u8* temp_r9;

    _Static_assert((sizeof(buckets[0]) == 8), "(" "sizeof(buckets[0]) == 8" ") failed");

    temp_r9 = &HSD_PSDisp_8040C360[arg0];
    temp_r29 = (new_var = &hsd_804D0908[arg0]);
    var_r28 = *temp_r29;
    if (*temp_r9 == arg1) {
        *arg2 = var_r28;
        *arg3 = particle_list[arg0];
        return var_r28;
    }

    *temp_r9 = arg1;
    if (var_r28 == 0L) {
        particle_list[arg0] = 0L;
        *arg2 = 0L;
        *arg3 = 0L;
        return 0L;
    }

    memset(buckets, 0, sizeof(buckets));
    temp_r3 = var_r28->kind;
    if (temp_r3 & 8) {
        var_r0 = 0;
    } else {
        var_r0 = 1;
    }
    temp_r4 = ((temp_r3 >> 0x19) & 7) + (var_r0 * 8);
    buckets[temp_r4].head = var_r28;
    var_r6 = temp_r4;
    var_r7 = var_r28->next;

    while (var_r7 != 0L) {
        if ((var_r28->kind ^ var_r7->kind) & 0x0E000008) {
            buckets[var_r6].tail = var_r28;
            temp_r3_2 = var_r7->kind;
            if (temp_r3_2 & 8) {
                var_r0_2 = 0;
            } else {
                var_r0_2 = 1;
            }
            var_r6 = ((temp_r3_2 >> 0x19) & 7) + (var_r0_2 * 8);
            if (buckets[var_r6].head == 0L) {
                buckets[var_r6].head = var_r7;
            } else {
                buckets[var_r6].tail->next = var_r7;
            }
        }
        var_r28 = var_r7;
        var_r7 = var_r7->next;
    }
    buckets[var_r6].tail = var_r28;

    var_r6_2 = 0L;
    var_r4 = 0L;
    var_r7_2 = 0L;
    var_r5 = 0L;

    for (i = 0; i < 8; i++) {
        if (buckets[i].head != 0L) {
            if (var_r4 == 0L) {
                var_r4 = buckets[i].head;
            } else {
                *var_r6_2 = buckets[i].head;
            }
            var_r6_2 = &buckets[i].tail->next;
        }
    }

    for (i = 8; i < 16; i++) {
        if (buckets[i].head != 0L) {
            if (var_r5 == 0L) {
                var_r5 = buckets[i].head;
            } else {
                *var_r7_2 = buckets[i].head;
            }
            var_r7_2 = &buckets[i].tail->next;
        }
    }

    var_r3 = 0L;
    if (var_r6_2 != 0L) {
        var_r3 = var_r4;
        *var_r6_2 = var_r5;
    }
    if (var_r7_2 != 0L) {
        if (var_r3 == 0L) {
            var_r3 = var_r5;
        }
        *var_r7_2 = 0L;
    }

    *temp_r29 = var_r3;
    particle_list[arg0] = var_r5;
    *arg2 = var_r3;
    *arg3 = var_r5;
    return var_r3;
}

static inline HSD_Particle* psDispSubPoint(HSD_Particle* pp)
{
    Vec3 buf[16];
    Vec3* p;
    HSD_Particle* last;
    HSD_Particle* q;
    s32 count;
    s32 i;
    u8 w;

    psSetCurrentMtx(GX_PNMTX0);
    w = (pp->size > 42.5) ? 255.0f : 6.0f * pp->size;
    if (prevPointSize != (s32) w) {
        prevPointSize = w;
        GXSetPointSize(w, GX_TO_ONE);
    }
    last = pp;
    p = buf;
    p->x = pp->pos.x;
    p->y = pp->pos.y;
    p->z = pp->pos.z;
    p++;
    count = 1;
    q = pp->next;
    while (q != 0L) {
        if (q->size == pp->size && q->appsrt == 0L &&
            !((q->kind ^ pp->kind) & 0xC0100400) && q->primColCount == 0 &&
            q->primCol.r == pp->primCol.r && q->primCol.g == pp->primCol.g &&
            q->primCol.b == pp->primCol.b && q->primCol.a == pp->primCol.a &&
            !(q->kind & DispPoint) &&
            (!(pp->kind & DispLighting) ||
             (q->matColCount == 0 && q->ambColCount == 0 &&
              q->matRGB == pp->matRGB && q->matA == pp->matA &&
              q->ambRGB == pp->ambRGB && q->ambA == pp->ambA)))
        {
            count++;
            p->x = q->pos.x;
            p->y = q->pos.y;
            p->z = q->pos.z;
            p++;
            if (count == 16) {
                p = buf;
                if (pp->kind & DispTexture) {
                    setVtxDesc(0);
                    GXBegin(GX_POINTS, GX_VTXFMT0, 16U);
                } else {
                    setVtxDesc(1);
                    GXBegin(GX_POINTS, GX_VTXFMT1, 16U);
                }
                for (i = count; i != 0; i--) {
                    GXPosition3f32(p->x, p->y, p->z);
                    p++;
                    if (pp->kind & DispTexture) {
                        GXTexCoord1x8(1);
                    }
                }
                p = buf;
                count = 0;
            }
            q = (last = q)->next;
        } else {
            break;
        }
    }
    if (count != 0) {
        p = buf;
        if (pp->kind & DispTexture) {
            setVtxDesc(0);
            GXBegin(GX_POINTS, GX_VTXFMT0, (u16) count);
        } else {
            setVtxDesc(1);
            GXBegin(GX_POINTS, GX_VTXFMT1, (u16) count);
        }
        for (i = count; i != 0; i--) {
            GXPosition3f32(p->x, p->y, p->z);
            p++;
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(1);
            }
        }


        if (q != 0L) {
        }
    }
    return last;
}

static inline HSD_Particle* psDispSubPointTrail(HSD_Particle* pp)
{
    Vec3 vbuf[32];
    GXColor cbuf[32];
    Vec3* p;
    GXColor* c;
    HSD_Particle* last;
    HSD_Particle* q;
    s32 count;
    s32 i;
    u8 w;

    (void) c;
    psSetCurrentMtx(GX_PNMTX0);
    w = (pp->size > 42.5) ? 255.0f : 6.0f * pp->size;
    if (prevLineWidth != (s32) w) {
        prevLineWidth = w;
        GXSetLineWidth(w, GX_TO_ONE);
    }
    p = vbuf;
    c = cbuf;
    {
        Vec3* dst = p++;
        dst->x = pp->pos.x;
        dst->y = pp->pos.y;
        dst->z = pp->pos.z;
    }
    if (pp->kind & Tornado) {
        f32 x, y, z;
        calcTornadoLastPos(pp, &x, &y, &z);
        p->x = x;
        p->y = y;
        p->z = z;
        p++;
    } else {
        p->x = pp->pos.x - pp->vel.x;
        p->y = pp->pos.y - pp->vel.y;
        p->z = pp->pos.z - pp->vel.z;
        p++;
    }
    getClrTrail(pp, c);
    c[1] = c[0];
    count = 1;
    c[1].a = (u8) ((f32) c[1].a * pp->trail);
    c += 2;
    last = pp;
    q = pp->next;
    while (q != 0L) {
        if (q->size == pp->size && q->appsrt == 0L &&
            !((q->kind ^ pp->kind) & 0xC0100400) && !(q->kind & DispPoint))
        {
            {
                Vec3* dst = p++;
                dst->x = q->pos.x;
                dst->y = q->pos.y;
                dst->z = q->pos.z;
            }
            if (q->kind & Tornado) {
                f32 x, y, z;
                calcTornadoLastPos(q, &x, &y, &z);
                p->x = x;
                p->y = y;
                p->z = z;
                p++;
            } else {
                p->x = q->pos.x - q->vel.x;
                p->y = q->pos.y - q->vel.y;
                p->z = q->pos.z - q->vel.z;
                p++;
            }
            getClrTrail(q, c);
            c[1] = c[0];
            count++;
            c[1].a = (u8) ((f32) c[1].a * q->trail);
            c += 2;
            if (count == 16) {
                p = vbuf;
                c = cbuf;
                if (pp->kind & DispTexture) {
                    setVtxDesc(2);
                    GXBegin(GX_LINES, GX_VTXFMT2, 0x20U);
                } else {
                    setVtxDesc(3);
                    GXBegin(GX_LINES, GX_VTXFMT3, 0x20U);
                }
                for (i = count; i != 0; i--) {
                    GXPosition3f32(p[1].x, p[1].y, p[1].z);
                    GXColor4u8(c[1].r, c[1].g, c[1].b, c[1].a);
                    if (pp->kind & DispTexture) {
                        GXTexCoord1x8(0);
                    }
                    GXPosition3f32(p[0].x, p[0].y, p[0].z);
                    GXColor4u8(c[0].r, c[0].g, c[0].b, c[0].a);
                    if (pp->kind & DispTexture) {
                        GXTexCoord1x8(1);
                    }
                    p += 2;
                    c += 2;
                }
                p = vbuf;
                c = cbuf;
                count = 0;
            }
            last = q;
            q = q->next;
        } else {
            break;
        }
    }
    if (count != 0) {
        GXColor* draw_colors;

        p = vbuf;
        draw_colors = cbuf;
        if (pp->kind & DispTexture) {
            setVtxDesc(2);
            GXBegin(GX_LINES, GX_VTXFMT2, count * 2);
        } else {
            setVtxDesc(3);
            GXBegin(GX_LINES, GX_VTXFMT3, count * 2);
        }
        for (i = count; i != 0; i--) {
            GXPosition3f32(p[1].x, p[1].y, p[1].z);
            GXColor4u8(draw_colors[1].r, draw_colors[1].g, draw_colors[1].b,
                       draw_colors[1].a);
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(0);
            }
            GXPosition3f32(p[0].x, p[0].y, p[0].z);
            GXColor4u8(draw_colors[0].r, draw_colors[0].g, draw_colors[0].b,
                       draw_colors[0].a);
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(1);
            }
            p += 2;
            draw_colors += 2;
        }
    }
    (void) p;
    return last;
}

static inline void setBlendMode(int blend_mode)
{
    if (HSD_PSDisp_804D792C != blend_mode) {
        HSD_PSDisp_804D792C = blend_mode;
        switch (blend_mode) {
        case 0:
            GXSetBlendMode(GX_BM_BLEND, GX_BL_SRCALPHA, GX_BL_INVSRCALPHA,
                           GX_LO_CLEAR);
            break;
        case 1:
            GXSetBlendMode(GX_BM_BLEND, GX_BL_SRCALPHA, GX_BL_ONE,
                           GX_LO_CLEAR);
            break;
        default:
            OSReport("Particle:setBlendMode:Unknown mode\n");
            break;
        }
    }
}

static inline void psSetCurrentMtx(GXPosNrmMtx idx)
{
    if (HSD_PSDisp_804D7948[0] != idx) {
        HSD_PSDisp_804D7948[0] = idx;
        GXSetCurrentMtx(idx);
    }
}

static inline void psDispSubMakePolygon(HSD_Particle* pp, u8* texform, f32 x,
                                        f32 y, f32 z, f32 x0, f32 y0, f32 z0,
                                        f32 x1, f32 y1, f32 z1, GXColor* color,
                                        f32* prev_x, f32* prev_y, f32* prev_z)
{
    Vec2 right;
    f32 right_z;
    Vec2 up;
    f32 up_z;
    u8* it = texform;


    f32 cx;

    right.x = x0;
    right.y = y0;
    right_z = z0;
    up.x = x1;
    up.y = y1;
    up_z = z1;

    psSetCurrentMtx(GX_PNMTX0);
    if (pp->kind & Trail) {
        if (pp->kind & Tornado) {
            calcTornadoLastPos(pp, prev_x, prev_y, prev_z);
        } else {
            *prev_x = x - pp->vel.x;
            *prev_y = y - pp->vel.y;
            *prev_z = z - pp->vel.z;
        }
        getClrTrail(pp, color);
        if (it == 0L) {
            if (pp->kind & DispTexture) {
                setVtxDesc(2);
                GXBegin(GX_QUADS, GX_VTXFMT2, 4);
            } else {
                setVtxDesc(3);
                GXBegin(GX_QUADS, GX_VTXFMT3, 4);
            }
            GXPosition3f32((*prev_x) - right.x, (*prev_y) - right.y,
                           (*prev_z) - right_z);
            {
                u8 a = color->a;
                u8 b = color->b;
                u8 g = color->g;
                u16 r = color->r;
                GXColor4u8(r, g, b, (u8) ((f32) a * pp->trail));
            }
            if (pp->kind & DispTexture) {
                u8 tex_base = (pp->kind >> 16) & 0xC;

                (*(volatile PPCWGPipe *)0xCC008000).u8 = tex_base;
            }
            GXPosition3f32(x - up.x, y - up.y, z - up_z);
            {
                u8 a = color->a;
                u8 b = color->b;
                u8 g = color->g;
                u16 r = color->r;
                GXColor4u8(r, g, b, a);
            }
            if (pp->kind & DispTexture) {
                (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 1;
            }
            GXPosition3f32(x + right.x, y + right.y, z + right_z);
            {
                u8 a = color->a;
                u8 b = color->b;
                u8 g = color->g;
                u16 r = color->r;
                GXColor4u8(r, g, b, a);
            }
            if (pp->kind & DispTexture) {
                (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 2;
            }
            GXPosition3f32((*prev_x) + up.x, (*prev_y) + up.y,
                           (*prev_z) + up_z);
            {
                u8 a = color->a;
                f32 alpha = (f32) a * pp->trail;
                u8 b = color->b;
                u8 g = color->g;
                u16 r = color->r;
                GXColor4u8(r, g, b, (u8) alpha);
            }
            if (pp->kind & DispTexture) {
                (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 3;
            }
        } else {
            f32 trail_alpha = 255.0f * (1.0f - pp->trail);
            f32 up_len = sqrtf(up.x * up.x + up.y * up.y + up_z * up_z);

            if (up_len != 0.0f) {
                f32 dz = z - (*prev_z);
                f32 dx = x - (*prev_x);
                f32 dy = y - (*prev_y);
                f32 xl = dx * dx;
                f32 yl = dy * dy;
                f32 zl = dz * dz;
                f32 segment_len = sqrtf(zl + (xl + yl));
                f32 ratio = segment_len / up_len;
                u32 primitive_count = *(u32*) it;

                it += sizeof(u32);
                up.x *= ratio;
                up.y *= ratio;
                up_z *= ratio;
                for (; primitive_count != 0; primitive_count--) {
                    GXPrimitive primitive = it[0];
                    u8 count = it[1];
                    s32 i;

                    it += 4;
                    if (pp->kind & DispTexture) {
                        setVtxDesc(5);
                        GXBegin(primitive, GX_VTXFMT5, count);
                    } else {
                        setVtxDesc(3);
                        GXBegin(primitive, GX_VTXFMT3, count);
                    }
                    for (i = count; i > 0; i--) {
                        f32 s = *(f32*) &it[0];
                        f32 sx = 2.0f * (s - 0.5f);
                        f32 t;
                        f32 tx;
                        s32 converted_alpha;
                        s32 alpha;

                        if (pp->kind & TexFlipS) {
                            s = 1.0f - s;
                        }
                        t = *(f32*) &it[4];
                        it += 8;
                        alpha = (s32) (255.0f - t * trail_alpha);
                        converted_alpha = (s32) (255.0f - t * trail_alpha);
                        if (converted_alpha < 0) {
                            alpha = 0;
                        }
                        if (alpha > 0xFF) {
                            alpha = 0xFF;
                        }
                        tx = 2.0f * (t - 0.5f);
                        if (pp->kind & TexFlipT) {
                            t = 1.0f - t;
                        }
                        (*(volatile PPCWGPipe *)0xCC008000).f32 = up.x * tx + (right.x * sx + x);
                        (*(volatile PPCWGPipe *)0xCC008000).f32 = up.y * tx + (right.y * sx + y);
                        (*(volatile PPCWGPipe *)0xCC008000).f32 = up_z * tx + (right_z * sx + z);
                        GXColor4u8(color->r, color->g, color->b, alpha);
                        if (pp->kind & DispTexture) {
                            (*(volatile PPCWGPipe *)0xCC008000).f32 = s;
                            (*(volatile PPCWGPipe *)0xCC008000).f32 = t;
                        }
                    }
                }
            }
        }
    } else if (it == 0L) {
        if (pp->kind & DispTexture) {
            setVtxDesc(0);
            GXBegin(GX_QUADS, GX_VTXFMT0, 4);
        } else {
            setVtxDesc(1);
            GXBegin(GX_QUADS, GX_VTXFMT1, 4);
        }
        GXPosition3f32((cx = x - right.x), y - right.y, z - right_z);
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = (pp->kind >> 16) & 0xC;
        }
        GXPosition3f32((cx = x - up.x), y - up.y, z - up_z);
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 1;
        }
        GXPosition3f32((cx = x + right.x), y + right.y, z + right_z);
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 2;
        }
        GXPosition3f32(x + up.x, y + up.y, z + up_z);
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 3;
        }
    } else {
        u32 primitive_count = *(u32*) it;
        it += sizeof(u32);
        for (; primitive_count != 0; primitive_count--) {
            GXPrimitive primitive = it[0];
            u8 count = it[1];
            s32 i;

            it += 4;
            if (pp->kind & DispTexture) {
                setVtxDesc(4);
                GXBegin(primitive, GX_VTXFMT4, count);
            } else {
                setVtxDesc(1);
                GXBegin(primitive, GX_VTXFMT1, count);
            }
            for (i = count; i > 0; i--) {
                f32 s = *(f32*) &it[0];
                f32 sx = 2.0f * (s - 0.5f);
                f32 t;
                f32 tx;

                if (pp->kind & TexFlipS) {
                    s = 1.0f - s;
                }
                t = *(f32*) &it[4];
                it += 8;
                tx = 2.0f * (t - 0.5f);
                if (pp->kind & TexFlipT) {
                    t = 1.0f - t;
                }
                GXPosition3f32(x + right.x * sx + up.x * tx,
                               y + right.y * sx + up.y * tx,
                               z + right_z * sx + up_z * tx);
                if (pp->kind & DispTexture) {
                    (*(volatile PPCWGPipe *)0xCC008000).f32 = s;
                    (*(volatile PPCWGPipe *)0xCC008000).f32 = t;
                }
            }
        }
    }
    (void) (up.x + up.y + up_z);
}

static inline void psMaskAbsF32(f32* value)
{
    *(s32*) value &= 0x7FFFFFFF;
}




static inline bool psMaskAbsLtF32(f32 value, f32 limit)
{
    psMaskAbsF32(&value);
    return value < limit;
}

static inline bool psMaskAbsGtF32(f32 value, f64 limit)
{
    psMaskAbsF32(&value);
    return value > limit;
}




static inline bool psAbsLtF32(f32 value, f32 limit)
{
    *(s32*) &value &= 0x7FFFFFFF;
    return value < limit;
}

static inline bool psAbsGtF32(f32 value, f64 limit)
{
    *(s32*) &value &= 0x7FFFFFFF;
    return value > limit;
}

static inline bool psDispSubAbsLtF32(f32 value, f32 limit)
{
    return psAbsLtF32(value, limit);
}

static inline bool psDispSubAbsGtF32(f32 value, f64 limit)
{
    return psAbsGtF32(value, limit);
}

static inline void psDispSub(HSD_Particle* pp, u8* texform)
{
    f32 right_y;
    f32 right_x;
    f32 right_z;
    f32 up_x;
    f32 up_y;
    f32 up_z;
    f32 angle;
    f32 x;
    f32 y;
    f32 z;

    x = pp->pos.x;
    y = pp->pos.y;
    z = pp->pos.z;
    if (texform != 0L) {
        right_x = rvmtx[0][0] * pp->size;
        up_x = -rvmtx[0][1] * pp->size;
        right_y = rvmtx[1][0] * pp->size;
        up_y = -rvmtx[1][1] * pp->size;
        right_z = rvmtx[2][0] * pp->size;
        up_z = -rvmtx[2][1] * pp->size;
    } else {
        right_x = HSD_PSDisp_804D7914 * pp->size;
        up_x = HSD_PSDisp_804D7918 * pp->size;
        right_y = HSD_PSDisp_804D791C * pp->size;
        up_y = HSD_PSDisp_804D7920 * pp->size;
        right_z = HSD_PSDisp_804D7924 * pp->size;
        up_z = HSD_PSDisp_804D7928 * pp->size;
    }
    if ((pp->kind & Trail) || (pp->kind & DirVec)) {
        f32 x;
        f32 y;

        if (0.0f == prj[0]) {
            f32 prev_x;
            f32 prev_y;
            f32 prev_z;
            f32 w0;
            f32 w0inv;
            f32 w1;
            f32 w1inv;
            f32 pv13;
            f32 pv03;

            if (pp->kind & Tornado) {
                calcTornadoLastPos(pp, &prev_x, &prev_y, &prev_z);
            } else {
                prev_x = pp->pos.x - pp->vel.x;
                prev_y = pp->pos.y - pp->vel.y;
                prev_z = pp->pos.z - pp->vel.z;
            }
            w0 = vmtx[2][3] +
                 (vmtx[2][2] * pp->pos.z +
                  (vmtx[2][0] * pp->pos.x + vmtx[2][1] * pp->pos.y));
            if (0.0f == w0) {
                return;
            }
            w0inv = -1.0f / w0;
            w1 = vmtx[2][3] + (vmtx[2][2] * prev_z +
                               (vmtx[2][0] * prev_x + vmtx[2][1] * prev_y));
            if (0.0f == w1) {
                return;
            }
            w1inv = -1.0f / w1;
            pv03 = pvmtx[0][3];
            pv13 = pvmtx[1][3];
            x = w0inv * (pv03 + (pvmtx[0][2] * pp->pos.z +
                                 (pvmtx[0][0] * pp->pos.x +
                                  pvmtx[0][1] * pp->pos.y))) -
                w1inv *
                    (pv03 + (pvmtx[0][2] * prev_z +
                             (pvmtx[0][0] * prev_x + pvmtx[0][1] * prev_y)));
            y = w0inv * (pv13 + (pvmtx[1][2] * pp->pos.z +
                                 (pvmtx[1][0] * pp->pos.x +
                                  pvmtx[1][1] * pp->pos.y))) -
                w1inv *
                    (pv13 + (pvmtx[1][2] * prev_z +
                             (pvmtx[1][0] * prev_x + pvmtx[1][1] * prev_y)));


            (void) (pvmtx[1][1] * prev_y);
        } else if (pp->kind & Tornado) {
            f32 prev_x;
            f32 prev_y;
            f32 prev_z;
            f32 dx;
            f32 dy;
            f32 dz;

            calcTornadoLastPos(pp, &prev_x, &prev_y, &prev_z);
            dx = pp->pos.x - prev_x;
            dy = pp->pos.y - prev_y;
            dz = pp->pos.z - prev_z;
            x = pvmtx[0][2] * dz + (pvmtx[0][0] * dx + pvmtx[0][1] * dy);
            y = pvmtx[1][2] * dz + (pvmtx[1][0] * dx + pvmtx[1][1] * dy);
        } else {
            x = pvmtx[0][2] * pp->vel.z +
                (pvmtx[0][0] * pp->vel.x + pvmtx[0][1] * pp->vel.y);
            y = pvmtx[1][2] * pp->vel.z +
                (pvmtx[1][0] * pp->vel.x + pvmtx[1][1] * pp->vel.y);
        }
        if (psDispSubAbsLtF32(y, 1.17549435e-38f)) {
            angle = (x >= 0.0f) ? 1.5707964f : -1.5707964f;
        } else {
            angle = atan2f(x, y);
        }
        if (pp->kind & DirVec) {
            angle += pp->rotate;
        }
    } else {
        angle = pp->rotate;
    }
    if (psDispSubAbsGtF32(angle, 0.01)) {
        Mtx mtx;
        Vec3 axis;

        f32 rx = right_x;
        f32 ry = right_y;
        f32 rz = right_z;
        f32 ux = up_x;
        f32 uz = up_z;
        f32 uy = up_y;
        f32 ax;
        f32 ay;
        f32 az;

        ax = ry * uz - rz * uy;
        {
            f32 axis_y_product = rx * uz;
            ay = rz * ux - axis_y_product;
        }
        az = rx * uy - ry * ux;
        axis.x = ax;
        axis.y = ay;
        axis.z = az;
        PSMTXRotAxisRad(mtx, &axis, angle);
        right_x = mtx[0][2] * rz + (mtx[0][0] * rx + mtx[0][1] * ry);
        right_y = mtx[1][2] * rz + (mtx[1][0] * rx + mtx[1][1] * ry);
        right_z = mtx[2][2] * rz + (mtx[2][0] * rx + mtx[2][1] * ry);
        up_x = mtx[0][2] * uz + (mtx[0][0] * ux + mtx[0][1] * uy);
        up_y = mtx[1][2] * uz + (mtx[1][0] * ux + mtx[1][1] * uy);
        up_z = mtx[2][2] * uz + (mtx[2][0] * ux + mtx[2][1] * uy);
    }
    {
        GXColor color;
        f32 prev_x;
        f32 prev_y;
        f32 prev_z;

        psDispSubMakePolygon(pp, texform, x, y, z, right_x, right_y, right_z,
                             up_x, up_y, up_z, &color, &prev_x, &prev_y,
                             &prev_z);
    }
}

static inline void psScaleAppSRTAxes(HSD_Particle* pp, Mtx mtx)
{
    mtx[0][0] *= pp->size;
    mtx[1][0] *= pp->size;
    mtx[2][0] *= pp->size;
    mtx[0][1] *= pp->size;
    mtx[1][1] *= pp->size;
    mtx[2][1] *= pp->size;
    mtx[0][2] *= pp->size;
    mtx[1][2] *= pp->size;
    mtx[2][2] *= pp->size;
}

static inline void psDispSubAPPSRTPoint(HSD_Particle* pp)
{
    Mtx scratch_mtx;
    Vec3 scratch_scale;
    f32 cur_x;
    f32 cur_y;
    f32 cur_z;
    f32 prev_x;
    f32 prev_y;
    f32 prev_z;
    u8 w;

    psSetCurrentMtx(GX_PNMTX1);
    if (pp->appsrt != 0L) {
        if (pp->appsrt->frameNum != psFrameNum) {
            f32 scale_x;
            f32 scale_y;

            if (pp->appsrt->status != PS_APPSTATUS_STILL) {
                Vec3* translate = &pp->appsrt->translate;
                Vec3* rotate = (Vec3*) &pp->appsrt->rot;
                Vec3* scale = &pp->appsrt->scale;
                MtxPtr mmtx = pp->appsrt->mmtx;

                HSD_MtxSRT(mmtx, scale, rotate, translate, 0L);
            }
            if (pp->appsrt->status == PS_APPSTATUS_ONCE) {
                pp->appsrt->status = PS_APPSTATUS_STILL;
            }
            PSMTXConcat(vmtx, pp->appsrt->mmtx, (MtxPtr) &pp->appsrt->ssx);
            scale_x = pp->appsrt->ssx * pp->appsrt->ssx +
                      pp->appsrt->x74 * pp->appsrt->x74 +
                      pp->appsrt->x84 * pp->appsrt->x84;
            scale_x = sqrtf(scale_x);
            pp->appsrt->x94 = scale_x;
            scale_y = pp->appsrt->ssy * pp->appsrt->ssy +
                      pp->appsrt->x78 * pp->appsrt->x78 +
                      pp->appsrt->x88 * pp->appsrt->x88;
            scale_y = sqrtf(scale_y);
            pp->appsrt->x98 = scale_y;
            if (pp->appsrt->xA2 != 0) {
                PSMTXIdentity(scratch_mtx);
                scratch_mtx[0][3] = pp->appsrt->translate.x;
                scratch_mtx[1][3] = pp->appsrt->translate.y;
                scratch_mtx[2][3] = pp->appsrt->translate.z;
                PSMTXConcat(vmtx, scratch_mtx, scratch_mtx);
                HSD_MtxGetScale(scratch_mtx, &scratch_scale);
                PSMTXScale((MtxPtr) &pp->appsrt->ssx, scratch_scale.x,
                           scratch_scale.y, scratch_scale.z);
                pp->appsrt->x70 = scratch_mtx[0][3];
                pp->appsrt->x80 = scratch_mtx[1][3];
                pp->appsrt->x90 = scratch_mtx[2][3];
            }
        }
        pp->appsrt->frameNum = psFrameNum;
    }
    cur_x = pp->appsrt->x70 +
            (pp->appsrt->x6C * pp->pos.z +
             (pp->appsrt->ssx * pp->pos.x + pp->appsrt->ssy * pp->pos.y));
    cur_y = pp->appsrt->x80 +
            (pp->appsrt->x7C * pp->pos.z +
             (pp->appsrt->x74 * pp->pos.x + pp->appsrt->x78 * pp->pos.y));
    cur_z = pp->appsrt->x90 +
            (pp->appsrt->x8C * pp->pos.z +
             (pp->appsrt->x84 * pp->pos.x + pp->appsrt->x88 * pp->pos.y));
    (void) (pp->pos.x, pp->pos.y);
    (void) (pp->pos.z, pp->size);
    if (pp->kind & Tornado) {
        f32 x;
        f32 y;
        f32 z;

        calcTornadoLastPos(pp, &x, &y, &z);
        prev_x =
            pp->appsrt->x70 + (pp->appsrt->x6C * z +
                               (pp->appsrt->ssx * x + pp->appsrt->ssy * y));
        prev_y =
            pp->appsrt->x80 + (pp->appsrt->x7C * z +
                               (pp->appsrt->x74 * x + pp->appsrt->x78 * y));
        prev_z =
            pp->appsrt->x90 + (pp->appsrt->x8C * z +
                               (pp->appsrt->x84 * x + pp->appsrt->x88 * y));
    } else {
        prev_x =
            pp->appsrt->x70 + (pp->appsrt->x6C * (pp->pos.z - pp->vel.z) +
                               (pp->appsrt->ssx * (pp->pos.x - pp->vel.x) +
                                pp->appsrt->ssy * (pp->pos.y - pp->vel.y)));
        prev_y =
            pp->appsrt->x80 + (pp->appsrt->x7C * (pp->pos.z - pp->vel.z) +
                               (pp->appsrt->x74 * (pp->pos.x - pp->vel.x) +
                                pp->appsrt->x78 * (pp->pos.y - pp->vel.y)));
        prev_z =
            pp->appsrt->x90 + (pp->appsrt->x8C * (pp->pos.z - pp->vel.z) +
                               (pp->appsrt->x84 * (pp->pos.x - pp->vel.x) +
                                pp->appsrt->x88 * (pp->pos.y - pp->vel.y)));
    }

    w = (pp->size > 42.5) ? 255.0f : 6.0f * pp->size;
    if (pp->kind & Trail) {
        GXColor draw_color;

        if (prevLineWidth != (s32) w) {
            prevLineWidth = w;
            GXSetLineWidth(w, GX_TO_ONE);
        }
        getClrTrail(pp, &draw_color);
        if (pp->kind & DispTexture) {
            setVtxDesc(2);
            GXBegin(GX_LINES, GX_VTXFMT2, 2);
        } else {
            setVtxDesc(3);
            GXBegin(GX_LINES, GX_VTXFMT3, 2);
        }
        GXPosition3f32(prev_x, prev_y, prev_z);
        GXColor4u8(draw_color.r, draw_color.g, draw_color.b,
                   (u8) ((f32) draw_color.a * pp->trail));
        if (pp->kind & DispTexture) {
            GXTexCoord1x8(0);
        }
        GXPosition3f32(cur_x, cur_y, cur_z);
        GXColor4u8(draw_color.r, draw_color.g, draw_color.b, draw_color.a);
        if (pp->kind & DispTexture) {
            GXTexCoord1x8(1);
        }
    } else {
        if (prevPointSize != (s32) w) {
            prevPointSize = w;
            GXSetPointSize(w, GX_TO_ONE);
        }
        if (pp->kind & DispTexture) {
            setVtxDesc(0);
            GXBegin(GX_POINTS, GX_VTXFMT0, 1);
        } else {
            setVtxDesc(1);
            GXBegin(GX_POINTS, GX_VTXFMT1, 1);
        }
        GXPosition3f32(cur_x, cur_y, cur_z);
        if (pp->kind & DispTexture) {
            GXTexCoord1x8(1);
        }
    }
}

static inline void psDispSubAppSRT(HSD_Particle* pp, u8* texform)
{
    Mtx draw_mtx;

    Vec3 pad;
    Vec3 scratch_scale;
    f32 x_extent;
    f32 y_extent;
    f32 ax;
    f32 ay;
    f32 bx;
    f32 by;
    f32 angle;
    u8* it = texform;



    f32 w0;
    f32 w1;
    f32 w0inv;
    f32 w1inv;
    f32 f11;
    f32 f8;
    f32 f12;
    f32 f13;
    f32 f16;
    f32 f20;
    f32 f17;
    f32 f18;
    f32 f20b;
    f32 s7F8;
    f32 s7FC;
    f32 s800;
    f32 s804;
    f32 s808;
    f32 prev_pos_x;
    f32 prev_pos_y;
    f32 prev_pos_z;
    f32 cur_x;
    f32 cur_y;
    f32 cur_z;

    if (pp->appsrt->frameNum != psFrameNum) {
        f32 scale_x;
        f32 scale_y;

        if (pp->appsrt->status != PS_APPSTATUS_STILL) {
            Vec3* translate = &pp->appsrt->translate;
            Vec3* rotate = (Vec3*) &pp->appsrt->rot;
            Vec3* scale = &pp->appsrt->scale;
            MtxPtr mmtx = pp->appsrt->mmtx;

            HSD_MtxSRT(mmtx, scale, rotate, translate, 0L);
        }
        if (pp->appsrt->status == PS_APPSTATUS_ONCE) {
            pp->appsrt->status = PS_APPSTATUS_STILL;
        }
        PSMTXConcat(vmtx, pp->appsrt->mmtx, (MtxPtr) &pp->appsrt->ssx);
        scale_x = pp->appsrt->ssx * pp->appsrt->ssx +
                  pp->appsrt->x74 * pp->appsrt->x74 +
                  pp->appsrt->x84 * pp->appsrt->x84;
        scale_x = sqrtf(scale_x);
        pp->appsrt->x94 = scale_x;
        scale_y = pp->appsrt->ssy * pp->appsrt->ssy +
                  pp->appsrt->x78 * pp->appsrt->x78 +
                  pp->appsrt->x88 * pp->appsrt->x88;
        scale_y = sqrtf(scale_y);
        pp->appsrt->x98 = scale_y;
        if (pp->appsrt->xA2 != 0) {
            PSMTXIdentity(draw_mtx);
            draw_mtx[0][3] = pp->appsrt->translate.x;
            draw_mtx[1][3] = pp->appsrt->translate.y;
            draw_mtx[2][3] = pp->appsrt->translate.z;
            PSMTXConcat(vmtx, draw_mtx, draw_mtx);
            HSD_MtxGetScale(draw_mtx, &scratch_scale);
            PSMTXScale((MtxPtr) &pp->appsrt->ssx, scratch_scale.x,
                       scratch_scale.y, scratch_scale.z);
            pp->appsrt->x70 = draw_mtx[0][3];
            pp->appsrt->x80 = draw_mtx[1][3];
            pp->appsrt->x90 = draw_mtx[2][3];
        }
        pp->appsrt->frameNum = psFrameNum;
    }
    {
        f32 pos_x;
        f32 pos_y;

        PSMTXCopy((MtxPtr) &pp->appsrt->ssx, draw_mtx);
        cur_x = draw_mtx[0][3] + (draw_mtx[0][2] * pp->pos.z +
                                  (draw_mtx[0][0] * (pos_x = pp->pos.x) +
                                   draw_mtx[0][1] * (pos_y = pp->pos.y)));
        cur_y = draw_mtx[1][3] +
                (draw_mtx[1][2] * pp->pos.z +
                 (draw_mtx[1][0] * pos_x + draw_mtx[1][1] * pos_y));
        cur_z = draw_mtx[2][3] +
                (draw_mtx[2][2] * pp->pos.z +
                 (draw_mtx[2][0] * pos_x + draw_mtx[2][1] * pos_y));
        if (pp->kind & Tornado) {
            f32 x;
            f32 y;
            f32 z;

            calcTornadoLastPos(pp, &x, &y, &z);
            prev_pos_x =
                draw_mtx[0][3] + (draw_mtx[0][2] * z +
                                  (draw_mtx[0][0] * x + draw_mtx[0][1] * y));
            prev_pos_y =
                draw_mtx[1][3] + (draw_mtx[1][2] * z +
                                  (draw_mtx[1][0] * x + draw_mtx[1][1] * y));
            prev_pos_z =
                draw_mtx[2][3] + (draw_mtx[2][2] * z +
                                  (draw_mtx[2][0] * x + draw_mtx[2][1] * y));
        } else {
            f32 dz = pp->pos.z - pp->vel.z;
            f32 dx = pp->pos.x - pp->vel.x;
            f32 dy = pp->pos.y - pp->vel.y;

            prev_pos_x =
                draw_mtx[0][3] + (draw_mtx[0][2] * dz +
                                  (draw_mtx[0][0] * dx + draw_mtx[0][1] * dy));
            prev_pos_y =
                draw_mtx[1][3] + (draw_mtx[1][2] * dz +
                                  (draw_mtx[1][0] * dx + draw_mtx[1][1] * dy));
            prev_pos_z =
                draw_mtx[2][3] + (draw_mtx[2][2] * dz +
                                  (draw_mtx[2][0] * dx + draw_mtx[2][1] * dy));
        }
        psScaleAppSRTAxes(pp, draw_mtx);
        (void) &pad;
    }
    x_extent = pp->appsrt->x94 * pp->size;
    y_extent = pp->appsrt->x98 * pp->size;
    if (it == 0L) {
        ay = y_extent;
        by = -ay;
        ax = bx = x_extent;
    } else {
        ay = 0.0f;
        ax = x_extent;
        by = -y_extent;
        bx = ay;
    }
    if ((pp->kind & Trail) || (pp->kind & DirVec)) {
        f32 vf1;
        f32 vf2;


        __attribute__((unused)) f32 m00 = pp->appsrt->ssx;
        __attribute__((unused)) f32 m01 = pp->appsrt->ssy;
        __attribute__((unused)) f32 m02 = pp->appsrt->x6C;
        __attribute__((unused)) f32 m03 = pp->appsrt->x70;
        __attribute__((unused)) f32 m10 = pp->appsrt->x74;
        __attribute__((unused)) f32 m11 = pp->appsrt->x78;
        __attribute__((unused)) f32 m12 = pp->appsrt->x7C;
        __attribute__((unused)) f32 m13 = pp->appsrt->x80;
        __attribute__((unused)) f32 m20 = pp->appsrt->x84;
        __attribute__((unused)) f32 m21 = pp->appsrt->x88;
        __attribute__((unused)) f32 m22 = pp->appsrt->x8C;
        __attribute__((unused)) f32 m23 = pp->appsrt->x90;
        if (0.0f == prj[0]) {
            f32 prev_x;
            f32 prev_y;
            f32 prev_z;

            if (pp->kind & Tornado) {
                calcTornadoLastPos(pp, &prev_x, &prev_y, &prev_z);
            } else {
                prev_x = pp->pos.x - pp->vel.x;
                prev_y = pp->pos.y - pp->vel.y;
                prev_z = pp->pos.z - pp->vel.z;
            }
            w0 = pp->appsrt->x90 +
                 (pp->appsrt->x8C * pp->pos.z +
                  (pp->appsrt->x84 * pp->pos.x + pp->appsrt->x88 * pp->pos.y));
            s808 = prj[1] * pp->appsrt->ssx + prj[2] * pp->appsrt->x84;
            s804 = prj[1] * pp->appsrt->ssy + prj[2] * pp->appsrt->x88;
            f16 = prj[1] * pp->appsrt->x6C + prj[2] * pp->appsrt->x8C;
            f20 = prj[1] * pp->appsrt->x70 + prj[2] * pp->appsrt->x90;
            f12 = prj[3] * pp->appsrt->x74 + prj[4] * pp->appsrt->x84;
            f8 = prj[3] * pp->appsrt->x78 + prj[4] * pp->appsrt->x88;
            f11 = prj[3] * pp->appsrt->x7C + prj[4] * pp->appsrt->x8C;
            f13 = prj[3] * pp->appsrt->x80 + prj[4] * pp->appsrt->x90;
            if (0.0f == w0) {
                return;
            }
            w0inv = -1.0f / w0;
            w1 = pp->appsrt->x90 +
                 (pp->appsrt->x8C * prev_z +
                  (pp->appsrt->x84 * prev_x + pp->appsrt->x88 * prev_y));
            if (0.0f == w1) {
                return;
            }
            w1inv = -1.0f / w1;
            vf1 = w0inv * (f20 + (f16 * pp->pos.z +
                                  (s808 * pp->pos.x + s804 * pp->pos.y))) -
                  w1inv *
                      (f20 + (f16 * prev_z + (s808 * prev_x + s804 * prev_y)));
            vf2 =
                w0inv * (f13 + (f11 * pp->pos.z +
                                (f12 * pp->pos.x + f8 * pp->pos.y))) -
                w1inv * (f13 + (f11 * prev_z + (f12 * prev_x + f8 * prev_y)));
        } else {
            s800 = prj[1] * pp->appsrt->ssx + prj[2];
            s7FC = prj[1] * pp->appsrt->ssy + prj[2];
            s7F8 = prj[1] * pp->appsrt->x6C + prj[2];
            f17 = prj[3] * pp->appsrt->x74 + prj[4];
            f18 = prj[3] * pp->appsrt->x78 + prj[4];
            f20b = prj[3] * pp->appsrt->x7C + prj[4];
            if (pp->kind & Tornado) {
                f32 tx;
                f32 ty;
                f32 tz;
                calcTornadoLastPos(pp, &tx, &ty, &tz);
                {
                    f32 dx;
                    f32 dy;
                    f32 dz;

                    dy = pp->pos.y - ty;
                    dx = pp->pos.x - tx;
                    dz = pp->pos.z - tz;
                    vf1 = s7F8 * dz + (s800 * dx + s7FC * dy);
                    vf2 = f20b * dz + (f17 * dx + f18 * dy);
                }
            } else {
                f32 vz;
                f32 vx;
                f32 vy;

                vy = pp->vel.y;
                vx = pp->vel.x;
                vz = pp->vel.z;
                vf1 = s7F8 * vz + (s800 * vx + s7FC * vy);
                vf2 = f20b * vz + (f17 * vx + f18 * vy);
            }
        }
        if (psMaskAbsLtF32(vf2, 1.17549435e-38f)) {
            angle = (-vf1 >= 0.0f) ? 1.5707964f : -1.5707964f;
        } else {
            angle = atan2f(-vf1, vf2);
        }
        if (pp->kind & DirVec) {
            angle += pp->rotate;
        }
    } else {
        angle = pp->rotate;
    }
    if (psMaskAbsGtF32(angle, 0.01)) {
        f32 c = cosf(angle);
        f32 s = sinf(angle);
        f32 old_x = ax;
        ax = c * ax - s * ay;
        ay = s * old_x + c * ay;
        old_x = bx;
        bx = c * bx - s * by;
        by = s * old_x + c * by;
    }
    psSetCurrentMtx(GX_PNMTX1);





    if (pp->kind & Trail) {
        f32 xl;
        f32 yl;
        f32 zl;
        GXColor draw_color;

        getClrTrail(pp, &draw_color);
        if (it == 0L) {
            if (pp->kind & DispTexture) {
                setVtxDesc(2);
                GXBegin(GX_QUADS, GX_VTXFMT2, 4U);
            } else {
                setVtxDesc(3);
                GXBegin(GX_QUADS, GX_VTXFMT3, 4U);
            }
            GXPosition3f32(-ax + prev_pos_x, -ay + prev_pos_y, prev_pos_z);
            GXColor4u8(draw_color.r, draw_color.g, draw_color.b,
                       (u8) ((f32) draw_color.a * pp->trail));
            if (pp->kind & DispTexture) {
                GXTexCoord1x8((pp->kind >> 16) & 0xC);
            }
            GXPosition3f32(-bx + cur_x, -by + cur_y, cur_z);
            GXColor4u8(draw_color.r, draw_color.g, draw_color.b, draw_color.a);
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(((pp->kind >> 16) & 0xC) + 1);
            }
            GXPosition3f32(ax + cur_x, ay + cur_y, cur_z);
            GXColor4u8(draw_color.r, draw_color.g, draw_color.b, draw_color.a);
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(((pp->kind >> 16) & 0xC) + 2);
            }
            GXPosition3f32(bx + prev_pos_x, by + prev_pos_y, prev_pos_z);
            GXColor4u8(draw_color.r, draw_color.g, draw_color.b,
                       (u8) ((f32) draw_color.a * pp->trail));
            if (pp->kind & DispTexture) {
                GXTexCoord1x8(((pp->kind >> 16) & 0xC) + 3);
            }
        } else {
            f32 trail_alpha = 255.0f * (1.0f - pp->trail);
            f32 axis_len = sqrtf(bx * bx + by * by);

            if (axis_len != 0.0f) {
                f32 dx = cur_x - prev_pos_x;
                f32 dy = cur_y - prev_pos_y;
                f32 dz = cur_z - prev_pos_z;
                u32 primitive_count;

                xl = dx * dx;
                yl = dy * dy;
                zl = dz * dz;
                axis_len = sqrtf(zl + (xl + yl)) / axis_len;
                primitive_count = *(u32*) it;

                bx *= axis_len;
                by *= axis_len;
                it += sizeof(u32);
                for (; primitive_count != 0; primitive_count--) {
                    GXPrimitive primitive = it[0];
                    u8 count = it[1];
                    s32 i;

                    it += 4;
                    if (pp->kind & DispTexture) {
                        setVtxDesc(5);
                        GXBegin(primitive, GX_VTXFMT5, count);
                    } else {
                        setVtxDesc(3);
                        GXBegin(primitive, GX_VTXFMT3, count);
                    }
                    for (i = count; i > 0; i--) {
                        f32 s = *(f32*) &it[0];
                        f32 sx = 2.0f * (s - 0.5f);
                        f32 t;
                        f32 tx;
                        s32 converted_alpha;
                        s32 alpha;

                        if (pp->kind & TexFlipS) {
                            s = 1.0f - s;
                        }
                        t = *(f32*) &it[4];
                        it += 8;
                        alpha = (s32) (255.0f - t * trail_alpha);
                        converted_alpha = (s32) (255.0f - t * trail_alpha);
                        if (converted_alpha < 0) {
                            alpha = 0;
                        }
                        if (alpha > 0xFF) {
                            alpha = 0xFF;
                        }
                        tx = 2.0f * (t - 0.5f);
                        if (pp->kind & TexFlipT) {
                            t = 1.0f - t;
                        }
                        GXPosition3f32(cur_x + ax * sx + bx * tx,
                                       cur_y + ay * sx + by * tx, cur_z);
                        GXColor4u8(draw_color.r, draw_color.g, draw_color.b,
                                   (u8) alpha);
                        if (pp->kind & DispTexture) {
                            (*(volatile PPCWGPipe *)0xCC008000).f32 = s;
                            (*(volatile PPCWGPipe *)0xCC008000).f32 = t;
                        }
                    }
                }
            }
        }
    } else if (it == 0L) {
        if (pp->kind & DispTexture) {
            setVtxDesc(0);
            GXBegin(GX_QUADS, GX_VTXFMT0, 4U);
        } else {
            setVtxDesc(1);
            GXBegin(GX_QUADS, GX_VTXFMT1, 4U);
        }
        (*(volatile PPCWGPipe *)0xCC008000).f32 = -ax + cur_x;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = -ay + cur_y;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = cur_z;
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = (pp->kind >> 16) & 0xC;
        }
        (*(volatile PPCWGPipe *)0xCC008000).f32 = -bx + cur_x;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = -by + cur_y;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = cur_z;
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 1;
        }
        (*(volatile PPCWGPipe *)0xCC008000).f32 = ax + cur_x;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = ay + cur_y;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = cur_z;
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 2;
        }
        (*(volatile PPCWGPipe *)0xCC008000).f32 = bx + cur_x;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = by + cur_y;
        (*(volatile PPCWGPipe *)0xCC008000).f32 = cur_z;
        if (pp->kind & DispTexture) {
            (*(volatile PPCWGPipe *)0xCC008000).u8 = ((pp->kind >> 16) & 0xC) + 3;
        }
    } else {
        u32 primitive_count = *(u32*) it;

        it += sizeof(u32);
        for (; primitive_count != 0; primitive_count--) {
            GXPrimitive prim = it[0];
            u8 count = it[1];
            s32 i;
            it += 4;
            if (pp->kind & DispTexture) {
                setVtxDesc(4);
                GXBegin(prim, GX_VTXFMT4, count);
            } else {
                setVtxDesc(1);
                GXBegin(prim, GX_VTXFMT1, count);
            }
            for (i = count; i > 0; i--) {
                f32 s = *(f32*) &it[0];
                f32 sx = 2.0f * (s - 0.5f);
                f32 t;
                f32 tx;

                if (pp->kind & TexFlipS) {
                    s = 1.0f - s;
                }
                t = *(f32*) &it[4];
                it += 8;
                tx = 2.0f * (t - 0.5f);
                if (pp->kind & TexFlipT) {
                    t = 1.0f - t;
                }
                GXPosition3f32(cur_x + ax * sx + bx * tx,
                               cur_y + ay * sx + by * tx, cur_z);
                if (pp->kind & DispTexture) {
                    (*(volatile PPCWGPipe *)0xCC008000).f32 = s;
                    (*(volatile PPCWGPipe *)0xCC008000).f32 = t;
                }
            }
        }
    }
}

static inline void psUpdateBillboardAxes(const Mtx inv_view)
{
    f32 right_x;
    f32 up_x;
    f32 right_y;
    f32 up_y;
    f32 right_z;
    f32 up_z;

    right_x = inv_view[0][0];
    up_x = inv_view[0][1];
    HSD_PSDisp_804D7914 = right_x + up_x;
    HSD_PSDisp_804D7918 = right_x - up_x;
    right_y = inv_view[1][0];
    up_y = inv_view[1][1];
    HSD_PSDisp_804D791C = right_y + up_y;
    HSD_PSDisp_804D7920 = right_y - up_y;
    right_z = inv_view[2][0];
    up_z = inv_view[2][1];
    HSD_PSDisp_804D7924 = right_z + up_z;
    HSD_PSDisp_804D7928 = right_z - up_z;
}





void psDispParticles(u32 target_link, u32 sw)
{
    s32 sp7B4;
    void* sp7B0;
    u32 sp7AC;
    u32 sp7A8;
    u8 sp7A5;
    u8 sp7A4;
    s32 needs_setup;
    void* sp79C;
    psdisp_Tlut tlut_obj;
    __attribute__((unused)) s32 stack_pad;
    GXTexObj sp764;
    HSD_Particle* sorted_particles;
    HSD_Particle* non_edge_particles;
    psdisp_Mtx billboard_mtx;
    f32 y2;
    GXTlutObj gx_tlut_obj;
    s32 alpha_compare_mode;
    s32 prev_tex_interp_near;
    u32 prev_kind;
    HSD_Particle* pp;

    alpha_compare_mode = 0;
    prev_tex_interp_near = 0;
    sp7A5 = 0;
    sp7A4 = 0xFF;
    needs_setup = 1;
    if (sw == 0) {
        if (psFrameNum < 0xFFU) {
            psFrameNum += 1;
            return;
        }
        psFrameNum = 1;
        return;
    }
    sp7B4 = 0;
    do {
        if (target_link & (1 << sp7B4)) {
            particleSort(sp7B4, psFrameNum, &sorted_particles,
                         &non_edge_particles);
            if (sw == 1) {
                pp = sorted_particles;
            } else {
                pp = non_edge_particles;
            }
            while (pp != 0L) {
                HSD_PSTexGroup* tex_group = 0L;
                HSD_PSFormGroup* form_group = 0L;
                u8* form = 0L;
                void* image;
                void* tlut;
                u32 blend_mode;
                u8 alpha0;
                u8 alpha1;
                GXTexWrapMode wrap_s;
                GXTexWrapMode wrap_t;
                f32 scale_s;
                f32 scale_t;
                GXTexFmt fmt;
                u8** tex_table;
                u32 width;
                u32 height;

                if ((sw == 1) && !(pp->kind & TexEdge)) {
                    break;
                }
                if (!(pp->size < 1.19209290e-07F)) {
                    if (needs_setup != 0) {
                        sp79C = 0L;
                        prevPointSize = -1;
                        sp7B0 = 0L;
                        prevLineWidth = -1;
                        prevChanCtrl = -1;
                        psSetupTevInvalidState();
                        sp7A8 = (u32) -1;
                        prev_kind &= 0xFEFFFFFF;
                        sp7AC = (u32) -1;
                        HSD_FogSet(0L);
                        prevChanMat.r = prevChanMat.g = prevChanMat.b = 0xFF;
                        prevChanAmb.r = prevChanAmb.g = prevChanAmb.b = 0xFF;
                        prevChanMat.a = prevChanAmb.a = 0xFF;
                        GXSetChanMatColor(GX_COLOR0A0, prevChanMat);
                        GXSetChanAmbColor(GX_COLOR0A0, prevChanAmb);
                        psSetupTevInvalidState();
                        psSetupTevCommon();
                        psSetColor(&prevColorPrim, 0xFF);
                        psSetColor(&prevColorEnv, 0);
                        psSetColor(&prevColorMat, 0xFF);
                        GXSetTevColor(GX_TEVREG0, prevColorPrim);
                        GXSetTevColor(GX_TEVREG1, prevColorEnv);
                        GXSetTevColor(GX_TEVREG2, prevColorMat);
                        HSD_PSDisp_804D792C = -1;
                        GXSetZCompLoc(((GXBool)0));
                        HSD_CObjGetViewingMtx(HSD_CObjGetCurrent(), vmtx);
                        PSMTXInverse(vmtx, rvmtx);
                        {
                            f32 w0;
                            f32 x_offset;
                            f32 x_scale;
                            f32 w1;
                            f32 y_offset;
                            f32 y_scale;
                            f32 w2;
                            f32 w3;
                            f32 y0;
                            f32 y1;

                            GXGetProjectionv(prj);
                            if (0.0f == prj[0]) {
                                x_scale = prj[1];
                                x_offset = prj[2];
                                w0 = vmtx[2][0];
                                pvmtx[0][0] =
                                    x_scale * vmtx[0][0] + x_offset * w0;
                                w1 = vmtx[2][1];
                                pvmtx[0][1] =
                                    x_scale * vmtx[0][1] + x_offset * w1;
                                w2 = vmtx[2][2];
                                pvmtx[0][2] =
                                    x_scale * vmtx[0][2] + x_offset * w2;
                                w3 = vmtx[2][3];
                                pvmtx[0][3] =
                                    x_scale * vmtx[0][3] + x_offset * w3;
                                y_scale = prj[3];
                                y_offset = prj[4];
                                y0 = y_offset * w0;
                                y1 = y_offset * w1;
                                y2 = y_offset * w2;
                                pvmtx[1][0] = y_scale * vmtx[1][0] + y0;
                                pvmtx[1][1] = y_scale * vmtx[1][1] + y1;
                                pvmtx[1][2] = y_scale * vmtx[1][2] + y2;
                                pvmtx[1][3] =
                                    y_scale * vmtx[1][3] + (y_offset * w3);
                            } else {
                                pvmtx[0][0] = prj[1] * vmtx[0][0] + prj[2];
                                pvmtx[0][1] = prj[1] * vmtx[0][1] + prj[2];
                                pvmtx[0][2] = prj[1] * vmtx[0][2] + prj[2];
                                pvmtx[0][3] = prj[1] * vmtx[0][3] + prj[2];
                                pvmtx[1][0] = prj[3] * vmtx[1][0] + prj[4];
                                pvmtx[1][1] = prj[3] * vmtx[1][1] + prj[4];
                                pvmtx[1][2] = prj[3] * vmtx[1][2] + prj[4];
                                pvmtx[1][3] = prj[3] * vmtx[1][3] + prj[4];
                            }


                            psUpdateBillboardAxes(*(const Mtx*) rvmtx);
                        }
                        GXLoadPosMtxImm(vmtx, GX_PNMTX0);
                        billboard_mtx = HSD_PSDisp_803B9628;
                        GXLoadPosMtxImm(billboard_mtx.mtx, GX_PNMTX1);
                        HSD_PSDisp_804D7948[0] = GX_PNMTX1;
                        psSetCurrentMtx(GX_PNMTX0);
                        GXEnableTexOffsets(GX_TEXCOORD0, ((GXBool)1), ((GXBool)1));
                        GXSetCullMode(GX_CULL_BACK);
                        GXSetArray((GX_VA_TEX0), (HSD_PSDisp_8040C340), (2));

                        psSetupVtxFormat(GX_VTXFMT0, 0, 1, GX_RGB565);
                        psSetupVtxFormat(GX_VTXFMT1, 0, 0, GX_RGB565);
                        psSetupVtxFormat(GX_VTXFMT2, 1, 1, GX_RGB565);
                        psSetupVtxFormat(GX_VTXFMT3, 1, 0, GX_RGB565);
                        psSetupVtxFormat(GX_VTXFMT4, 0, 1, GX_RGBA6);
                        psSetupVtxFormat(GX_VTXFMT5, 1, 1, GX_RGBA6);
                        needs_setup = 0;
                    }

                    blend_mode = (pp->kind >> 0x16U) & 3;
                    setBlendMode(blend_mode);

                    if (pp->aCmpCount != 0) {
                        s32 scale = (65536 * pp->aCmpRemain) / pp->aCmpCount;
                        alpha0 = ((pp->aCmpParam1Target << 16) +
                                  scale * (pp->aCmpParam1 -
                                           pp->aCmpParam1Target)) >>
                                 16;
                        alpha1 = ((pp->aCmpParam2Target << 16) +
                                  scale * (pp->aCmpParam2 -
                                           pp->aCmpParam2Target)) >>
                                 16;
                    } else {
                        alpha0 = pp->aCmpParam1;
                        alpha1 = pp->aCmpParam2;
                    }
                    if ((alpha_compare_mode != pp->aCmpMode) ||
                        (sp7A5 != alpha0) || (sp7A4 != alpha1))
                    {
                        sp7A5 = alpha0;
                        alpha_compare_mode = pp->aCmpMode;
                        sp7A4 = alpha1;
                        GXSetAlphaCompare((alpha_compare_mode >> 3) & 7, sp7A5,
                                          (alpha_compare_mode >> 6) & 3,
                                          alpha_compare_mode & 7, sp7A4);
                    }

                    psSetupTev((u32*) pp);
                    setupChanCtrl(pp);
                    setupChanReg(pp);
                    setupTevReg(pp);
                    if ((pp->kind & TexEdge) != sp7AC) {
                        sp7AC = pp->kind & TexEdge;
                        if ((s32) sp7AC != 0) {
                            GXSetZMode(((GXBool)1), GX_LEQUAL, ((GXBool)1));
                        } else {
                            GXSetZMode(((GXBool)1), GX_LEQUAL, ((GXBool)0));
                        }
                    }
                    if (((pp->kind ^ prev_kind) & DispFog) != 0) {
                        if (pp->kind & DispFog) {
                            HSD_FogSet(HSD_PSDisp_804D7908);
                        } else {
                            HSD_FogSet(0L);
                        }
                    }

                    if (((HSD_PSFormGroup***) psNumCmdList)[pp->bank] !=
                            0L &&
                        (form_group =
                             ((HSD_PSFormGroup***)
                                  psNumCmdList)[pp->bank][pp->texGroup]) !=
                            0L



                    )
                    {
                        form = form_group->formTable[pp->poseNum];
                    } else {
                        form = 0L;
                    }

                    if (pp->kind & DispTexture) {
                        if (pp->kind & MirrorS) {
                            scale_s = 2.0f;
                            wrap_s = GX_MIRROR;
                        } else {
                            scale_s = 1.0f;
                            wrap_s = GX_CLAMP;
                        }
                        if (pp->kind & MirrorT) {
                            scale_t = 2.0f;
                            wrap_t = GX_MIRROR;
                        } else {
                            scale_t = 1.0f;
                            wrap_t = GX_CLAMP;
                        }
                        if ((pp->kind & (MirrorS | MirrorT)) != sp7A8) {
                            Mtx temp_mtx;

                            sp7A8 = pp->kind & (MirrorS | MirrorT);
                            sp7B0 = 0L;
                            PSMTXScale(temp_mtx, scale_s, scale_t, 1.0f);
                            if (pp->kind & MirrorT) {
                                temp_mtx[1][3] = 1.0f;
                            }
                            GXLoadTexMtxImm(temp_mtx, GX_TEXMTX0, GX_MTX2x4);
                            GXSetTexCoordGen2(GX_TEXCOORD0, GX_TG_MTX2x4,
                                              GX_TG_TEX0, GX_TEXMTX0, ((GXBool)0),
                                              GX_PTIDENTITY);
                        }
                        tex_group = psTexGroupArray[pp->bank][pp->texGroup];
                        if (tex_group != 0L) {
                            fmt = tex_group->fmt;
                            tex_table = tex_group->texTable;
                            width = tex_group->width;
                            height = tex_group->height;
                        } else {
                            fmt = 0;
                            height = 0;
                            width = 0;
                            tex_table = 0L;
                        }
                        if (tex_table != 0L) {
                            image = tex_table[pp->poseNum];
                        } else {
                            image = 0L;
                        }
                        if ((fmt == GX_TF_C4) || (fmt == GX_TF_C8)) {
                            if (tex_table != 0L) {
                                void** palettes =
                                    (void**) &tex_table[tex_group->num];
                                if (palettes != 0L) {
                                    if (pp->palNum != 0xFF) {
                                        tlut = palettes[pp->palNum];
                                    } else if (!(pp->kind & ComTLUT)) {
                                        tlut = palettes[pp->poseNum];
                                    } else {
                                        tlut = palettes[0];
                                    }
                                    if (tlut != sp79C) {
                                        tlut_obj.fmt = (GXTlutFmt) (u8)
                                                           tex_group->tlutfmt;
                                        tlut_obj.tlut_name = GX_TLUT0;
                                        tlut_obj.n_entries =
                                            (fmt == GX_TF_C4) ? 0x10 : 0x100;
                                        GXInitTlutObj(&gx_tlut_obj, tlut,
                                                      tlut_obj.fmt,
                                                      tlut_obj.n_entries);
                                        GXLoadTlut(&gx_tlut_obj,
                                                   tlut_obj.tlut_name);
                                    }
                                    sp7B0 = 0L;
                                }
                            }
                        }
                        if ((sp7B0 != image) && (image != 0L)) {
                            sp7B0 = image;
                            switch (fmt) {
                            case GX_TF_C4:
                            case GX_TF_C8:
                                GXInitTexObjCI(&sp764, image, width, height,
                                               fmt, wrap_s, wrap_t, ((GXBool)0),
                                               GX_TLUT0);
                                break;
                            case GX_TF_I4:
                            case GX_TF_I8:
                            case GX_TF_IA4:
                            case GX_TF_IA8:
                            case GX_TF_RGB565:
                            case GX_TF_RGB5A3:
                            case GX_TF_RGBA8:
                            case GX_TF_CMPR:
                                GXInitTexObj(&sp764, image, width, height, fmt,
                                             wrap_s, wrap_t, ((GXBool)0));
                                break;
                            default:
                                ((0) ? ((void) 0) : __assert("src/sysdolphin/baselib/psdisp.c", 2153, "0"));
                                break;
                            }
                            prev_tex_interp_near = pp->kind & TexInterpNear;
                            GXInitTexObjLOD(
                                &sp764,
                                (prev_tex_interp_near != 0) ? GX_NEAR
                                                            : GX_LINEAR,
                                (pp->kind & TexInterpNear) ? GX_NEAR
                                                           : GX_LINEAR,
                                0.0f, 0.0f, 0.0f, ((GXBool)0), ((GXBool)0),
                                GX_ANISO_1);
                            GXLoadTexObj(&sp764, GX_TEXMAP0);
                        }
                        if ((u32) prev_tex_interp_near !=
                            (pp->kind & TexInterpNear))
                        {
                            prev_tex_interp_near = pp->kind & TexInterpNear;
                            GXInitTexObjLOD(
                                &sp764,
                                (prev_tex_interp_near != 0) ? GX_NEAR
                                                            : GX_LINEAR,
                                (s32) (pp->kind & TexInterpNear) != 0
                                    ? GX_NEAR
                                    : GX_LINEAR,
                                0.0f, 0.0f, 0.0f, ((GXBool)0), ((GXBool)0),
                                GX_ANISO_1);
                            GXLoadTexObj(&sp764, GX_TEXMAP0);
                        }
                    }

                    if (pp->kind & DispPoint) {
                        if (pp->appsrt != 0L) {
                            psDispSubAPPSRTPoint(pp);
                        } else {
                            if (pp->kind & Trail) {
                                pp = psDispSubPointTrail(pp);
                            } else {
                                pp = psDispSubPoint(pp);
                            }
                        }
                    } else if (pp->appsrt != 0L) {
                        psDispSubAppSRT(pp, form);
                    } else {
                        psDispSub(pp, form);
                    }
                }

                prev_kind = pp->kind;
                pp = pp->next;
            }
        }
        sp7B4 += 1;
    } while (sp7B4 < 0x10);
    if (needs_setup == 0) {
        HSD_StateInvalidate(-1);
    }
}
