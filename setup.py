import setuptools

# Local imports
import setup_utils

requirements = setup_utils.get_requirements()
dev_requirements = setup_utils.get_dev_requirements()

setuptools.setup(
    name="softsync",
    version="0.0.1",
    description="Sync softly",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=requirements,
    extras_require={'dev': dev_requirements},
    entry_points={'console_scripts': ['softsync=softsync:run']},
)
