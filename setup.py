from setuptools import setup, find_packages
import platform
import glob

# Detect the operating system
system = platform.system()
# Define the dependencies based on the operating system
if system == "Linux":
    tensorflow_dependency = (
        "tensorflow==2.12.0"  # Reemplaza con la versión adecuada para Linux
    )
elif system == "Darwin":  # macOS
    tensorflow_dependency = (
        "tensorflow-macos==2.12.0"  # Reemplaza con la versión adecuada para macOS
    )
elif system == "Windows":
    tensorflow_dependency = (
        "tensorflow==2.12.0"  # Reemplaza con la versión adecuada para Windows
    )
else:
    raise RuntimeError(f"Unsupported operating system: {system}")


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
        "numpy == 1.23.5",
        "pandas",
        "pip == 24.0", # Esto es obligatorio para usar gym == 0.21.0
        "setuptools==65.5.0",
        "jsonschema",
        "matplotlib",
        "importlib-metadata",
        "protobuf",
        "networkx",
        "ipykernel",
        tensorflow_dependency,
        "gym == 0.21.0",
        "stable-baselines3[extra]==1.8.0",
        "sb3_contrib",
    ],
)

