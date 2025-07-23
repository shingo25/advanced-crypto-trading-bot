#!/bin/bash
# Vercel build script - optimized for @vercel/next

echo "🚀 Starting Vercel build process..."
echo "📦 Current commit: $(git rev-parse HEAD)"

# Generate requirements.txt for Vercel Python functions (critical)
echo "🐍 Preparing Python environment for Vercel..."
cp requirements-vercel.txt api/requirements.txt

# Create a build marker
echo "📝 Creating build marker..."
echo "BUILD_TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)" > .vercel_build_info
echo "BUILD_COMMIT=$(git rev-parse HEAD)" >> .vercel_build_info

echo "✅ Python environment ready. @vercel/next will handle frontend build."
