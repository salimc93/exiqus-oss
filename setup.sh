#!/bin/bash

# GitHub Analyzer Test Environment Setup
# This script sets up everything needed to test your analyzer

echo "🚀 GitHub Analyzer Test Environment Setup"
echo "========================================"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed."
    exit 1
fi

# Create project structure
echo "📁 Creating project structure..."
mkdir -p github-analyzer-testing
cd github-analyzer-testing

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install required packages
echo "📦 Installing required packages..."
pip install PyGithub anthropic python-dotenv pandas

# Create .env template
echo "🔐 Creating .env template..."
cat > .env.example << 'EOF'
# GitHub Personal Access Token
# Get one from: https://github.com/settings/tokens
GITHUB_TOKEN=your_github_token_here

# Anthropic API Key (for AI insights)
# Get one from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenAI API Key (alternative to Anthropic)
# Get one from: https://platform.openai.com/
OPENAI_API_KEY=your_openai_key_here
EOF

# Copy the test repo generator
echo "📝 Creating test repository generator..."
cat > generate_test_repos.py << 'EOF'
# [Content from the test-repo-generator artifact would go here]
# For brevity, this is a placeholder
print("Test repo generator ready!")
EOF

# Create analyzer prototype
echo "🔬 Creating analyzer prototype..."
cat > prototype_analyzer.py << 'EOF'
# [Content from the prototype analyzer would go here]
# For brevity, this is a placeholder
print("Analyzer prototype ready!")
EOF

# Create test runner
echo "🧪 Creating test runner..."
cat > run_tests.py << 'EOF'
# [Content from the test-analyzer-script artifact would go here]
# For brevity, this is a placeholder
print("Test runner ready!")
EOF

# Create README
echo "📚 Creating README..."
cat > README.md << 'EOF'
# GitHub Analyzer Testing Environment

## Quick Start

1. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Generate test repositories**
   ```bash
   python generate_test_repos.py
   ```

3. **Run the analyzer prototype**
   ```bash
   python prototype_analyzer.py
   ```

4. **Run validation tests**
   ```bash
   python run_tests.py
   ```

## Test Repository Types

- **perfect-repo**: Gold standard with all best practices
- **beginner-learning**: Typical learning journey
- **abandoned-project**: Started strong but abandoned
- **poor-practices**: Common bad patterns
- **empty-readme**: Good code, no docs
- **inconsistent-commits**: Sporadic maintenance
- **no-tests**: Production code without tests
- **copy-paste-tutorial**: Obvious tutorial copy
- **excellent-docs**: Outstanding documentation
- **monorepo**: Enterprise-style structure

## Testing Workflow

1. Generate local test repos
2. Test analyzer against local repos
3. Validate results match expectations
4. Optionally push to GitHub for real API testing

## Customizing Tests

Edit `generate_test_repos.py` to add new test cases or modify existing ones.
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy your .env.example to .env and add your API keys"
echo "2. Run: python generate_test_repos.py"
echo "3. Copy the full generator, analyzer, and test runner code from the artifacts above"
echo "4. Start testing your analyzer!"
echo ""
echo "📍 Your testing environment is at: $(pwd)"