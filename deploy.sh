#!/bin/bash
# Quick deployment script for Railway
# Run this after you're ready to deploy

echo "🚀 SafeTrace - Railway Deployment"
echo "=================================="
echo ""

# Check if git is clean
if [[ -n $(git status -s) ]]; then
    echo "📝 Uncommitted changes detected. Committing..."
    git add .
    git commit -m "Railway deployment configuration"
    echo "✅ Changes committed"
else
    echo "✅ Git is clean, no changes to commit"
fi

echo ""
echo "📤 Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Push complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Go to https://railway.app"
echo "2. Click 'Start a New Project'"
echo "3. Select 'Deploy from GitHub repo'"
echo "4. Choose 'safetrace' repository"
echo "5. Add environment variables:"
echo "   - BLOCKCHAIR_API_KEY=your_key_here"
echo "   - CACHE_BACKEND=memory"
echo "6. Wait for deployment (~2-3 minutes)"
echo "7. Test: https://your-url.railway.app/docs"
echo ""
echo "🎉 That's it! Your SafeTrace will be live!"
