import setuptools

package = 'Plots'
version = '0.5.1'

setuptools.setup(
    name=package,
    version=version,
    description="A graph plotting app for GNOME",
    packages=setuptools.find_packages(),
    package_data={
        "plots.ui": ["*.glade"],
        "plots": ["shaders/*.glsl"],
        "plots.res": ["*.svg"],
    },
    install_requires=[
        "PyGObject",
        "PyOpenGL",
        "Jinja2",
        "numpy",
        "lark-parser",
    ],
    python_requires='~=3.6',
    entry_points={
        "gui_scripts": [
            "plots=plots:main"
        ],
    },
)
