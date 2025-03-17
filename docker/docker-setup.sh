#!/bin/bash
# Helper script for setting up and testing the Docker environment

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Workday Scraper Docker Setup Helper${NC}"
echo "This script will help you set up and test the Docker environment."
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker before continuing."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Warning: Docker Compose is not installed.${NC}"
    echo "You may need to install Docker Compose to use the docker-compose.yml file."
fi

# Check if required files exist
required_files=("docker/Dockerfile" "docker/docker-compose.yml" "docker/entrypoint.sh")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo -e "${RED}Error: The following required files are missing:${NC}"
    for file in "${missing_files[@]}"; do
        echo "- $file"
    done
    exit 1
fi

# Create required directories
echo "Creating required directories..."
mkdir -p data configs logs

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    if [ -f "config/.env.docker" ]; then
        cp config/.env.docker .env
        echo -e "${GREEN}Created .env file from config/.env.docker template.${NC}"
        echo -e "${YELLOW}Please edit the .env file with your Telegram bot token and chat ID.${NC}"
    else
        echo -e "${RED}Error: config/.env.docker template not found.${NC}"
        exit 1
    fi
fi

# Check if there are any config files in the configs directory
if [ ! "$(ls -A configs)" ]; then
    echo -e "${YELLOW}No configuration files found in configs directory.${NC}"
    echo "Creating a sample config file..."
    echo "autodesk,https://autodesk.wd1.myworkdayjobs.com/Ext" > configs/autodesk.txt
    echo -e "${GREEN}Created sample config file at configs/autodesk.txt${NC}"
fi

# Function to check for exec format errors in container logs
check_for_format_errors() {
    if docker-compose -f docker/docker-compose.yml logs | grep -q "exec format error"; then
        echo -e "${RED}Format errors detected in container logs.${NC}"
        echo "This usually happens when the entrypoint script has Windows line endings or architecture mismatch."
        echo "The Dockerfile has been updated to fix these issues."
        echo "Please rebuild the container with option 1."
        return 1
    fi
    return 0
}

# Display options menu
while true; do
    echo
    echo "What would you like to do?"
    echo "1) Build Docker image"
    echo "2) Start container"
    echo "3) Stop container"
    echo "4) View container logs"
    echo "5) Check container status"
    echo "6) Force rebuild (fixes 'exec format error')"
    echo "7) Exit"
    echo
    read -p "Enter your choice (1-7): " choice

    case $choice in
        1)
            echo -e "${GREEN}Building Docker image...${NC}"
            docker-compose -f docker/docker-compose.yml build
            ;;
        2)
            echo -e "${GREEN}Starting container...${NC}"
            docker-compose -f docker/docker-compose.yml up -d
            echo -e "${GREEN}Container started in detached mode.${NC}"
            # Wait a moment for the container to start
            sleep 3
            # Check for exec format errors
            check_for_format_errors
            ;;
        3)
            echo -e "${GREEN}Stopping container...${NC}"
            docker-compose -f docker/docker-compose.yml down
            ;;
        4)
            echo -e "${GREEN}Showing container logs (press Ctrl+C to exit)...${NC}"
            docker-compose -f docker/docker-compose.yml logs -f
            ;;
        5)
            echo -e "${GREEN}Container status:${NC}"
            docker-compose -f docker/docker-compose.yml ps
            ;;
        6)
            echo -e "${GREEN}Force rebuilding Docker image to fix format issues...${NC}"
            # First stop any running containers
            docker-compose -f docker/docker-compose.yml down
            # Clean up previous build cache
            docker-compose -f docker/docker-compose.yml build --no-cache
            echo -e "${GREEN}Rebuild complete. Starting container...${NC}"
            docker-compose -f docker/docker-compose.yml up -d
            echo -e "${GREEN}Container started in detached mode.${NC}"
            # Wait a moment for the container to start
            sleep 3
            # Check for exec format errors
            check_for_format_errors
            ;;
        7)
            echo -e "${GREEN}Exiting.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please enter a number between 1 and 7.${NC}"
            ;;
    esac
done