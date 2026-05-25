from setuptools import setup, find_packages

setup(
    name="cad-asm",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "build123d>=0.10.0",
        "pydantic>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "cad-asm=cad_asm.cli:main",
        ],
    },
    python_requires=">=3.10",
)
