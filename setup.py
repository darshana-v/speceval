from setuptools import setup, find_packages

setup(
    name="speceval",
    version="0.1.0",
    description="Multi-language formal specification inference benchmark for LLMs",
    author="Darshana Venkatadasan",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "docker>=7.0",
        "psutil>=5.9",
        "anthropic>=0.30",
        "openai>=1.30",
    ],
    extras_require={
        "dev": ["pytest>=8.0"],
    },
)
