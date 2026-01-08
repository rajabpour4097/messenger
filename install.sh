#!/bin/bash

#################################################
# SecureChat Quick Install Script
# برای Ubuntu 22.04/24.04
#################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo ""
echo "==========================================="
echo "   🔐 SecureChat Installation Script"
echo "==========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. Creating docker group..."
fi

# Check Ubuntu version
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    print_warning "This script is optimized for Ubuntu. Proceed with caution."
fi

#################################################
# Step 1: Update System
#################################################
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated"

#################################################
# Step 2: Install Docker
#################################################
print_status "Installing Docker..."

# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group
sudo usermod -aG docker $USER

print_success "Docker installed: $(docker --version)"

#################################################
# Step 3: Configure Firewall
#################################################
print_status "Configuring firewall..."

sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https

print_success "Firewall configured"

#################################################
# Step 4: Setup Project
#################################################
print_status "Setting up project..."

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning ".env file created from .env.example"
        print_warning "Please edit .env file with your settings!"
        
        # Generate random keys
        DJANGO_KEY=$(openssl rand -base64 50 | tr -d '\n')
        JWT_KEY=$(openssl rand -base64 50 | tr -d '\n')
        DB_PASS=$(openssl rand -base64 20 | tr -d '\n')
        REDIS_PASS=$(openssl rand -base64 20 | tr -d '\n')
        ROOM_KEY=$(openssl rand -base64 30 | tr -d '\n')
        
        # Update .env with generated keys
        sed -i "s|DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$DJANGO_KEY|g" .env
        sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|g" .env
        sed -i "s|DB_PASSWORD=.*|DB_PASSWORD=$DB_PASS|g" .env
        sed -i "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASS|g" .env
        sed -i "s|ROOM_KEY_PASSWORD=.*|ROOM_KEY_PASSWORD=$ROOM_KEY|g" .env
        
        print_success "Random keys generated"
    else
        print_error ".env.example not found!"
        exit 1
    fi
else
    print_success ".env file already exists"
fi

#################################################
# Step 5: Build and Run
#################################################
print_status "Building and starting containers..."

# Need to use sudo for first run (group not active yet)
sudo docker compose up -d --build

print_success "Containers started"

#################################################
# Step 6: Wait for services
#################################################
print_status "Waiting for services to be ready..."
sleep 10

#################################################
# Step 7: Show Status
#################################################
echo ""
echo "==========================================="
echo "   📊 Installation Status"
echo "==========================================="
echo ""

sudo docker compose ps

echo ""
echo "==========================================="
echo "   ✅ Installation Complete!"
echo "==========================================="
echo ""
echo -e "🌐 Access your application at:"
echo -e "   ${GREEN}http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')${NC}"
echo ""
echo -e "👤 Default admin credentials:"
echo -e "   Username: ${YELLOW}admin${NC}"
echo -e "   Password: ${YELLOW}adminpassword123${NC}"
echo ""
echo -e "${RED}⚠️  IMPORTANT SECURITY STEPS:${NC}"
echo "   1. Change admin password immediately!"
echo "   2. Edit .env file with your domain"
echo "   3. Setup SSL for HTTPS"
echo ""
echo -e "📖 See ${BLUE}DEPLOYMENT.md${NC} for detailed instructions"
echo ""
echo -e "${YELLOW}Note: You may need to logout and login again"
echo -e "      to use docker without sudo${NC}"
echo ""
