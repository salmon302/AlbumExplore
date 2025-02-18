from setuptools import setup, find_packages

setup(
	name="albumexplore",
	version="0.1.0",
	package_dir={"": "src"},
	packages=find_packages(where="src", exclude=["tests*"]),
	install_requires=[
		'pandas>=2.0.0',
		'networkx>=3.0.0',
		'fastapi>=0.100.0',
		'sqlalchemy>=2.0.0',
		'pytest>=7.0.0',
		'python-dateutil>=2.8.2',
		'uvicorn>=0.23.0',
		'pycountry>=22.3.5',
		'pydantic>=2.0.0',
	],
	extras_require={
		'test': [
			'pytest>=7.0.0',
			'pytest-cov>=4.0.0',
			'pytest-benchmark>=4.0.0',
			'psutil>=5.9.0',
			'memory_profiler>=0.60.0',
		],
		'dev': [
			'line_profiler>=4.0.0',
			'gprof2dot>=2022.7.29',
		],
	},
	python_requires='>=3.8',
	entry_points={
		'pytest11': [
			'performance = tests.test_performance',
		],
		'console_scripts': [
			'albumexplore-gui = albumexplore.gui.app:main',
		],
	},
)