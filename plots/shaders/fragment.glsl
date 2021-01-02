#version 330 core
in vec2 graph_pos;
out vec3 color;

uniform vec2 pixel_extent;
uniform float scale;

#define ln(x) log(x)
#define pi 3.141592653589793
#define e 2.718281828459045

float rand(vec2 co){
    // implementation found at: lumina.sourceforge.net/Tutorials/Noise.html
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

{% for body, expression in formulae %}
float formula{{ loop.index0 }}(float x) {
    {{ body }}
    return {{ expression }};
}
{% endfor %}

void main() {
    float samples = 20;
    float step = 1.4*pixel_extent.x / samples;
    float jitter = .5;

    {% if formulae %}
    float inside[]= float[]({{ ([0.0] * formulae|length) | join(",") }});
    float outside[]= float[]({{ ([0.0] * formulae|length) | join(",") }});
    float prev[]= float[]({{ ([0.0] * formulae|length) | join(",") }});
    int monotonic[] = int[]({{ ([0] * formulae|length) | join(",") }});
    for (float i = 0.0; i < samples; i++) {
            float ii = i + jitter*rand(vec2(graph_pos.x + i*step, graph_pos.y));
            float x = graph_pos.x + ii*step;
            float yj = jitter*rand(vec2(graph_pos.y, graph_pos.y + i*step));
            float lower = (-0.5+yj)*pixel_extent.y;
            float upper = (0.5+yj)*pixel_extent.y;
            float fp, f;
            {% for _ in formulae %}
            f = formula{{loop.index0}}(x) - graph_pos.y;
            if (lower < f && f < upper)
                inside[{{loop.index0}}] += 1.0;
            else
                outside[{{loop.index0}}] += sign(f);
            fp = prev[{{loop.index0}}];
            if (i != 0.0)
                monotonic[{{loop.index0}}] += int(sign(f - fp));
            prev[{{loop.index0}}] = f;
            {% endfor %}
    }
    {% endif %}
    color = vec3(1.0);
    {% for _ in formulae %}
    if (inside[{{loop.index0}}] > 0.0)
        color = vec3(1.-inside[{{loop.index0}}]/samples);
    if (abs(outside[{{loop.index0}}]) != samples)
        color = vec3(abs(outside[{{loop.index0}}])/samples);
    if (abs(monotonic[{{loop.index0}}]) == int(samples) - 3)
        color = vec3(1.0);

    {% endfor %}

    float axis_width = pixel_extent.x;
    if (abs(graph_pos.x) < axis_width
        || abs(graph_pos.y) < axis_width)
        color -= 1.0-vec3(0.2,0.2,1.0);
    if (abs(mod(graph_pos.x, 1.0)) < axis_width
        || abs(mod(graph_pos.y, 1.0)) < axis_width)
        color -= 1.0-vec3(0.8, 0.8, 1.0);
}
