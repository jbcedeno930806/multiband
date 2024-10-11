from setuptools import setup, find_packages
import glob
import platform

# Detect the operating system
system = platform.system()


setup_requires = ["wheel==0.38.4"]

setup(
    name="multibandsim",
    version="0.0.1",
    description="",
    data_files=glob.glob(".json"),
    author="Jorge Bermudez",
    author_email="jabc.chile@gmail.com",
    url="",
    packages=find_packages(),
    package_data={"": ["**/*.json"]},
    # package_dir={"": "."},
    #   install_requires=INSTALL_REQUIRES,
    include_package_data=True,
    install_requires=[
        "numpy",
        "pip == 24.0",
        "setuptools==65.5.0",
        "gym == 0.21.0",
        "jsonschema",
        "importlib-metadata",
        "protobuf",
        "ipykernel",
    ],
)
