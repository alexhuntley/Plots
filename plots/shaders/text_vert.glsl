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

layout (location = 0) in vec4 vertex;

out vec2 vUV;

uniform mat4 model;
uniform mat4 projection;

void main()
{
    vUV         = vertex.zw;
    gl_Position = projection * model * vec4(vertex.xy, 0.0, 1.0);
}
