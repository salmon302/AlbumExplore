"""Setup configuration for Album Explorer package."""
from setuptools import setup, find_packages

setup(
    name="albumexplore",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PyQt6>=6.4.0",
        "SQLAlchemy>=2.0.0",
        "alembic>=1.11.0",
        "pandas>=2.0.0",
        "networkx>=3.0",
        "pycountry>=22.3.5",
    ],
    extras_require={
        "dev": [
            "black>=23.0.0",
            "rich>=10.0.0",
            "memory_profiler>=0.60.0",
            "psutil>=5.9.0",
            "gprof2dot>=2022.7.29",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-benchmark>=4.0.0",
            "pytest-cov>=4.0.0",
            "line_profiler>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "albumexplore=albumexplore.gui.app:main",
        ],
    },
    python_requires=">=3.8",
)