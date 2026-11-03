#include "porsche_yuv_gl.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>

/* GLES2 scalar ABI, matching the QNX SDK. Resolve within our GLES handle. */
typedef struct {
    unsigned (*CreateShader)(unsigned);
    void (*ShaderSource)(unsigned, int, const char *const *, const int *);
    void (*CompileShader)(unsigned);
    void (*GetShaderiv)(unsigned, unsigned, int *);
    void (*DeleteShader)(unsigned);
    unsigned (*CreateProgram)(void);
    void (*AttachShader)(unsigned, unsigned);
    void (*BindAttribLocation)(unsigned, unsigned, const char *);
    void (*LinkProgram)(unsigned);
    void (*GetProgramiv)(unsigned, unsigned, int *);
    void (*DeleteProgram)(unsigned);
    void (*UseProgram)(unsigned);
    int (*GetUniformLocation)(unsigned, const char *);
    void (*Uniform1i)(int, int);
    void (*GenTextures)(int, unsigned *);
    void (*DeleteTextures)(int, const unsigned *);
    void (*ActiveTexture)(unsigned);
    void (*BindTexture)(unsigned, unsigned);
    void (*TexParameteri)(unsigned, unsigned, int);
    void (*PixelStorei)(unsigned, int);
    void (*TexImage2D)(unsigned, int, int, int, int, int, unsigned, unsigned, const void *);
    void (*TexSubImage2D)(unsigned, int, int, int, int, int, unsigned, unsigned, const void *);
    void (*BindBuffer)(unsigned, unsigned);
    void (*VertexAttribPointer)(unsigned, int, unsigned, unsigned char, int, const void *);
    void (*EnableVertexAttribArray)(unsigned);
    void (*DisableVertexAttribArray)(unsigned);
    void (*DrawArrays)(unsigned, int, int);
    void (*ReadPixels)(int, int, int, int, unsigned, unsigned, void *);
} gl_api;

typedef struct {
    gl_api gl;
    cw_window *window;
    unsigned program, shaders[2], textures[3];
    int textures_allocated;
    float vertices[16];
} renderer;

static const char *vertex_shader =
    "attribute vec2 position;attribute vec2 texcoord;varying vec2 uv;"
    "void main(){gl_Position=vec4(position,0.0,1.0);uv=texcoord;}";
/* Limited-range BT.601, as in the pinned upstream CarPlay receiver. VUI-driven
 * colour-space selection is not implemented; keep this assumption explicit. */
static const char *fragment_shader =
    "precision mediump float;varying vec2 uv;"
    "uniform sampler2D tex_y;uniform sampler2D tex_u;uniform sampler2D tex_v;"
    "void main(){float y=1.16438356*(texture2D(tex_y,uv).r-0.06274510);"
    "float u=texture2D(tex_u,uv).r-0.50196078;"
    "float v=texture2D(tex_v,uv).r-0.50196078;"
    "gl_FragColor=vec4(y+1.59602678*v,y-0.39176229*u-0.81296764*v,"
    "y+2.01723214*u,1.0);}";

void cw_yuv_gl_stop(cw_yuv_gl *state) {
    renderer *r;
    unsigned i;
    if (!state || !(r = state->implementation))
        return;
    if (r->textures_allocated)
        r->gl.DeleteTextures(3, r->textures);
    for (i = 0; i < 2; ++i)
        if (r->shaders[i])
            r->gl.DeleteShader(r->shaders[i]);
    if (r->program)
        r->gl.DeleteProgram(r->program);
    free(r);
    state->implementation = NULL;
}

static int load(gl_api *g, void *library) {
#define GL_LOAD(name)                                                                              \
    do {                                                                                           \
        g->name = (__typeof__(g->name))dlsym(library, "gl" #name);                                 \
        if (!g->name)                                                                              \
            return 0;                                                                              \
    } while (0)
    GL_LOAD(CreateShader);
    GL_LOAD(ShaderSource);
    GL_LOAD(CompileShader);
    GL_LOAD(GetShaderiv);
    GL_LOAD(DeleteShader);
    GL_LOAD(CreateProgram);
    GL_LOAD(AttachShader);
    GL_LOAD(BindAttribLocation);
    GL_LOAD(LinkProgram);
    GL_LOAD(GetProgramiv);
    GL_LOAD(DeleteProgram);
    GL_LOAD(UseProgram);
    GL_LOAD(GetUniformLocation);
    GL_LOAD(Uniform1i);
    GL_LOAD(GenTextures);
    GL_LOAD(DeleteTextures);
    GL_LOAD(ActiveTexture);
    GL_LOAD(BindTexture);
    GL_LOAD(TexParameteri);
    GL_LOAD(PixelStorei);
    GL_LOAD(TexImage2D);
    GL_LOAD(TexSubImage2D);
    GL_LOAD(BindBuffer);
    GL_LOAD(VertexAttribPointer);
    GL_LOAD(EnableVertexAttribArray);
    GL_LOAD(DisableVertexAttribArray);
    GL_LOAD(DrawArrays);
    GL_LOAD(ReadPixels);
#undef GL_LOAD
    return 1;
}

int cw_yuv_gl_start(cw_yuv_gl *state, cw_window *window, void *library) {
    static const float vertices[] = {-1, -1, 0, 1, 1, -1, 1, 1, 1, 1, 1, 0, -1, 1, 0, 0};
    static const char *uniforms[] = {"tex_y", "tex_u", "tex_v"};
    renderer *r;
    unsigned i;
    int ok;
    if (!state || state->implementation || !window || !window->context || !window->surface ||
        !library || (window->width & 1) || (window->height & 1) || window->width < 64 ||
        window->height < 64 || window->width > 1920 || window->height > 1080)
        return 0;
    r = calloc(1, sizeof(*r));
    if (!r)
        return 0;
    state->implementation = r;
    r->window = window;
    memcpy(r->vertices, vertices, sizeof(vertices));
    if (!load(&r->gl, library))
        goto failed;
    for (i = 0; i < 2; ++i) {
        const char *source = i ? fragment_shader : vertex_shader;
        r->shaders[i] = r->gl.CreateShader(i ? 0x8b30 : 0x8b31);
        if (!r->shaders[i])
            goto failed;
        r->gl.ShaderSource(r->shaders[i], 1, &source, NULL);
        r->gl.CompileShader(r->shaders[i]);
        ok = 0;
        r->gl.GetShaderiv(r->shaders[i], 0x8b81, &ok);
        if (!ok)
            goto failed;
    }
    r->program = r->gl.CreateProgram();
    if (!r->program)
        goto failed;
    r->gl.AttachShader(r->program, r->shaders[0]);
    r->gl.AttachShader(r->program, r->shaders[1]);
    r->gl.BindAttribLocation(r->program, 0, "position");
    r->gl.BindAttribLocation(r->program, 1, "texcoord");
    r->gl.LinkProgram(r->program);
    ok = 0;
    r->gl.GetProgramiv(r->program, 0x8b82, &ok);
    if (!ok)
        goto failed;
    r->gl.UseProgram(r->program);
    r->gl.GenTextures(3, r->textures);
    r->textures_allocated = 1;
    r->gl.PixelStorei(0x0cf5, 1); /* GL_UNPACK_ALIGNMENT */
    for (i = 0; i < 3; ++i) {
        int location = r->gl.GetUniformLocation(r->program, uniforms[i]);
        if (!r->textures[i] || location < 0)
            goto failed;
        r->gl.ActiveTexture(0x84c0 + i);
        r->gl.BindTexture(0x0de1, r->textures[i]);
        r->gl.TexParameteri(0x0de1, 0x2801, 0x2601);
        r->gl.TexParameteri(0x0de1, 0x2800, 0x2601);
        r->gl.TexParameteri(0x0de1, 0x2802, 0x812f);
        r->gl.TexParameteri(0x0de1, 0x2803, 0x812f);
        r->gl.TexImage2D(0x0de1, 0, 0x1909, (int)(window->width >> !!i),
                         (int)(window->height >> !!i), 0, 0x1909, 0x1401, NULL);
        r->gl.Uniform1i(location, (int)i);
    }
    if (window->api.gl_error())
        goto failed;
    return 1;
failed:
    cw_yuv_gl_stop(state);
    return 0;
}

int cw_yuv_gl_draw_sample(cw_yuv_gl *state, const unsigned char *pixels, size_t size,
                           unsigned char sample[4]) {
    renderer *r;
    unsigned i;
    size_t offset = 0;
    cw_window *w;
    if (!state || !(r = state->implementation) || !pixels)
        return 0;
    w = r->window;
    if (size != (size_t)w->width * w->height * 3 / 2)
        return 0;
    r->gl.UseProgram(r->program);
    for (i = 0; i < 3; ++i) {
        unsigned pw = w->width >> !!i, ph = w->height >> !!i;
        r->gl.ActiveTexture(0x84c0 + i);
        r->gl.BindTexture(0x0de1, r->textures[i]);
        r->gl.TexSubImage2D(0x0de1, 0, 0, 0, (int)pw, (int)ph, 0x1909, 0x1401, pixels + offset);
        offset += (size_t)pw * ph;
    }
    w->api.disable(0x0c11); /* no colourbar scissor */
    w->api.disable(0x0be2); /* opaque frame, no blending */
    w->api.disable(0x0b71); /* no inherited depth test */
    w->api.viewport(0, 0, (int)w->width, (int)w->height);
    r->gl.BindBuffer(0x8892, 0);
    r->gl.VertexAttribPointer(0, 2, 0x1406, 0, 4 * sizeof(float), r->vertices);
    r->gl.VertexAttribPointer(1, 2, 0x1406, 0, 4 * sizeof(float), r->vertices + 2);
    r->gl.EnableVertexAttribArray(0);
    r->gl.EnableVertexAttribArray(1);
    r->gl.DrawArrays(0x0006, 0, 4);
    if (sample)
        r->gl.ReadPixels((int)w->width / 2, (int)w->height / 2, 1, 1, 0x1908, 0x1401, sample);
    r->gl.DisableVertexAttribArray(0);
    r->gl.DisableVertexAttribArray(1);
    return !w->api.gl_error() && w->api.swap_buffers(w->display, w->surface);
}

int cw_yuv_gl_draw(cw_yuv_gl *state, const unsigned char *pixels, size_t size) {
    return cw_yuv_gl_draw_sample(state, pixels, size, NULL);
}
