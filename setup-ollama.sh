#!/bin/bash

################################################################################
# Ollama Setup Script for DevGenius
# Sets up FREE vision AI (Llama 3.2 Vision) to replace AWS Bedrock
#
# Cost Savings: $0.03 → $0.00 per diagram (100% savings!)
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

################################################################################
# Main Setup
################################################################################

print_header "DevGenius Ollama Setup - FREE Vision AI"

print_info "This script will install Ollama and Llama 3.2 Vision"
print_info "Cost savings: \$0.03 → \$0.00 per diagram (100% savings!)"
echo ""

################################################################################
# Step 1: Check if Ollama is already installed
################################################################################

print_header "Step 1: Checking Ollama Installation"

if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 || echo "unknown")
    print_success "Ollama is already installed: $OLLAMA_VERSION"
else
    print_info "Ollama not found. Installing..."

    # Detect OS
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            print_info "Detected Linux. Installing Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        Darwin*)
            print_info "Detected macOS. Installing Ollama..."
            if command -v brew &> /dev/null; then
                brew install ollama
            else
                print_warning "Homebrew not found. Downloading Ollama installer..."
                curl -fsSL https://ollama.com/install.sh | sh
            fi
            ;;
        *)
            print_error "Unsupported OS: ${OS}"
            print_info "Please install Ollama manually from: https://ollama.com"
            exit 1
            ;;
    esac

    if command -v ollama &> /dev/null; then
        print_success "Ollama installed successfully!"
    else
        print_error "Ollama installation failed"
        exit 1
    fi
fi

################################################################################
# Step 2: Start Ollama service
################################################################################

print_header "Step 2: Starting Ollama Service"

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Ollama service is already running"
else
    print_info "Starting Ollama service..."

    # Start Ollama in background
    if [[ "$OS" == "Darwin"* ]]; then
        # macOS - use open command
        open -a Ollama 2>/dev/null || nohup ollama serve > /tmp/ollama.log 2>&1 &
    else
        # Linux - use systemd or nohup
        if systemctl is-active --quiet ollama 2>/dev/null; then
            systemctl start ollama
        else
            nohup ollama serve > /tmp/ollama.log 2>&1 &
        fi
    fi

    # Wait for Ollama to start
    print_info "Waiting for Ollama to start..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_success "Ollama service started successfully"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_error "Failed to start Ollama service"
        print_info "Try running manually: ollama serve"
        exit 1
    fi
fi

################################################################################
# Step 3: Pull Llama 3.2 Vision model
################################################################################

print_header "Step 3: Downloading Llama 3.2 Vision Model"

# Check if model already exists
if ollama list | grep -q "llama3.2-vision"; then
    print_success "Llama 3.2 Vision model already downloaded"
else
    print_info "Downloading Llama 3.2 Vision model (this may take a few minutes)..."
    print_warning "Model size: ~7GB - ensure you have enough disk space"

    if ollama pull llama3.2-vision; then
        print_success "Llama 3.2 Vision model downloaded successfully"
    else
        print_error "Failed to download Llama 3.2 Vision model"
        exit 1
    fi
fi

################################################################################
# Step 4: Verify installation
################################################################################

print_header "Step 4: Verifying Installation"

# List available models
print_info "Available Ollama models:"
ollama list

# Test the model
print_info "Testing Llama 3.2 Vision..."
if ollama run llama3.2-vision "test" <<< "exit" > /dev/null 2>&1; then
    print_success "Model test successful"
else
    print_warning "Model test failed, but model is installed"
fi

################################################################################
# Step 5: Configure DevGenius
################################################################################

print_header "Step 5: Configuring DevGenius"

# Create .env file if it doesn't exist
if [ ! -f "chatbot/.env" ]; then
    print_info "Creating chatbot/.env file..."
    cat > chatbot/.env << EOF
# Vision AI Provider Configuration
VISION_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision

# AWS Configuration (optional - only needed for Bedrock fallback)
# AWS_REGION=us-east-1
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
EOF
    print_success "Created chatbot/.env"
else
    print_info "chatbot/.env already exists"
    print_warning "Make sure it contains: VISION_PROVIDER=ollama"
fi

################################################################################
# Step 6: Install Python dependencies
################################################################################

print_header "Step 6: Installing Python Dependencies"

cd chatbot

if [ -f "requirements.txt" ]; then
    print_info "Installing Python packages..."

    # Check if venv exists
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install requirements
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    print_success "Python dependencies installed"
else
    print_warning "requirements.txt not found - skipping Python setup"
fi

cd ..

################################################################################
# Done!
################################################################################

print_header "🎉 Setup Complete!"

print_success "Ollama + Llama 3.2 Vision is ready to use!"
echo ""
print_info "Cost Comparison:"
echo "  • Old approach (Bedrock): \$0.03 per diagram"
echo "  • New approach (Ollama):  \$0.00 per diagram ✨"
echo "  • Savings: 100%!"
echo ""
print_info "Next Steps:"
echo "  1. Test the installation:"
echo "     cd chatbot"
echo "     python vision_ai_ollama.py"
echo ""
echo "  2. Generate Terraform from a diagram:"
echo "     python iac_orchestrator.py --image diagram.png --name my-arch --vision-provider ollama"
echo ""
echo "  3. Compare costs:"
echo "     python iac_orchestrator.py --cost-comparison"
echo ""
echo "  4. (Optional) Run with Docker:"
echo "     docker-compose -f docker-compose.ollama.yml up -d"
echo ""
print_success "Enjoy FREE vision AI! 🚀"
