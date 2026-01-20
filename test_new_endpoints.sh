#!/bin/bash

# Test script for new admin endpoints
# Run this after starting the server with: uvicorn app.main:app --reload

BASE_URL="http://localhost:8000"
API_BASE="$BASE_URL/api"

echo "======================================"
echo "Testing New Admin Endpoints"
echo "======================================"
echo ""

# Note: These tests require admin authentication
# You'll need to replace TOKEN with an actual admin JWT token

# Get admin token (you'll need to login first)
# For now, we'll just test that the endpoints exist and return expected error codes

echo "1. Testing Store Configuration Endpoints"
echo "----------------------------------------"

echo "GET /api/admin/store/config"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/config"

echo "GET /api/admin/store/config/branding"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/config/branding"

echo "GET /api/admin/store/config/contact"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/config/contact"

echo "GET /api/admin/store/config/locale"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/config/locale"

echo "GET /api/admin/store/config/smtp"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/config/smtp"

echo ""
echo "2. Testing Pickup Locations Endpoints"
echo "--------------------------------------"

echo "GET /api/admin/store/pickup-locations"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/pickup-locations"

echo ""
echo "3. Testing Email Templates Endpoints"
echo "------------------------------------"

echo "GET /api/admin/store/email-templates"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/email-templates"

echo "GET /api/admin/store/email-templates/variables"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/admin/store/email-templates/variables"

echo ""
echo "======================================"
echo "Test Complete"
echo "======================================"
echo ""
echo "Expected results:"
echo "- Status 401 (Unauthorized) = Endpoint exists but requires auth"
echo "- Status 404 (Not Found) = Endpoint not registered"
echo "- Status 200 (OK) = Endpoint works (if you have auth)"
echo ""
