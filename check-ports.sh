#!/bin/bash

# Cross-platform port checker script for LLM Council
# Works on Linux, macOS, and Windows (Git Bash/WSL)

echo "Checking ports for LLM Council..."
echo ""

# Colors for output (if supported)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_port() {
    local port=$1
    local service=$2
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux or macOS
        if command -v lsof &> /dev/null; then
            if lsof -i :$port &> /dev/null; then
                echo -e "${RED}✗ Port $port ($service) is IN USE${NC}"
                echo "  Process using the port:"
                lsof -i :$port | tail -n +2
                return 1
            else
                echo -e "${GREEN}✓ Port $port ($service) is AVAILABLE${NC}"
                return 0
            fi
        elif command -v netstat &> /dev/null; then
            if netstat -an 2>/dev/null | grep -q ":$port "; then
                echo -e "${RED}✗ Port $port ($service) is IN USE${NC}"
                return 1
            else
                echo -e "${GREEN}✓ Port $port ($service) is AVAILABLE${NC}"
                return 0
            fi
        else
            echo -e "${YELLOW}⚠ Cannot check port $port - lsof/netstat not available${NC}"
            return 2
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows (Git Bash or Cygwin)
        if netstat -ano 2>/dev/null | grep -q ":$port "; then
            echo -e "${RED}✗ Port $port ($service) is IN USE${NC}"
            echo "  Process using the port:"
            netstat -ano | grep ":$port "
            return 1
        else
            echo -e "${GREEN}✓ Port $port ($service) is AVAILABLE${NC}"
            return 0
        fi
    else
        echo -e "${YELLOW}⚠ Unknown OS type: $OSTYPE${NC}"
        return 2
    fi
}

# Check backend port (8001)
check_port 8001 "Backend"

# Check frontend port (5174)
check_port 5174 "Frontend"

echo ""
echo "If ports are in use, you can:"
echo "1. Stop the process using the port"
echo "2. Modify ports in docker-compose.yml (see README.md)"
echo "3. Use the check-ports script to find available ports"

