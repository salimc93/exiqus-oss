#!/bin/bash
# Test PR history endpoint with authentication

# Get auth token (assuming user is logged in via frontend)
# For now, just check if endpoint is accessible
curl -s http://localhost:8000/api/v1/pr/ -H "Authorization: Bearer test" 2>&1 | head -c 500
