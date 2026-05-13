# Test math regex on user's actual content patterns
import re

# The actual content the user has (multi-line $...$ with \triangleq, \mathcal, etc.)
raw = r"""\{\} $d$ \triangleq $Subscript for desired value$
\{\} $q or $ \{\} $q$ \triangleq $ Quaternion-related variable$
\{\} $R or $ \{\} $R$ \triangleq $Rotation matrix-related variable$

az, $ \beta_{z}, ax, ax, a_{g}, a_{yx}, a_{qg} 
Positivegains$ \triangleq $Time modulation parameter$
ci, hi$ \triangleq $ Centers and widths of Gaussians
T$ \triangleq $Time duration
t$ \triangleq $ Continuous time

$ \mathcal{S}_{++}^{n} m \times m $ SPD manifoldSym $ ^{m} 
m symmetric matrix space

$$E=mc^2$$
\[\mathbf{D}^{V}, \mathbf{D}^{W}\]

Some text with $x^2 + y^2 = z^2$ and $a_{ij}$.

\[\boldsymbol{\Phi}=\begin{bmatrix}x_1&x_2\\x_3&x_4\end{bmatrix}\]

[vec\binom{a\quad b}{b\quad d}=\binom{a}{d}\sqrt{2}b\]

A table row: | $d$ | $\triangleq$ | Subscript |"""

# Test current regex
old_regex = r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|\$[^$\n]+\$)'
new_regex = r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$))'

print("=== OLD REGEX (rejects \\n in $...$) ===")
for m in re.finditer(old_regex, raw):
    print(f"  MATCH: {m.group(1)[:80]}...")

print("\n=== NEW REGEX (allows \\n in $...$) ===")
for m in re.finditer(new_regex, raw):
    print(f"  MATCH: {m.group(1)[:80]}...")

# Count how many blocks each catches
old_matches = len(list(re.finditer(old_regex, raw)))
new_matches = len(list(re.finditer(new_regex, raw)))
print(f"\nOld: {old_matches} matches, New: {new_matches} matches")
print(f"New catches {new_matches - old_matches} more math blocks")

# Verify key patterns are caught
checks = [
    r'$ \beta_{z}, ax, ax, a_{g}, a_{yx}, a_{qg} \nPositivegains$',
    r'$ \mathcal{S}_{++}^{n} m \times m $',
    r'$$E=mc^2$$',
    r'\[\mathbf{D}^{V}, \mathbf{D}^{W}\]',
    r'\[\boldsymbol{\Phi}=\begin{bmatrix}',
    r'$d$',
    r'$a_{ij}$',
]
print("\n=== Verification ===")
for check in checks:
    found = bool(re.search(new_regex, raw[raw.find(check[:10]):raw.find(check[:10])+200] if check[:10] in raw else raw))
    print(f"  {'✅' if found else '❌'} {check[:50]}")