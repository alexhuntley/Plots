# Copyright 2021 Alexander Huntley

# This file is part of Plots.

# Plots is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Plots is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Plots.  If not, see <https://www.gnu.org/licenses/>.


import pytest
import re

import plots.formula as f
from plots.parser import from_latex

from tests.fixtures import cursor

def clean(s):
    return re.sub(r" +", " ", s.replace("\n", " ")).strip()

@pytest.mark.parametrize('latex, body, expr', [
    (r"\sum_{i=1}^{50}3i-1", """
float sum0 = 0.0;
for (float i=1.0; i <= 50.0; i++) {
    sum0 += 3.0*i;
}
""", "sum0-1.0"),
    # x + x Σ[x^2(Σ x^{ij}) + Σexp(ikx)]
    (r"x + x\sum_{i=1}^{4}[x^{2}(\sum_{j=1}^{i}x^{ij})+\sum_{k=1}^{i^{2}}\operatorname{exp}(ikx)]", """
float sum2 = 0.0;
for (float i=1.0; i <= 4.0; i++) {
    float sum0 = 0.0;
    for (float j=1.0; j <= i; j++) {
        sum0 += mypow(x, (i*j));
    }
    float sum1 = 0.0;
    for (float k=1.0; k <= mypow(i, (2.0)); k++) {
        sum1 += exp(i*k*x);
    }
    sum2 += (mypow(x, (2.0))*(sum0)+sum1);
}
""", "x+x*sum2"),
    (r"\prod_{i=4}^{50}\operatorname{sin}(3ix-1)", """
float sum0 = 1.0;
for (float i=4.0; i <= 50.0; i++) {
    sum0 *= sin(3.0*i*x-1.0);
}
""", "sum0"),
])
def test_sum_to_glsl(latex, body, expr):
    f.Sum.glsl_var_counter = 0
    glsl = from_latex(latex).to_glsl()
    assert clean(glsl[0]) == clean(body)
    assert glsl[1] == expr
