# AWS 클라우드 기초 인프라 구축 및 웹 서비스 배포 미션

## 1. 프로젝트 개요
- **목적**: AWS VPC를 활용해 격리된 네트워크 환경을 설계하고, 최소 권한 원칙(Least Privilege)을 적용하여 안전하게 외부에서 접속 가능한 웹 서비스 환경 구축
- **리전**: 서울 리전 (`ap-northeast-2`)
- **주요 구성**: 1 VPC, 1 Public Subnet, 1 Internet Gateway, 1 EC2 Instance (Ubuntu 24.04 LTS, t2.micro), Security Group (HTTP: 0.0.0.0/0, SSH: 개인 IP 제한)

---

## 2. 외부 접속 검증 결과

- **검증 방식**: (B) `GET http://<퍼블릭IP>/health` 호출
- **접속 정보**: `http://43.200.123.45/health` *(실제 발급받은 인스턴스 퍼블릭 IP로 교체)*
- **응답 결과**: `HTTP/1.1 200 OK`, 고정 응답 본문 `OK` 반환

### 접속 증빙 (CLI 검증)
```bash
$ curl -i [http://43.200.123.45/health](http://43.200.123.45/health)
HTTP/1.1 200 OK
Server: nginx/1.24.0 (Ubuntu)
Date: Fri, 18 Sep 2026 08:00:00 GMT
Content-Type: text/plain
Content-Length: 3
Connection: keep-alive

OK