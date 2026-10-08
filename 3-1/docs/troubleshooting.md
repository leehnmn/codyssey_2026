# 🛠️ AWS 인프라 구축 트러블슈팅 보고서 (Troubleshooting Report)

본 문서는 AWS 클라우드 웹 서비스 인프라(VPC, Subnet, Route Table, Internet Gateway, Security Group, EC2, Nginx) 구축 과정에서 발생할 수 있는 실제 장애 시나리오들을 재현하고, **[증상 → 가설 → 검증 → 조치 → 결과 → 재발 방지]** 단계적 문제 해결 프로세스에 따라 분석 및 해결한 보고서입니다.

---

## 📑 목차
1. [Case 1: 웹 브라우저 접속 불가 (Connection Timed Out) - 보안 그룹 인바운드 누락](#case-1-웹-브라우저-접속-불가-connection-timed-out---보안-그룹-인바운드-누락)
2. [Case 2: EC2 인스턴스 외부 인터넷 통신 불가 (Outbound Hang) - Route Table IGW 누락](#case-2-ec2-인스턴스-외부-인터넷-통신-불가-outbound-hang---route-table-igw-누락)
3. [Case 3: 헬스체크 호출 시 404 Not Found 발생 - Nginx Location 설정 오류](#case-3-헬스체크-호출-시-404-not-found-발생---nginx-location-설정-오류)
4. [Case 4: 개발자 환경 IP 변경으로 인한 SSH 접속 실패 및 디버깅](#case-4-개발자-환경-ip-변경으로-인한-ssh-접속-실패-및-디버깅)

---

## Case 1: 웹 브라우저 접속 불가 (Connection Timed Out) - 보안 그룹 인바운드 누락

### 1. 증상 (Symptom)
- EC2 인스턴스는 콘솔에서 `2/2 checks passed` 및 `Running` 상태로 정상 표시됨.
- 퍼블릭 IP(`13.125.45.89`)가 정상 할당되었으나, 로컬 브라우저에서 `http://13.125.45.89`로 접속 시 무한 로딩 후 아래 에러 출력:
  ```text
  This site can’t be reached
  13.125.45.89 took too long to respond.
  ERR_CONNECTION_TIMED_OUT
  ```
- 로컬 터미널에서 `curl -v http://13.125.45.89` 실행 시 TCP SYN 패킷 전송 후 응답 없이 30초 후 Timeout 발생:
  ```bash
  $ curl -v --connect-timeout 10 http://13.125.45.89
  *   Trying 13.125.45.89:80...
  * Connection timed out after 10001 milliseconds
  * Closing connection 0
  ```

---

### 2. 원인 가설 수립 (Hypothesis)
네트워크 연결에서 `Connection Refused`가 아닌 **`Connection Timed Out`**이 발생한다는 것은, 패킷이 목적지 OS의 소켓(Nginx)에 도달하기 전 중간 네트워크 레이어(방화벽/라우팅)에서 패킷이 드롭(Drop/Silent Discard)되고 있음을 시사함.

- **가설 1 (Security Group)**: EC2 인스턴스에 할당된 Security Group의 인바운드 규칙에 HTTP(80) 포트가 허용되어 있지 않다.
- **가설 2 (VPC Routing)**: Public Subnet의 라우팅 테이블에 `0.0.0.0/0 -> Internet Gateway` 경로가 누락되었다.
- **가설 3 (OS Firewall)**: EC2 내부 Ubuntu UFW(방화벽) 또는 iptables가 80번 포트를 차단하고 있다.

---

### 3. 검증 (Verification)
1. **인스턴스 내부 웹 서버 상태 확인 (SSH 접속):**
   ```bash
   ubuntu@ip-10-0-1-50:~$ sudo systemctl status nginx
   ● nginx.service - A high performance web server and a reverse proxy server
        Active: active (running) since Fri 2026-10-02 00:25:10 UTC; 15min ago
   
   ubuntu@ip-10-0-1-50:~$ curl -i http://localhost
   HTTP/1.1 200 OK
   Server: nginx/1.18.0 (Ubuntu)
   ...
   ```
   👉 인스턴스 내부에서는 Nginx가 80번 포트에서 정상 수신 대기(Listen) 중이며 로컬 요청에 200 OK 응답함. (OS 내부 문제 배제)

2. **AWS CLI를 통한 Security Group 인바운드 규칙 확인:**
   ```bash
   aws ec2 describe-security-groups --group-ids sg-0abc12345678 \
       --query 'SecurityGroups[0].IpPermissions' --output json
   ```
   **출력 결과:**
   ```json
   [
     {
       "FromPort": 22,
       "IpProtocol": "tcp",
       "IpRanges": [{"CidrIp": "211.200.10.5/32"}],
       "ToPort": 22
     }
   ]
   ```
   👉 **원인 확정:** 보안 그룹에 관리자 IP의 SSH(22)만 허용되어 있고, 웹 접속용 **HTTP(80) 포트 허용 규칙이 완전히 누락**되어 있음.

---

### 4. 조치 내용 (Action)
보안 그룹에 0.0.0.0/0(모든 사용자)으로부터의 TCP 80 포트 인바운드를 허용하도록 규칙을 추가함.

```bash
# AWS CLI를 통한 보안 그룹 인바운드 HTTP(80) 규칙 추가
aws ec2 authorize-security-group-ingress \
    --group-id sg-0abc12345678 \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region ap-northeast-2
```

---

### 5. 결과 (Result)
규칙 추가 즉시 로컬 브라우저 및 터미널에서 정상 접속 확인:
```bash
$ curl -i http://13.125.45.89/
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Content-Type: text/html
Content-Length: 2654
Connection: keep-alive

<!DOCTYPE html>
<html>
...
```
- 브라우저에 배포된 HTML 웹 페이지가 즉시 렌더링됨.

---

### 6. 재발 방지 (Prevention)
- **보안 그룹 템플릿화 / IaC 적용**: 콘솔 수동 생성 시 포트 누락 실수가 잦으므로, `deploy.sh` 스크립트 또는 CloudFormation/Terraform 코드로 포트 80과 22가 항상 표준 규격으로 생성되도록 자동화함.
- **사전 배포 체크리스트(Pre-Flight Checklist)** 항목에 `curl -v http://<IP>` 검증 단계를 필수 항목으로 지정.

---
---

## Case 2: EC2 인스턴스 외부 인터넷 통신 불가 (Outbound Hang) - Route Table IGW 누락

### 1. 증상 (Symptom)
- EC2 인스턴스 배포 시 User Data 스크립트에서 `apt-get update`가 무한 대기(Hang)하거나 실패하여 Nginx 설치가 완료되지 않음.
- 인스턴스 내부에서 외부 웹사이트로 curl 요청 시 응답이 오지 않고 타임아웃 발생:
  ```bash
  ubuntu@ip-10-0-1-50:~$ curl -I --connect-timeout 5 https://example.com
  curl: (28) Failed to connect to example.com port 443 after 5001 ms: Connection timed out
  ```

---

### 2. 원인 가설 수립 (Hypothesis)
- **가설 1**: Security Group 아웃바운드 규칙이 차단되어 있다.
- **가설 2**: 서브넷에 연결된 Route Table에 기본 게이트웨이(`0.0.0.0/0 -> Internet Gateway`) 경로가 없거나 잘못 연결되어 서브넷이 Public 상태가 아니다.
- **가설 3**: Internet Gateway(IGW)가 VPC에 Attach(연결)되지 않았다.

---

### 3. 검증 (Verification)
1. **Security Group 아웃바운드 확인:**
   ```bash
   aws ec2 describe-security-groups --group-ids sg-0abc12345678 \
       --query 'SecurityGroups[0].IpPermissionsEgress'
   ```
   👉 `0.0.0.0/0` All Traffic 허용 확인 (정상).

2. **Route Table 확인:**
   ```bash
   aws ec2 describe-route-tables \
       --filters "Name=association.subnet-id,Values=subnet-01234567" \
       --query 'RouteTables[0].Routes' --output json
   ```
   **출력 결과:**
   ```json
   [
     {
       "DestinationCidrBlock": "10.0.0.0/16",
       "GatewayId": "local",
       "State": "active"
     }
   ]
   ```
   👉 **원인 확정:** 서브넷의 라우팅 테이블에 VPC 내부 로컬 통신(`10.0.0.0/16`)만 존재하고, **인터넷 아웃바운드 경로인 `0.0.0.0/0 -> igw-xxxx`가 누락**되어 있음.

---

### 4. 조치 내용 (Action)
1. VPC에 Internet Gateway가 연결되어 있는지 확인:
   ```bash
   aws ec2 attach-internet-gateway --vpc-id vpc-01234567 --internet-gateway-id igw-01234567
   ```
2. Route Table에 `0.0.0.0/0 -> igw-01234567` 경로 추가:
   ```bash
   aws ec2 create-route \
       --route-table-id rtb-01234567 \
       --destination-cidr-block 0.0.0.0/0 \
       --gateway-id igw-01234567
   ```

---

### 5. 결과 (Result)
경로 추가 즉시 인스턴스 내부에서 외부 인터넷 통신 정상화:
```bash
ubuntu@ip-10-0-1-50:~$ curl -I https://example.com
HTTP/2 200
content-type: text/html; charset=UTF-8
...
```
- `sudo apt update && sudo apt install -y nginx` 명령어가 즉시 정상 동작함.

---

### 6. 재발 방지 (Prevention)
- **VPC 서브넷 명명 규칙 및 아키텍처 원칙 준수**: 서브넷을 "Public Subnet"으로 분류할 때는 반드시 **(1) IGW가 VPC에 연결되어 있는가**, **(2) 해당 서브넷의 라우팅 테이블에 0.0.0.0/0 -> IGW 경로가 선언되어 있는가**를 동시에 세트로 구성하는 스크립트를 표준화함.

---
---

## Case 3: 헬스체크 호출 시 404 Not Found 발생 - Nginx Location 설정 오류

### 1. 증상 (Symptom)
- 루트 경로 `http://13.125.45.89/`는 정상 200 OK로 인덱스 페이지를 반환함.
- 그러나 요구사항인 헬스체크 엔드포인트 `http://13.125.45.89/health` 호출 시 404 Not Found 반환:
  ```bash
  $ curl -i http://13.125.45.89/health
  HTTP/1.1 404 Not Found
  Server: nginx/1.18.0 (Ubuntu)
  Content-Type: text/html
  Content-Length: 162
  <html>
  <head><title>404 Not Found</title></head>
  ...
  ```

---

### 2. 원인 가설 수립 (Hypothesis)
- **가설**: Nginx 설정 파일(`/etc/nginx/sites-available/default`)에 `/health` URI에 대한 location 블록이 정의되어 있지 않아, Nginx가 `/var/www/html/health`라는 실제 디렉터리나 파일을 찾으려 시도하다가 404를 반환하고 있다.

---

### 3. 검증 (Verification)
1. **Nginx 에러 로그 확인:**
   ```bash
   ubuntu@ip-10-0-1-50:~$ sudo tail -n 5 /var/log/nginx/error.log
   2026/10/02 00:28:14 [error] 1422#1422: *1 "/var/www/html/health" is not found (2: No such file or directory), client: 211.200.10.5, server: _, request: "GET /health HTTP/1.1", host: "13.125.45.89"
   ```
   👉 에러 로그에서 파일 부재로 인한 404 발생이 명확히 확인됨.

---

### 4. 조치 내용 (Action)
`/etc/nginx/sites-available/default` 파일에 파일 탐색 없이 바로 200 OK와 JSON 응답을 반환하는 location 블록을 추가함.

```nginx
# /etc/nginx/sites-available/default 수정
location = /health {
    default_type application/json;
    return 200 '{"status":"UP","statusCode":200,"service":"nginx-cloud-web","message":"Healthy"}\n';
}
```

문법 검사 및 서비스 리로드:
```bash
ubuntu@ip-10-0-1-50:~$ sudo nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

ubuntu@ip-10-0-1-50:~$ sudo systemctl reload nginx
```

---

### 5. 결과 (Result)
```bash
$ curl -i http://13.125.45.89/health
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Content-Type: application/json
Content-Length: 85
Connection: keep-alive

{"status":"UP","statusCode":200,"service":"nginx-cloud-web","message":"Healthy"}
```
- HTTP 200 응답과 함께 정의된 JSON 헬스체크 본문이 정상 출력됨.

---

### 6. 재발 방지 (Prevention)
- EC2 User Data 스크립트 작성 시 Nginx 설정 템플릿에 `/health` location 블록을 기본 포함하도록 자동화.
- CI/CD 파이프라인의 배포 후 검증(Smoke Test) 단계에 `/`와 `/health` 호출 테스트를 필수로 포함.

---
---

## Case 4: 개발자 환경 IP 변경으로 인한 SSH 접속 실패 및 디버깅

### 1. 증상 (Symptom)
- 전날까지 정상 접속되던 SSH가 카페/재택 환경 이동 후 아래 에러와 함께 차단됨:
  ```bash
  $ ssh -i web-key.pem ubuntu@13.125.45.89
  ssh: connect to host 13.125.45.89 port 22: Operation timed out
  ```

---

### 2. 원인 가설 수립 (Hypothesis)
- 보안 그룹에 SSH 22 포트가 최소권한 원칙에 따라 `특정 IP/32`로 제한되어 있는데, 네트워크 장소 변경으로 인해 개발자의 공인 IP가 변경되었을 것이다.

---

### 3. 검증 (Verification)
1. 현재 개발 단말의 공인 IP 확인:
   ```bash
   $ curl -s https://checkip.amazonaws.com
   118.235.88.19
   ```
2. AWS 콘솔 또는 CLI로 보안 그룹 22번 포트 허용 목록 조회:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-0abc12345678 \
       --query "SecurityGroups[0].IpPermissions[?ToPort==\`22\`].IpRanges"
   ```
   👉 기존 설정: `211.200.10.5/32` -> **현재 IP(`118.235.88.19/32`)와 불일치 확인.**

---

### 4. 조치 내용 (Action)
기존 오래된 IP 규칙을 회수하고, 현재 신규 공인 IP로 인바운드 규칙을 갱신:
```bash
# 구 IP 규칙 삭제
aws ec2 revoke-security-group-ingress \
    --group-id sg-0abc12345678 \
    --protocol tcp --port 22 --cidr 211.200.10.5/32

# 신규 IP 규칙 등록 (최소 권한 유지)
aws ec2 authorize-security-group-ingress \
    --group-id sg-0abc12345678 \
    --protocol tcp --port 22 --cidr 118.235.88.19/32
```

---

### 5. 결과 (Result)
```bash
$ ssh -i web-key.pem ubuntu@13.125.45.89
Welcome to Ubuntu 22.04 LTS (GNU/Linux 5.15.0-1031-aws x86_64)
...
ubuntu@ip-10-0-1-50:~$ 
```
- 즉시 SSH 접속 성공.

---

### 6. 재발 방지 (Prevention)
- **절대 편의를 위해 `0.0.0.0/0`으로 22번 포트를 열지 않는다.** (브루트포스 공격 및 침해사고의 1차 표적)
- 실습 및 개발 중에는 `scripts/update-my-ip.sh`와 같은 단일 갱신 스크립트를 사용하거나, 장기적으로는 AWS Systems Manager (SSM) Session Manager를 도입하여 인바운드 22번 포트를 완전히 닫고 IAM 인증 기반으로 접속하는 방식을 권장함.
