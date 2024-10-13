from setuptools import setup, find_packages
import glob

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
    include_package_data=True,
    install_requires=[
        "numpy",
        "pandas",
        "pip == 24.2",
        "setuptools==65.5.0",
        "jsonschema",
        "importlib-metadata",
        "protobuf",
        "networkx",
        "ipykernel",
    ],
)
