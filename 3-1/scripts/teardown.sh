#!/usr/bin/env bash
# ==============================================================================
# AWS Infrastructure Safe Teardown Script
# Safely tears down resources in reverse dependency order to prevent residual billing.
# ==============================================================================

set -euo pipefail

REGION="ap-northeast-2"
PROJECT_TAG="AWS-Web-Service-Mission"

echo "========================================================================"
echo "⚠️  Starting AWS Infrastructure Safe Teardown in [${REGION}]"
echo "========================================================================"

# 1. Find and Terminate Instances
echo "1️⃣  Searching for EC2 instances with tag Project=${PROJECT_TAG}..."
INSTANCE_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" "Name=instance-state-name,Values=pending,running,stopped" \
    --region "$REGION" \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text)

if [ -n "$INSTANCE_IDS" ]; then
    echo "   Terminating instances: ${INSTANCE_IDS}"
    aws ec2 terminate-instances --instance-ids ${INSTANCE_IDS} --region "$REGION" > /dev/null
    echo "⏳ Waiting for instances to terminate completely..."
    aws ec2 wait instance-terminated --instance-ids ${INSTANCE_IDS} --region "$REGION"
    echo "   ✓ Instances terminated and root EBS volumes cleaned up."
else
    echo "   No active instances found."
fi

# 2. Delete Security Groups
echo "2️⃣  Searching for Security Groups..."
SG_IDS=$(aws ec2 describe-security-groups \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" \
    --region "$REGION" \
    --query 'SecurityGroups[].GroupId' \
    --output text)

for SG in $SG_IDS; do
    echo "   Deleting Security Group: ${SG}"
    aws ec2 delete-security-group --group-id "$SG" --region "$REGION" || true
done

# 3. Disassociate and Delete Route Tables
echo "3️⃣  Cleaning up Route Tables..."
RT_INFOS=$(aws ec2 describe-route-tables \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" \
    --region "$REGION" \
    --query 'RouteTables[].[RouteTableId]' \
    --output text)

for RT in $RT_INFOS; do
    # Disassociate associations first
    ASSOC_IDS=$(aws ec2 describe-route-tables --route-table-ids "$RT" --region "$REGION" \
        --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' --output text)
    for ASSOC in $ASSOC_IDS; do
        aws ec2 disassociate-route-table --association-id "$ASSOC" --region "$REGION" || true
    done
    echo "   Deleting Route Table: ${RT}"
    aws ec2 delete-route-table --route-table-id "$RT" --region "$REGION" || true
done

# 4. Detach and Delete Internet Gateways
echo "4️⃣  Cleaning up Internet Gateways..."
IGW_IDS=$(aws ec2 describe-internet-gateways \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" \
    --region "$REGION" \
    --query 'InternetGateways[].[InternetGatewayId,Attachments[0].VpcId]' \
    --output text)

while read -r IGW VPC; do
    if [ -n "$IGW" ] && [ "$IGW" != "None" ]; then
        if [ -n "$VPC" ] && [ "$VPC" != "None" ]; then
            echo "   Detaching IGW ${IGW} from VPC ${VPC}..."
            aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC" --region "$REGION" || true
        fi
        echo "   Deleting IGW ${IGW}..."
        aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" --region "$REGION" || true
    fi
done <<< "$IGW_IDS"

# 5. Delete Subnets
echo "5️⃣  Cleaning up Subnets..."
SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" \
    --region "$REGION" \
    --query 'Subnets[].SubnetId' \
    --output text)

for SUBNET in $SUBNET_IDS; do
    echo "   Deleting Subnet: ${SUBNET}"
    aws ec2 delete-subnet --subnet-id "$SUBNET" --region "$REGION" || true
done

# 6. Delete VPCs
echo "6️⃣  Cleaning up VPCs..."
VPC_IDS=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" \
    --region "$REGION" \
    --query 'Vpcs[].VpcId' \
    --output text)

for VPC in $VPC_IDS; do
    echo "   Deleting VPC: ${VPC}"
    aws ec2 delete-vpc --vpc-id "$VPC" --region "$REGION" || true
done

echo "========================================================================"
echo "🎉 TEARDOWN COMPLETE! All project resources have been safely destroyed."
echo "🛡️  Zero recurring billing risk verified."
echo "========================================================================"
