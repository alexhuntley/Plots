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
