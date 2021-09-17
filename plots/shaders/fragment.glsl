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
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
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
}

{% for s in sliders %}
{{ s.definition() }}
{% endfor %}

{% for v in variables %}
{{ v.definition() }}
{% endfor %}

{% for f in formulae %}
{{ f.definition() }}
{% endfor %}

void main() {
    vec3 color = vec3(1.0);
    vec3 formula_color = vec3(0);
    float samples = 36;
    float step = 1.4*pixel_extent.x / samples;
    float jitter = .5;

    {% for v in variables %}
    {
        {{ v.calculation() }}
    }
    {% endfor %}

    {% for f in formulae %}
    {
        {{ f.calculation() }}
    }
    {% endfor %}

    float axis_width = pixel_extent.x;
    color -= (1.0-vec3(0.2,0.2,0.2))*(1.0-smoothstep(axis_width*.6, axis_width*.65, abs(graph_pos.x)));
    color -= (1.0-vec3(0.2,0.2,0.2))*(1.0-smoothstep(axis_width*.6, axis_width*.65, abs(graph_pos.y)));
    color -= (1.0-vec3(0.7,0.7,0.7))*(1.0-smoothstep(axis_width, axis_width*1.05, abs(mod(graph_pos.x, major_grid))));
    color -= (1.0-vec3(0.7,0.7,0.7))*(1.0-smoothstep(axis_width, axis_width*1.05, abs(mod(graph_pos.y, major_grid))));
    color -= (1.0-vec3(0.9,0.9,0.9))*(1.0-smoothstep(axis_width, axis_width*1.05, abs(mod(graph_pos.x, minor_grid))));
    color -= (1.0-vec3(0.9,0.9,0.9))*(1.0-smoothstep(axis_width, axis_width*1.05, abs(mod(graph_pos.y, minor_grid))));
    rgba = vec4(color, 1);
}
