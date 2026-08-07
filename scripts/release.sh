#!/usr/bin/env bash
#
# release.sh - Prepare a new release
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Parse arguments
VERSION="${1:-}"
BUMP_TYPE="${1:-patch}"

if [ -z "${VERSION}" ]; then
    echo "Usage: $0 <version>"
    echo "       $0 <major|minor|patch>"
    echo ""
    echo "Examples:"
    echo "  $0 1.2.0          # Release specific version"
    echo "  $0 patch          # Bump patch version (0.0.1)"
    echo "  $0 minor          # Bump minor version (0.1.0)"
    echo "  $0 major          # Bump major version (1.0.0)"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep -oP 'version\s*=\s*"\K[^"]+' pyproject.toml | head -1)
echo "Current version: ${CURRENT_VERSION}"

# Calculate new version
case "${BUMP_TYPE}" in
    major)
        NEW_VERSION=$(echo "${CURRENT_VERSION}" | awk -F. '{print ($1+1)".0.0"}')
        ;;
    minor)
        NEW_VERSION=$(echo "${CURRENT_VERSION}" | awk -F. '{print $1"."($2+1)".0"}')
        ;;
    patch)
        NEW_VERSION=$(echo "${CURRENT_VERSION}" | awk -F. '{print $1"."$2"."($3+1)}')
        ;;
    *)
        NEW_VERSION="${BUMP_TYPE}"
        ;;
esac

echo "New version: ${NEW_VERSION}"
echo ""

# Confirm
read -p "Continue with release ${NEW_VERSION}? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled."
    exit 0
fi

# Run all checks first
echo "Running pre-release checks..."
./scripts/check.sh || {
    echo "Checks failed. Please fix issues before releasing."
    exit 1
}

# Update version in pyproject.toml
echo "Updating version..."
sed -i "s/version = \"${CURRENT_VERSION}\"/version = \"${NEW_VERSION}\"/" pyproject.toml

# Create git tag
echo "Creating git tag..."
git add pyproject.toml
git commit -m "chore(release): bump version to ${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

echo ""
echo "Release ${NEW_VERSION} prepared!"
echo ""
echo "Next steps:"
echo "  1. Review the commit: git show HEAD"
echo "  2. Push the tag: git push origin v${NEW_VERSION}"
echo "  3. Create release notes on GitHub"
