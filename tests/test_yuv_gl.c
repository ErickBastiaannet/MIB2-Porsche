#include "porsche_yuv_gl.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failure, shader_count, program_count, texture_count, uploads, swaps, draws;
static unsigned active;
static const unsigned char *input;
static unsigned CreateShader(unsigned type) {
    assert(type == 0x8b30 || type == 0x8b31);
    if (failure == 2)
        return 0;
    ++shader_count;
    return (unsigned)shader_count;
}
static void ShaderSource(unsigned s, int n, const char *const *text, const int *length) {
    assert(s && n == 1 && text && *text && !length);
}
static void CompileShader(unsigned s) { assert(s); }
static void GetShaderiv(unsigned s, unsigned attr, int *ok) {
    assert(s && attr == 0x8b81);
    *ok = failure != 3;
}
static void DeleteShader(unsigned s) {
    assert(s && shader_count > 0);
    --shader_count;
}
static unsigned CreateProgram(void) {
    if (failure == 4)
        return 0;
    ++program_count;
    return 10;
}
static void AttachShader(unsigned p, unsigned s) { assert(p == 10 && s); }
static void BindAttribLocation(unsigned p, unsigned a, const char *name) {
    assert(p == 10 && a < 2 && name);
}
static void LinkProgram(unsigned p) { assert(p == 10); }
static void GetProgramiv(unsigned p, unsigned attr, int *ok) {
    assert(p == 10 && attr == 0x8b82);
    *ok = failure != 5;
}
static void DeleteProgram(unsigned p) {
    assert(p == 10 && program_count);
    --program_count;
}
static void UseProgram(unsigned p) { assert(p == 10); }
static int GetUniformLocation(unsigned p, const char *name) {
    assert(p == 10 && name);
    return failure == 7 ? -1 : 1;
}
static void Uniform1i(int loc, int unit) { assert(loc == 1 && unit >= 0 && unit < 3); }
static void GenTextures(int n, unsigned *textures) {
    int i;
    assert(n == 3);
    for (i = 0; i < 3; ++i) {
        textures[i] = failure == 6 ? 0 : (unsigned)i + 1;
        if (textures[i])
            ++texture_count;
    }
}
static void DeleteTextures(int n, const unsigned *textures) {
    int i;
    assert(n == 3);
    for (i = 0; i < 3; ++i)
        if (textures[i])
            --texture_count;
}
static void ActiveTexture(unsigned unit) {
    assert(unit >= 0x84c0 && unit <= 0x84c2);
    active = unit - 0x84c0;
}
static void BindTexture(unsigned target, unsigned texture) {
    assert(target == 0x0de1 && texture == active + 1);
}
static void TexParameteri(unsigned target, unsigned attr, int value) {
    assert(target == 0x0de1 && attr && value);
}
static void PixelStorei(unsigned a, int value) { assert(a == 0x0cf5 && value == 1); }
static void TexImage2D(unsigned target, int level, int format, int w, int h, int border,
                       unsigned external, unsigned type, const void *data) {
    assert(target == 0x0de1 && !level && format == 0x1909 && !border && external == 0x1909 &&
           type == 0x1401 && !data);
    assert(w == (active ? 32 : 64) && h == (active ? 32 : 64));
}
static void TexSubImage2D(unsigned target, int level, int x, int y, int w, int h, unsigned format,
                          unsigned type, const void *data) {
    assert(target == 0x0de1 && !level && !x && !y && format == 0x1909 && type == 0x1401);
    assert(w == (active ? 32 : 64) && h == (active ? 32 : 64));
    assert(data == input + (active == 0 ? 0 : active == 1 ? 4096 : 5120));
    ++uploads;
}
static void BindBuffer(unsigned target, unsigned value) { assert(target == 0x8892 && !value); }
static void VertexAttribPointer(unsigned index, int n, unsigned type, unsigned char normalized,
                                int stride, const void *values) {
    const float *v = values;
    assert(index < 2 && n == 2 && type == 0x1406 && !normalized && stride == 16 && v);
    if (index == 0)
        assert(v[0] == -1 && v[1] == -1);
    else
        assert(v[0] == 0 && v[1] == 1);
}
static void EnableVertexAttribArray(unsigned a) { assert(a < 2); }
static void DisableVertexAttribArray(unsigned a) { assert(a < 2); }
static void DrawArrays(unsigned mode, int first, int count) {
    assert(mode == 6 && !first && count == 4);
    ++draws;
}
static void ReadPixels(int x, int y, int width, int height, unsigned format, unsigned type, void *out) {
    assert(x == 32 && y == 32 && width == 1 && height == 1 && format == 0x1908 && type == 0x1401);
    memset(out, 255, 4);
}
static unsigned gl_error(void) { return failure == 8; }
static unsigned swap(void *display, void *surface) {
    assert(display && surface);
    ++swaps;
    return failure != 9;
}
static void disable(unsigned feature) {
    assert(feature == 0x0c11 || feature == 0x0be2 || feature == 0x0b71);
}
static void viewport(int x, int y, int w, int h) { assert(!x && !y && w == 64 && h == 64); }
static void *fake_dlsym(void *library, const char *name) {
    assert(library);
    if (failure == 1)
        return NULL;
#define RESOLVE(n)                                                                                 \
    if (!strcmp(name, "gl" #n))                                                                    \
    return (void *)n
    RESOLVE(CreateShader);
    RESOLVE(ShaderSource);
    RESOLVE(CompileShader);
    RESOLVE(GetShaderiv);
    RESOLVE(DeleteShader);
    RESOLVE(CreateProgram);
    RESOLVE(AttachShader);
    RESOLVE(BindAttribLocation);
    RESOLVE(LinkProgram);
    RESOLVE(GetProgramiv);
    RESOLVE(DeleteProgram);
    RESOLVE(UseProgram);
    RESOLVE(GetUniformLocation);
    RESOLVE(Uniform1i);
    RESOLVE(GenTextures);
    RESOLVE(DeleteTextures);
    RESOLVE(ActiveTexture);
    RESOLVE(BindTexture);
    RESOLVE(TexParameteri);
    RESOLVE(PixelStorei);
    RESOLVE(TexImage2D);
    RESOLVE(TexSubImage2D);
    RESOLVE(BindBuffer);
    RESOLVE(VertexAttribPointer);
    RESOLVE(EnableVertexAttribArray);
    RESOLVE(DisableVertexAttribArray);
    RESOLVE(DrawArrays);
    RESOLVE(ReadPixels);
#undef RESOLVE
    assert(0);
    return NULL;
}
#define dlsym fake_dlsym
#include "../native/porsche_yuv_gl.c"
#undef dlsym
int main(void) {
    cw_yuv_gl gl = {0};
    cw_window window;
    unsigned char pixels[6144];
    int i;
    memset(&window, 0, sizeof(window));
    memset(pixels, 128, sizeof(pixels));
    input = pixels;
    window.context = (void *)1;
    window.surface = (void *)2;
    window.display = (void *)3;
    window.width = window.height = 64;
    window.api.gl_error = gl_error;
    window.api.swap_buffers = swap;
    window.api.disable = disable;
    window.api.viewport = viewport;
    for (i = 1; i <= 8; ++i) {
        failure = i;
        assert(!cw_yuv_gl_start(&gl, &window, (void *)4));
        assert(!gl.implementation && !shader_count && !program_count && !texture_count);
    }
    failure = 0;
    assert(cw_yuv_gl_start(&gl, &window, (void *)4));
    assert(!cw_yuv_gl_start(&gl, &window, (void *)4));
    assert(!cw_yuv_gl_draw(&gl, pixels, sizeof(pixels) - 1) && !uploads && !swaps);
    assert(cw_yuv_gl_draw(&gl, pixels, sizeof(pixels)) && uploads == 3 && swaps == 1 && draws == 1);
    failure = 9;
    assert(!cw_yuv_gl_draw(&gl, pixels, sizeof(pixels)));
    failure = 8;
    assert(!cw_yuv_gl_draw(&gl, pixels, sizeof(pixels)));
    cw_yuv_gl_stop(&gl);
    cw_yuv_gl_stop(&gl);
    assert(!shader_count && !program_count && !texture_count);
    puts("YUV_GL_PASS shader/link failures, missing API, texture ownership, plane offsets, "
         "orientation, swap failure, cleanup");
    return 0;
}
