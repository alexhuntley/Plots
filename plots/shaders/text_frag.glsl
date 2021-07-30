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

in vec2 vUV;

uniform sampler2D u_texture;
uniform vec3 textColor;

out vec4 fragColor;

void main()
{
    vec2 uv = vUV.xy;
    float text = texture(u_texture, uv).r;
    fragColor = vec4(vec3(1-text), clamp(text, 0.8, 1));
}
