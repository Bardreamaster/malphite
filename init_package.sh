#!/bin/bash

# Exit on error
set -e

# Function to display usage instructions
display_usage() {
    echo "Usage: $0 --name PACKAGE_NAME --author AUTHOR_NAME --email AUTHOR_EMAIL"
    echo
    echo "Configure a Python package with custom name, author, and email."
    echo "Required arguments:"
    echo "  --name    Package name (use-hyphens-for-multi-word-names)"
    echo "  --author  Author's name"
    echo "  --email   Author's email"
    echo
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --name)
        PACKAGE_NAME="$2"
        shift 2
        ;;
        --author)
        AUTHOR_NAME="$2"
        shift 2
        ;;
        --email)
        AUTHOR_EMAIL="$2"
        shift 2
        ;;
        --help|-h)
        display_usage
        ;;
        *)
        echo "Unknown option: $1"
        display_usage
        ;;
    esac
done

# Check if required arguments are provided
if [ -z "$PACKAGE_NAME" ] || [ -z "$AUTHOR_NAME" ] || [ -z "$AUTHOR_EMAIL" ]; then
    echo "Error: missing required arguments"
    display_usage
fi

# Convert hyphenated package name to underscore format for Python directory
PACKAGE_NAME_UNDERSCORE=$(echo $PACKAGE_NAME | tr '-' '_')

echo "Initializing Python package:"
echo "Package Name: $PACKAGE_NAME"
echo "Python Module Name: $PACKAGE_NAME_UNDERSCORE"
echo "Author: $AUTHOR_NAME"
echo "Email: $AUTHOR_EMAIL"
echo

# Update pyproject.toml
echo "Updating pyproject.toml..."
sed -i "s/name = \"python-package-template\"/name = \"$PACKAGE_NAME\"/" pyproject.toml
sed -i "s/{ name = \"changshan\", email = \"changshanshi@outlook.com\" }/{ name = \"$AUTHOR_NAME\", email = \"$AUTHOR_EMAIL\" }/" pyproject.toml

# Update the source directory name
echo "Renaming source directory..."
if [ -d "src/python_package_template" ]; then
    mkdir -p "src/$PACKAGE_NAME_UNDERSCORE"
    # Copy files from old directory to new directory
    cp -r src/python_package_template/* "src/$PACKAGE_NAME_UNDERSCORE/"
    # Remove old directory
    rm -rf src/python_package_template
    echo "Source directory renamed from 'src/python_package_template' to 'src/$PACKAGE_NAME_UNDERSCORE'"
else
    echo "Warning: src/python_package_template directory not found"
fi

# Update README.md
echo "Updating README.md..."
cat > README.md << EOF
# $PACKAGE_NAME

## Installation

\`\`\`bash
pip install $PACKAGE_NAME
\`\`\`

## Usage

\`\`\`python
import $PACKAGE_NAME_UNDERSCORE

# Add usage examples here
\`\`\`

## License

MIT License
EOF

# Initialize Sphinx documentation
echo "Initializing Sphinx documentation..."

# Create docs directory if it doesn't exist
mkdir -p docs

# Check if sphinx-quickstart is installed
if ! command -v sphinx-quickstart &> /dev/null; then
    echo "Warning: sphinx-quickstart command not found. Installing sphinx and related packages..."
    python3 -m pip install -r docs/requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install Sphinx and related packages."
        exit 1
    fi
    echo "Sphinx and related packages installed successfully."
fi

# Run sphinx-quickstart with error handling
cd docs
echo "Running sphinx-quickstart..."
sphinx-quickstart --sep \
    --no-batchfile \
    --project "$PACKAGE_NAME" \
    --author "$AUTHOR_NAME" \
    --release "0.1.0" \
    --language en \
    --makefile \
    --ext-autodoc \
    --ext-githubpages \
    --extensions "sphinx.ext.napoleon,sphinx-copybutton,sphinx_rtd_theme,myst-parser"

if [ $? -ne 0 ]; then
    echo "Warning: sphinx-quickstart failed."
fi

echo "Package successfully initialized!"
echo "Next steps:"
echo "1. Add your code to src/$PACKAGE_NAME_UNDERSCORE"
echo "2. Update the documentation in docs/source/"
echo "3. Build your package with: python -m build"
echo "4. Build documentation with: cd docs && make html"
