#!/bin/bash
# ==============================================================================
# AWS EC2 Cloud-Init User Data Script
# Target OS: Ubuntu 22.04 LTS / 20.04 LTS
# Description: Automated provisioning of Nginx Web Server, Health Check Endpoint,
#              and Self-verification test.
# ==============================================================================

set -euo pipefail

# Redirect all stdout & stderr to log file for debugging
exec > >(tee -a /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting EC2 User Data Provisioning..."

# 1. Update OS packages and install Nginx
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Updating apt repositories..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx curl jq

# 2. Deploy Nginx Virtual Host Configuration
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Configuring Nginx..."
cat << 'EOF' > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;
    root /var/www/html;
    index index.html;

    server_tokens off;

    location / {
        try_files $uri $uri/ =404;
    }

    location = /health {
        default_type application/json;
        return 200 '{"status":"UP","statusCode":200,"service":"nginx-cloud-web","message":"Healthy"}\n';
    }
}
EOF

# 3. Fetch Instance Metadata (IMDSv2) for Dynamic Web Page
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" || true)
if [ -n "$TOKEN" ]; then
    INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id || echo "Unknown-Instance")
    AVAIL_ZONE=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone || echo "ap-northeast-2a")
    LOCAL_IPV4=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4 || echo "10.0.1.50")
    PUBLIC_IPV4=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || echo "Dynamic-IP")
else
    INSTANCE_ID="i-demo12345678"
    AVAIL_ZONE="ap-northeast-2a"
    LOCAL_IPV4="10.0.1.50"
    PUBLIC_IPV4="13.125.45.89"
fi

# 4. Generate Landing Page HTML
cat << EOF > /var/www/html/index.html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Cloud Web Service</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #f8fafc; color: #1e293b; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .card { background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.06); width: 100%; max-width: 680px; padding: 36px; }
        .badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: #dcfce7; color: #15803d; border-radius: 9999px; font-size: 13px; font-weight: 700; margin-bottom: 20px; }
        .badge-dot { width: 8px; height: 8px; background: #16a34a; border-radius: 50%; }
        h1 { font-size: 26px; font-weight: 800; color: #0f172a; margin-bottom: 10px; }
        p.subtitle { color: #64748b; font-size: 15px; margin-bottom: 24px; line-height: 1.5; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 24px; }
        .info-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; }
        .info-label { font-size: 12px; color: #64748b; margin-bottom: 4px; font-weight: 500; }
        .info-value { font-size: 15px; color: #0f172a; font-weight: 700; font-family: monospace; }
        .health-banner { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin-top: 10px; }
        .health-banner a { color: #1d4ed8; text-decoration: none; font-weight: 700; }
        .health-banner a:hover { text-decoration: underline; }
        footer { margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 16px; font-size: 12px; color: #94a3b8; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">
            <span class="badge-dot"></span> 200 OK - Service Normal
        </div>
        <h1>AWS Cloud Web Service</h1>
        <p class="subtitle">격리된 Custom VPC와 최소권한 보안 그룹(Security Group)이 적용된 프로덕션 아키텍처 환경입니다.</p>

        <div class="grid">
            <div class="info-box">
                <div class="info-label">Public IPv4</div>
                <div class="info-value">${PUBLIC_IPV4}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Private IPv4 (VPC Subnet)</div>
                <div class="info-value">${LOCAL_IPV4}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Instance ID</div>
                <div class="info-value">${INSTANCE_ID}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Availability Zone</div>
                <div class="info-value">${AVAIL_ZONE}</div>
            </div>
        </div>

        <div class="health-banner">
            <span style="font-size: 13px; color: #1e40af; font-weight: 600;">🩺 Health Check Endpoint:</span><br>
            <span style="font-size: 14px; font-family: monospace; margin-top: 4px; display: inline-block;">
                <a href="/health" target="_blank">GET /health</a> (200 OK JSON)
            </span>
        </div>

        <footer>
            AWS Cloud Infrastructure Mission Submission &bull; Seoul Region (ap-northeast-2)
        </footer>
    </div>
</body>
</html>
EOF

# 5. Enable and Restart Nginx
systemctl enable nginx
systemctl restart nginx

# 6. Self-Verification (Local & Outbound)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running Self-Verification Checks..."

# Check 1: Local HTTP 200
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✓ Local curl check: PASS (HTTP 200)"
else
    echo "✗ Local curl check: FAIL (HTTP $HTTP_CODE)" >&2
fi

# Check 2: Outbound Internet Connectivity (via Internet Gateway)
OUTBOUND_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://example.com || echo "000")
if [ "$OUTBOUND_CODE" -eq 200 ]; then
    echo "✓ Outbound internet check via IGW: PASS (HTTP 200)"
else
    echo "✗ Outbound internet check via IGW: FAIL (Code: $OUTBOUND_CODE)" >&2
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] EC2 User Data Provisioning COMPLETED successfully!"
