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

{% for expression in formulae %}
float formula{{ loop.index0 }}(float x) {
    return {{ expression }};
}
{% endfor %}

void main() {
    vec2 samples = vec2(6, 6);
    vec2 step = 1.4*pixel_extent / samples;
    float jitter = .8;

    {% if formulae %}
    float count[]= float[]({{ ([0.0] * formulae|length) | join(",") }});
    bool asymptote[] = bool[]({{ (["false"] * formulae|length) | join(",") }});
    for (float i = 0.0; i < samples.x; i++) {
        for (float j = 0.0; j < samples.y; j++) {
            float ii = i + jitter*rand(vec2(graph_pos.x+ i*step.x,graph_pos.y+ j*step.y));
            float jj = j + jitter*rand(vec2(graph_pos.y + i*step.x,graph_pos.x+ j*step.y));
            {% for _ in formulae %}
            float f{{loop.index0}} = formula{{loop.index0}}(graph_pos.x + ii*step.x) - (graph_pos.y + jj*step.y);
            count[{{loop.index0}}] += sign(f{{loop.index0}});
            if (abs(f{{loop.index0}}) > 1000)
                asymptote[{{loop.index0}}] = true;
            {% endfor %}
        }
    }
    float total_samples = samples.x*samples.y;
    {% endif %}
    color = vec3(1.0);
    {% for _ in formulae %}
    if (abs(count[{{loop.index0}}]) != total_samples)// && !asymptote[{{loop.index0}}])
        color = vec3(abs(count[{{loop.index0}}])/total_samples);
    {% endfor %}

    float axis_width = pixel_extent.x;
    if (abs(graph_pos.x) < axis_width
        || abs(graph_pos.y) < axis_width)
        color -= 1.0-vec3(0.2,0.2,1.0);
    if (abs(mod(graph_pos.x, 1.0)) < axis_width
        || abs(mod(graph_pos.y, 1.0)) < axis_width)
        color -= 1.0-vec3(0.8, 0.8, 1.0);
}
