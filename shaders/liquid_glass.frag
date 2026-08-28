#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 sourceRect; // x, y, width, height in full-source UV space
    vec4 fxParams;   // time, distortion, aberration, blur
};

layout(binding = 1) uniform sampler2D source;

vec2 safeUv(vec2 uv) {
    return clamp(uv, vec2(0.001), vec2(0.999));
}

vec3 sampleBlur(vec2 uv, vec2 blurVec) {
    vec3 c = vec3(0.0);
    c += texture(source, safeUv(uv)).rgb * 0.40;
    c += texture(source, safeUv(uv + blurVec)).rgb * 0.15;
    c += texture(source, safeUv(uv - blurVec)).rgb * 0.15;
    c += texture(source, safeUv(uv + vec2(blurVec.y, -blurVec.x))).rgb * 0.15;
    c += texture(source, safeUv(uv - vec2(blurVec.y, -blurVec.x))).rgb * 0.15;
    return c;
}

void main() {
    vec2 local = qt_TexCoord0;
    float time = fxParams.x;
    float distortion = fxParams.y;
    float aberration = fxParams.z;
    float blur = fxParams.w;

    float edge = min(min(local.x, 1.0 - local.x), min(local.y, 1.0 - local.y));
    float edgeMask = 1.0 - smoothstep(0.015, 0.24, edge);

    // A subtle flowing normal field gives the edges the characteristic
    // liquid-lens wobble instead of a flat displacement.
    vec2 flow = vec2(
        sin(local.y * 15.0 + time * 2.2) + sin(local.y * 31.0 - time * 1.3),
        cos(local.x * 13.0 - time * 1.8) + cos(local.x * 27.0 + time * 1.1)
    ) * 0.00065;

    vec2 edgeNormal = normalize(vec2(
        smoothstep(0.22, 0.0, local.x) - smoothstep(0.78, 1.0, local.x),
        smoothstep(0.22, 0.0, local.y) - smoothstep(0.78, 1.0, local.y)
    ) + vec2(0.0001));

    vec2 warp = edgeNormal * distortion * edgeMask + flow * (0.35 + edgeMask * 1.2);
    vec2 uv = sourceRect.xy + local * sourceRect.zw + warp;

    // Lens-like chromatic separation is strongest near the rim.
    vec2 ca = warp * aberration * (0.7 + edgeMask * 2.2);
    float blurScale = blur * (0.55 + edgeMask * 1.5);
    vec2 blurVec = vec2(blurScale, blurScale * 0.7);

    vec3 base = sampleBlur(uv, blurVec);
    float red = texture(source, safeUv(uv + ca)).r;
    float green = base.g;
    float blue = texture(source, safeUv(uv - ca)).b;
    vec3 color = vec3(red, green, blue);

    // Milky glass body: slightly lift luminance while retaining the scene.
    float luminance = dot(color, vec3(0.2126, 0.7152, 0.0722));
    vec3 milk = mix(color, vec3(luminance), 0.10);
    milk = mix(milk, vec3(1.0), 0.055);

    // Fresnel-like rim highlight.
    float rim = pow(edgeMask, 1.8);
    milk += vec3(0.55, 0.72, 1.0) * rim * 0.035;

    // Very soft animated sheen passing across the surface.
    float sheen = smoothstep(0.0, 1.0, sin((local.x + local.y) * 7.0 - time * 1.25) * 0.5 + 0.5);
    milk += vec3(1.0) * sheen * 0.018;

    fragColor = vec4(milk, 0.76) * qt_Opacity;
}
