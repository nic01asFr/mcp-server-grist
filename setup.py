from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="mcp-server-grist",
    version="0.1.0",
    author="MCP Contributors",
    author_email="info@example.com",
    description="MCP server for Grist API integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/modelcontextprotocol/server-grist",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mcp-server-grist=grist_mcp_server:main",
        ],
    },
)