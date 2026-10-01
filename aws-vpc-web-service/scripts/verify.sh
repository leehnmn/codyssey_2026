#!/usr/bin/env bash
# ==============================================================================
# AWS Web Service Automated Verification Script
# Tests external accessibility of HTTP root and /health endpoints
# ==============================================================================

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <EC2_PUBLIC_IP>"
    echo "Example: $0 13.125.45.89"
    exit 1
fi

TARGET_IP="$1"
echo "========================================================================"
echo "🔍 Running Verification Tests against target: http://${TARGET_IP}"
echo "========================================================================"

# Test 1: Root URL
echo -n "Test 1: HTTP Root (http://${TARGET_IP}/)... "
STATUS_ROOT=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${TARGET_IP}/" || echo "FAILED")

if [ "$STATUS_ROOT" = "200" ]; then
    echo "✅ PASS (HTTP 200 OK)"
else
    echo "❌ FAIL (Status code: ${STATUS_ROOT})"
fi

# Test 2: Healthcheck Endpoint
echo -n "Test 2: Health Check (http://${TARGET_IP}/health)... "
STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${TARGET_IP}/health" || echo "FAILED")
HEALTH_BODY=$(curl -s --connect-timeout 5 "http://${TARGET_IP}/health" || echo "")

if [ "$STATUS_HEALTH" = "200" ]; then
    echo "✅ PASS (HTTP 200 OK)"
    echo "   Payload: ${HEALTH_BODY}"
else
    echo "❌ FAIL (Status code: ${STATUS_HEALTH})"
fi

# Summary
echo "========================================================================"
if [ "$STATUS_ROOT" = "200" ] && [ "$STATUS_HEALTH" = "200" ]; then
    echo "🎉 ALL TESTS PASSED! Web service is fully operational and publicly accessible."
else
    echo "⚠️  Verification encountered errors. Check Security Group and Route Table."
fi
echo "========================================================================"
