from setuptools import setup, find_packages
import glob
import platform

# Detect the operating system
system = platform.system()


def get_requires():
    requires = [
        "gymnasium",
        "networkx",
        "numpy",
        "ipykernel",
        "sb3_contrib",
        "pandas",
        "jsonschema",
        "optuna",
        # --- Para imitation::
        "seaborn",
        "scikit-learn",
        # "matplotlib",
        # "importlib-metadata",
        # "protobuf",
    ]

    # Define the dependencies based on the operating system
    if system == "Darwin":  # macOS
        requires.extend(["tensorflow-macos", "tensorflow-metal"])
    else:  # Windows or Linux
        requires.extend(["tensorflow"])

    return requires


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
    install_requires=get_requires(),
)
