#!/bin/bash
# Vercel build script to ensure fresh builds

echo "🚀 Starting Vercel build process..."
echo "📦 Current commit: $(git rev-parse HEAD)"
echo "🌿 Current branch: $(git branch --show-current)"

# Force clean build
echo "🧹 Cleaning previous build artifacts..."
rm -rf .vercel
rm -rf frontend/.next
rm -rf frontend/out
rm -rf __pycache__
find . -name "*.pyc" -delete

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm ci

# Build frontend
echo "🏗️ Building frontend..."
npm run build

# Return to root
cd ..

# Generate requirements.txt for Vercel functions (critical for Python functions)
echo "📦 Generating requirements.txt for Vercel..."
cp requirements-vercel.txt api/requirements.txt

# Create a build marker
echo "📝 Creating build marker..."
echo "BUILD_TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)" > .vercel_build_info
echo "BUILD_COMMIT=$(git rev-parse HEAD)" >> .vercel_build_info
echo "BUILD_BRANCH=$(git branch --show-current)" >> .vercel_build_info

echo "✅ Build completed successfully!"
