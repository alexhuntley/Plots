float inside = 0;
float outside = 0;
float prev = 0;
int monotonic = 0;
bool nans = false;
float radius = length(graph_pos);
float radial_step = step*1.414;
float theta0 = atan(graph_pos.y, graph_pos.x);
for (float i = 0.0; i < samples; i++) {
    float ii = i + jitter*rand(vec2(graph_pos.x, graph_pos.y + i*step)) - samples/2;
    float r = radius + ii*radial_step;
    float theta_j = jitter*rand(vec2(graph_pos.x + i*step, graph_pos.y))/samples;
    float lower = (-0.5+theta_j)*1.414*pixel_extent.x/radius;
    float upper = (0.5+theta_j)*1.414*pixel_extent.x/radius;
    float f;

    f = formula{{formula.id()}}(r) - theta0;
    if (lower < f && f < upper)
        inside += 1.0;
    else
        outside += sign(f);

    if (i != 0.0)
        monotonic += int(sign(f - prev));
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
