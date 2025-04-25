# Python Package Template

## Quick Start

(Optional) Click the "Use this template" button on GitHub to create a new repository based on this template.

Clone this repository:

```bash
git clone https://github.com/Bardreamaster/python_package_template.git
```

Edit permissions to allow execution of the `init_package.sh` script:

```bash
sudo chmod +x init_package.sh
```

Initialize the package with the desired name, author, and email:

```bash
./init_package.sh --name your-package-name --author "Your Name" --email "your.email@example.com"
```

After running the script, you can delete the `init_package.sh` script.

## Directory Structure

```plaintext
python_package_template/
├── .devcontainer/          # Development container configuration
├── docs/                   # Documentation files
├── src/
    ├──python_package_template/  # Source code for the package
├── tests/                  # test files
├── .gitignore              # Git ignore file with common python patterns
├── .pre-commit-config.yaml # Pre-commit configuration file
├── .pyirc                  # package index configuration
├── init_package.sh         # Script to initialize the package
├── LICENSE                 # License file
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # This file, the README
```

### devcontainer

This repository includes a `.devcontainer` folder for setting up a development container using Visual Studio Code. To use it, follow these steps:
1. Install the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension in Visual Studio Code.
2. Open the repository in Visual Studio Code.
3. Press `F1` and select "Remote-Containers: Reopen in Container" from the command palette.
4. Wait for the container to build and start. This may take a few minutes, especially the first time.
5. Once the container is running, you can start developing your Python package in a consistent environment.

## Related Sources

- [Python Packaging User Guide](https://packaging.python.org)
