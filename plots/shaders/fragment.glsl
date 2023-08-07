/*
   Copyright 2021 Alexander Huntley

   This file is part of Plots.

   Plots is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   Plots is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with Plots.  If not, see <https://www.gnu.org/licenses/>.
*/

#version 330 core
in vec2 graph_pos;
out vec4 rgba;

uniform vec2 pixel_extent;
uniform float scale;
uniform float major_grid;
uniform float minor_grid;
uniform float samples;
uniform float line_thickness;
uniform vec3 fg_color;
uniform vec3 bg_color;

#define pi 3.141592653589793
#define e 2.718281828459045

#define ln(x) log(x)
#define lg(x) log2(x)
#define log_base(b, x) (log(x)/log(b))
#define sec(x) (1.0/cos(x))
#define csc(x) (1.0/sin(x))
#define cosec(x) csc(x)
#define cot(x) (1.0/tan(x))
#define arcsin(x) asin(x)
#define arccos(x) acos(x)
#define arctan(x) atan(x)
#define asec(x) acos(1.0/(x))
#define acsc(x) asin(1.0/(x))
#define acosec(x) acsc(x)
#define acot(x) (atan(1.0/(x)) - ((x) > 0 ? 0.0 : pi))
#define arcsec(x) asec(x)
#define arccsc(x) acsc(x)
#define arccosec(x) acsc(x)
#define arccot(x) acot(x)
#define sech(x) (1.0/cosh(x))
#define csch(x) (1.0/sinh(x))
#define cosech(x) csch(x)
#define coth(x) (1.0/tanh(x))
#define asech(x) acosh(1.0/(x))
#define acsch(x) asinh(1.0/(x))
#define acosech(x) acsch(x)
#define acoth(x) atanh(1.0/(x))
#define sgn(x) sign(x)
#define sinc(x) (sin(x)/(x))

float rand(vec2 co){
    // implementation found at: lumina.sourceforge.net/Tutorials/Noise.html
    return 2*fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453) - 1;
}

float zmod(float x, float y) {
    // mod(x,y), but centered on zero
    return mod(x + y/2, y) - y/2;
}

float factorial(float x) {
    float res = 1;
    for (float i = 1; i <= x; i++)
        res *= i;
    return res;
}

float mypow(float x, float y) {
    if (x >= 0)
        return pow(x, y);
    else if (floor(y) == y) {
        return int(y) % 2 == 0 ? pow(-x, y) : -pow(-x, y);
    }
    return 1. / 0.;
}

{% for f in formulae %}
{{ f.definition() }}
{% endfor %}

void main() {
    vec3 color = bg_color;
    vec3 formula_color = vec3(0);
    float sample_extent = line_thickness*pixel_extent.x;
    float step = sample_extent / samples;
    float jitter = .4;

    float axis_width = pixel_extent.x;
    vec3 minor_color = mix(fg_color, bg_color, 0.8);
    color = mix(minor_color, color, smoothstep(axis_width*.4, axis_width*.6, abs(zmod(graph_pos.x, minor_grid))));
    color = mix(minor_color, color, smoothstep(axis_width*.4, axis_width*.6, abs(zmod(graph_pos.y, minor_grid))));
    vec3 major_color = mix(fg_color, bg_color, 0.6);
    color = mix(major_color, color, smoothstep(axis_width, axis_width*1.05, abs(zmod(graph_pos.x, major_grid))));
    color = mix(major_color, color, smoothstep(axis_width, axis_width*1.05, abs(zmod(graph_pos.y, major_grid))));
    vec3 axis_color = fg_color;
    color = mix(axis_color, color, smoothstep(axis_width*.6, axis_width*.65, abs(graph_pos.x)));
    color = mix(axis_color, color, smoothstep(axis_width*.6, axis_width*.65, abs(graph_pos.y)));

    {% for f in formulae %}
    {
        {{ f.calculation() }}
    }
    {% endfor %}

    rgba = vec4(color, 1);
}
