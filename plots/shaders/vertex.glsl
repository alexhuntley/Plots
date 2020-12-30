#version 330 core
layout (location = 0) in vec3 position;
out vec2 graph_pos;
uniform vec2 viewport;
uniform vec2 translation;
uniform float scale;

void main() {
    gl_Position = vec4(position, 1.0);
    vec2 normalised = position.xy * viewport / viewport.x;
    graph_pos = normalised*scale - translation;
}
