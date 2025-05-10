from setuptools import setup, find_packages

setup(
    name="bootstrap_spec_dialog",
    version="0.7",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "rich",
        "unidiff",
        "openai",
        "azure-identity",
    ],
    entry_points={
        "console_scripts": [
            "bootstrap-spec=boostrap:main",
        ],
    },
)
