float positives = 0, sample_count = 0;
float sqrt_samples = round(sqrt(samples)/2);
bool nans = false;
float _step = 2*6*step, _jitter = 4*jitter;
for (float i = -sqrt_samples; i < sqrt_samples; i++) {
    for (float j = -sqrt_samples; j < sqrt_samples; j++) {
        vec2 v = vec2(graph_pos.x + i*_step, graph_pos.y + j*_step);
        float ii = i + _jitter*rand(v);
        float _x = graph_pos.x + ii*_step;
        float jj = j + _jitter*rand(v.yx);
        float _y = graph_pos.y + jj*_step;
        float f = formula{{ formula.id() }}(_x, _y);
        if (f > 0)
            positives += 1;
        nans = nans || isinf(f) || isnan(f);
        sample_count += 1;
    }
}
formula_color = vec3({{ formula.rgba[:3] | join(",") }});
if (positives != 0 && positives != sample_count && !nans) {
    color = mix(color, formula_color,
                1 - abs(2*positives/sample_count - 1));
}
