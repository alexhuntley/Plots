float inside = 0;
float outside = 0;
float prev = 0;
int monotonic = 0;
bool nans = false;
for (float i = 0.0; i < samples; i++) {
    float ii = i + jitter*rand(vec2(graph_pos.x, graph_pos.y + i*step)) - samples/2;
    float y = graph_pos.y + ii*step;
    float xj = jitter*rand(vec2(graph_pos.x + i*step, graph_pos.y));
    float lower = (-0.5+xj)*sample_extent;
    float upper = (0.5+xj)*sample_extent;
    float fp, f;

    f = formula{{formula.id()}}(y) - graph_pos.x;
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
