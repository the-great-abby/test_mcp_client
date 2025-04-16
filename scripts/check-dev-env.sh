#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Helper function to check if string is valid JSON
is_json() {
    if echo "$1" | jq '.' >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Helper function to safely get JSON value with default
get_json_value() {
    local json="$1"
    local key="$2"
    local default="$3"
    
    if ! is_json "$json"; then
        echo "$default"
        return
    fi
    
    local value
    value=$(echo "$json" | jq -r "$key" 2>/dev/null)
    if [ $? -ne 0 ] || [ "$value" = "null" ] || [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

echo -e "${BOLD}🔍 Checking Development Environment...${NC}\n"

# Check system status
echo -e "📊 ${BOLD}Checking system status...${NC}"
status=$(make -f Makefile.ai ai-status 2>/dev/null)
if ! is_json "$status"; then
    echo -e "${RED}✖ Failed to get system status (invalid JSON response)${NC}"
    echo -e "${YELLOW}! Raw output: $status${NC}"
    echo -e "${YELLOW}! Hint: Try running 'make -f Makefile.ai ai-status' directly to see the error${NC}"
    exit 1
fi

# Debug output
echo -e "${YELLOW}Debug: Received JSON response${NC}" >&2
echo "$status" | jq '.' >&2

# Parse services
services=$(get_json_value "$status" '.data.services' "")
containers_running=$(get_json_value "$status" '.data.containers_running' "0")
db_status=$(get_json_value "$status" '.data.database' "not_ready")

echo -e "\n${BOLD}Services Status:${NC}"
if [ -n "$services" ]; then
    IFS=',' read -ra SERVICE_ARRAY <<< "$services"
    for service in "${SERVICE_ARRAY[@]}"; do
        if [ -n "$service" ]; then
            echo -e "${GREEN}✓${NC} $service is registered"
        fi
    done
else
    echo -e "${YELLOW}! No services found. Are the containers running?${NC}"
    SERVICE_ARRAY=()
fi

echo -e "\n${BOLD}Container Health:${NC}"
service_count=${#SERVICE_ARRAY[@]}
if [ "$service_count" -eq 0 ]; then
    echo -e "${YELLOW}! No services registered${NC}"
elif [ "$containers_running" -eq "$service_count" ]; then
    echo -e "${GREEN}✓${NC} All containers running ($containers_running/$service_count)"
else
    echo -e "${RED}✖ Some containers are down ($containers_running/$service_count)${NC}"
fi

echo -e "\n${BOLD}Database Status:${NC}"
if [ "$db_status" = "ready" ]; then
    echo -e "${GREEN}✓${NC} Database is ready"
else
    echo -e "${RED}✖ Database is not ready${NC}"
fi

# Validate all components
echo -e "\n${BOLD}🔄 Validating Components...${NC}"
validate=$(make -f Makefile.ai ai-validate 2>/dev/null)
if ! is_json "$validate"; then
    echo -e "${RED}✖ Validation failed (invalid JSON response)${NC}"
    echo -e "${YELLOW}! Hint: Try running 'make -f Makefile.ai ai-validate' directly to see the error${NC}"
    exit 1
fi

backend_status=$(get_json_value "$validate" '.data.backend_status' "000")
frontend_status=$(get_json_value "$validate" '.data.frontend_status' "000")
redis_ready=$(get_json_value "$validate" '.data.redis_ready' "false")

# Check Backend
echo -e "\n${BOLD}Backend Health:${NC}"
if [ "$backend_status" = "200" ]; then
    echo -e "${GREEN}✓${NC} Backend is healthy"
else
    echo -e "${RED}✖ Backend returned status $backend_status${NC}"
    echo -e "${YELLOW}! Hint: Check if the backend container is running and logs for errors${NC}"
fi

# Check Frontend
echo -e "\n${BOLD}Frontend Status:${NC}"
if [ "$frontend_status" = "200" ]; then
    echo -e "${GREEN}✓${NC} Frontend is responding"
else
    echo -e "${RED}✖ Frontend returned status $frontend_status${NC}"
    echo -e "${YELLOW}! Hint: Check if the frontend container is running and logs for errors${NC}"
fi

# Check Redis
echo -e "\n${BOLD}Redis Status:${NC}"
if [ "$redis_ready" = "true" ]; then
    echo -e "${GREEN}✓${NC} Redis is ready"
else
    echo -e "${RED}✖ Redis is not responding${NC}"
    echo -e "${YELLOW}! Hint: Check if the Redis container is running${NC}"
fi

# Run tests if everything is up
if [ "$backend_status" = "200" ] && [ "$db_status" = "ready" ]; then
    echo -e "\n${BOLD}🧪 Running Tests...${NC}"
    test_result=$(make -f Makefile.ai ai-test 2>/dev/null)
    
    if ! is_json "$test_result"; then
        echo -e "${RED}✖ Failed to run tests (invalid JSON response)${NC}"
    else
        coverage=$(get_json_value "$test_result" '.data.coverage' "0%")
        failed_tests=$(get_json_value "$test_result" '.data.failed_tests' "-1")
        
        echo -e "\n${BOLD}Test Results:${NC}"
        if [ "$failed_tests" -eq 0 ]; then
            echo -e "${GREEN}✓${NC} All tests passing"
            echo -e "${GREEN}✓${NC} Coverage: $coverage"
        elif [ "$failed_tests" -eq -1 ]; then
            echo -e "${RED}✖ Failed to get test results${NC}"
        else
            echo -e "${RED}✖ $failed_tests tests failed${NC}"
            echo -e "${YELLOW}!${NC} Coverage: $coverage"
            echo -e "${YELLOW}! Hint: Run 'make test' to see detailed test output${NC}"
        fi
    fi
fi

# Summary
echo -e "\n${BOLD}📋 Summary:${NC}"
all_good=true

# Only check container count if we have services
if [ ${#SERVICE_ARRAY[@]} -gt 0 ]; then
    [ "$containers_running" -ne ${#SERVICE_ARRAY[@]} ] && all_good=false
fi
[ "$db_status" != "ready" ] && all_good=false
[ "$backend_status" != "200" ] && all_good=false
[ "$frontend_status" != "200" ] && all_good=false
[ "$redis_ready" != "true" ] && all_good=false
if [ "$backend_status" = "200" ] && [ "$db_status" = "ready" ]; then
    [ "$failed_tests" != "0" ] 2>/dev/null && all_good=false
fi

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ Development environment is healthy and ready!${NC}"
else
    echo -e "${YELLOW}! Some components need attention. Check details above.${NC}"
    echo -e "\n${BOLD}Suggested Actions:${NC}"
    echo "1. Run 'make dev' to start all containers"
    echo "2. Check container logs with 'make logs'"
    echo "3. Run 'make check-dev' again to verify"
fi 