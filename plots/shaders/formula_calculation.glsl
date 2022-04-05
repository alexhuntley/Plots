float inside = 0;
float outside = 0;
float prev = 0;
int monotonic = 0;
bool nans = false;
for (float i = 0.0; i < samples; i++) {
    float ii = i + jitter*rand(vec2(graph_pos.x + i*step, graph_pos.y)) - samples/2;
    float x = graph_pos.x + ii*step;
    float yj = jitter*rand(vec2(graph_pos.y, graph_pos.y + i*step));
    float lower = (-0.5+yj)*sample_extent;
    float upper = (0.5+yj)*sample_extent;
    float fp, f;

    f = formula{{formula.id()}}(x) - graph_pos.y;
    if (lower < f && f < upper)
        inside += 1.0;
    else
        outside += sign(f);
    fp = prev;
    if (i != 0.0)
        monotonic += int(sign(f - fp));
    prev = f;
    nans = nans || isinf(f) || isnan(f);
}
formula_color = vec3({{ formula.rgba[:3] | join(",") }});
if (abs(monotonic) != int(samples) - 3 && !nans) {
    if (inside > 0.0)
        color = mix(color, formula_color, inside/samples);
    if (abs(outside) != samples)
        color = mix(color, formula_color, 1. - abs(outside)/samples);
}
