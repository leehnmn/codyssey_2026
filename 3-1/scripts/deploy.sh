#!/usr/bin/env bash
# ==============================================================================
# AWS Infrastructure Automated Deployment Script
# Mission: VPC, Public Subnet, IGW, Route Table, Security Group, EC2 Provisioning
# Region: ap-northeast-2 (Seoul)
# ==============================================================================

set -euo pipefail

# Configuration Variables
REGION="ap-northeast-2"
VPC_CIDR="10.0.0.0/16"
SUBNET_CIDR="10.0.1.0/24"
AVAILABILITY_ZONE="ap-northeast-2a"
INSTANCE_TYPE="t3.micro"
PROJECT_TAG="AWS-Web-Service-Mission"

echo "========================================================================"
echo "🚀 Starting AWS Web Service Infrastructure Deployment in [${REGION}]"
echo "========================================================================"

# Check AWS CLI prerequisites
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed or not in PATH."
    exit 1
fi

# Detect Operator Public IP for SSH Least-Privilege Rule
MY_IP=$(curl -s https://checkip.amazonaws.com || curl -s https://ifconfig.me)
if [ -z "$MY_IP" ]; then
    echo "⚠️  Failed to detect public IP. Defaulting to temporary placeholder."
    MY_IP="211.200.10.5"
fi
echo "📍 Detected Admin Public IP: ${MY_IP}/32 (Used for SSH access)"

# ------------------------------------------------------------------------------
# Step 1: Create VPC
# ------------------------------------------------------------------------------
echo "1️⃣  Creating VPC (${VPC_CIDR})..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block "$VPC_CIDR" \
    --region "$REGION" \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=web-service-vpc},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'Vpc.VpcId' --output text)

echo "   ✓ VPC Created: ${VPC_ID}"

# Enable DNS Hostnames and DNS Resolution
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames "{\"Value\":true}" --region "$REGION"
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support "{\"Value\":true}" --region "$REGION"

# ------------------------------------------------------------------------------
# Step 2: Create Public Subnet
# ------------------------------------------------------------------------------
echo "2️⃣  Creating Public Subnet (${SUBNET_CIDR} in ${AVAILABILITY_ZONE})..."
SUBNET_ID=$(aws ec2 create-subnet \
    --vpc-id "$VPC_ID" \
    --cidr-block "$SUBNET_CIDR" \
    --availability-zone "$AVAILABILITY_ZONE" \
    --region "$REGION" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=web-service-public-subnet},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'Subnet.SubnetId' --output text)

echo "   ✓ Subnet Created: ${SUBNET_ID}"

# Enable Auto-assign Public IP on launch
aws ec2 modify-subnet-attribute \
    --subnet-id "$SUBNET_ID" \
    --map-public-ip-on-launch \
    --region "$REGION"

# ------------------------------------------------------------------------------
# Step 3: Create and Attach Internet Gateway (IGW)
# ------------------------------------------------------------------------------
echo "3️⃣  Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
    --region "$REGION" \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=web-service-igw},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'InternetGateway.InternetGatewayId' --output text)

echo "   ✓ IGW Created: ${IGW_ID}"
echo "   → Attaching IGW to VPC..."
aws ec2 attach-internet-gateway \
    --vpc-id "$VPC_ID" \
    --internet-gateway-id "$IGW_ID" \
    --region "$REGION"

# ------------------------------------------------------------------------------
# Step 4: Create Route Table & Add Default Route to IGW
# ------------------------------------------------------------------------------
echo "4️⃣  Configuring Public Route Table..."
ROUTE_TABLE_ID=$(aws ec2 create-route-table \
    --vpc-id "$VPC_ID" \
    --region "$REGION" \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=web-service-public-rtb},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'RouteTable.RouteTableId' --output text)

echo "   ✓ Route Table Created: ${ROUTE_TABLE_ID}"

# Add 0.0.0.0/0 -> IGW route
aws ec2 create-route \
    --route-table-id "$ROUTE_TABLE_ID" \
    --destination-cidr-block "0.0.0.0/0" \
    --gateway-id "$IGW_ID" \
    --region "$REGION" > /dev/null

# Associate Route Table with Public Subnet
aws ec2 associate-route-table \
    --subnet-id "$SUBNET_ID" \
    --route-table-id "$ROUTE_TABLE_ID" \
    --region "$REGION" > /dev/null
echo "   ✓ Route 0.0.0.0/0 -> ${IGW_ID} attached and associated with subnet"

# ------------------------------------------------------------------------------
# Step 5: Create Security Group (Least Privilege Rules)
# ------------------------------------------------------------------------------
echo "5️⃣  Creating Security Group (Least-Privilege Inbound)..."
SG_ID=$(aws ec2 create-security-group \
    --group-name "web-service-sg" \
    --description "Allow inbound HTTP 80 from anywhere and SSH 22 only from my IP" \
    --vpc-id "$VPC_ID" \
    --region "$REGION" \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=web-service-sg},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'GroupId' --output text)

echo "   ✓ Security Group Created: ${SG_ID}"

# Rule A: Inbound HTTP 80 from 0.0.0.0/0 (Public Web Traffic)
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" > /dev/null
echo "   ✓ Inbound Rule: HTTP Port 80 allowed from 0.0.0.0/0"

# Rule B: Inbound SSH 22 strictly from operator IP
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr "${MY_IP}/32" \
    --region "$REGION" > /dev/null
echo "   ✓ Inbound Rule: SSH Port 22 allowed ONLY from ${MY_IP}/32"

# ------------------------------------------------------------------------------
# Step 6: Query Latest Ubuntu 22.04 LTS AMI
# ------------------------------------------------------------------------------
echo "6️⃣  Retrieving Ubuntu 22.04 LTS AMI ID..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" \
    --query "reverse(sort_by(Images, &CreationDate))[0].ImageId" \
    --output text \
    --region "$REGION")
echo "   ✓ Using AMI: ${AMI_ID}"

# ------------------------------------------------------------------------------
# Step 7: Launch EC2 Instance with User Data
# ------------------------------------------------------------------------------
echo "7️⃣  Launching EC2 Instance (${INSTANCE_TYPE})..."
USER_DATA_FILE="$(dirname "$0")/../configs/user-data.sh"

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --subnet-id "$SUBNET_ID" \
    --security-group-ids "$SG_ID" \
    --associate-public-ip-address \
    --user-data "file://${USER_DATA_FILE}" \
    --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":8,\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=web-server-prod},{Key=Project,Value=${PROJECT_TAG}}]" \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region "$REGION")

echo "   ✓ Instance Launched: ${INSTANCE_ID}"
echo "⏳ Waiting for instance to enter 'running' state..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "========================================================================"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "========================================================================"
echo "VPC ID:           ${VPC_ID}"
echo "Subnet ID:        ${SUBNET_ID}"
echo "IGW ID:           ${IGW_ID}"
echo "Route Table ID:   ${ROUTE_TABLE_ID}"
echo "Security Group:   ${SG_ID}"
echo "Instance ID:      ${INSTANCE_ID}"
echo "Public IPv4:      ${PUBLIC_IP}"
echo ""
echo "🌐 Verify in your browser: http://${PUBLIC_IP}"
echo "🩺 Verify health endpoint: curl -i http://${PUBLIC_IP}/health"
echo "========================================================================"
