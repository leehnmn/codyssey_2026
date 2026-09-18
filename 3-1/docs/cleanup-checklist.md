# AWS 실습 리소스 정리 및 과금 방지 체크리스트

실습 종료 후 과금 발생 방지를 위해 의존성 역순으로 리소스를 정리하고 점검을 완료하였습니다.

- **실습 리전**: `ap-northeast-2` (서울 리전)
- **정리 일시**: 2026-09-18
- **작업자**: IAM 실습 사용자

---

## 1. 리소스 정리 점검 목록

| 대상 리소스 | 확인 항목 | 정리 상태 | 확인 일시 |
| :--- | :--- | :---: | :---: |
| **EC2 Instance** | 인스턴스 상태가 `Terminated`(종료)로 전환되었는가? | [x] 완료 | 2026-09-18 |
| **EBS Volume** | 인스턴스 종료 후 루트 볼륨 자동 삭제 및 잔존 미사용 볼륨(`available`)이 없는가? | [x] 완료 | 2026-09-18 |
| **Elastic IP (EIP)** | 할당받은 탄력적 IP가 있을 시 `Release Elastic IP`(릴리스) 처리되었는가? (미연결 시 시간당 과금) | [x] 완료 (미사용) | 2026-09-18 |
| **Security Group** | 생성한 실습용 보안 그룹(`web-sg`)이 삭제되었는가? | [x] 완료 | 2026-09-18 |
| **Route Table** | 기본 라우팅 테이블 외 커스텀 생성한 `mission-public-rt`가 삭제되었는가? | [x] 완료 | 2026-09-18 |
| **Internet Gateway** | VPC에서 `Detach from VPC` 후 `Delete internet gateway` 처리되었는가? | [x] 완료 | 2026-09-18 |
| **Subnet** | 생성한 `mission-public-subnet-2a`가 삭제되었는가? | [x] 완료 | 2026-09-18 |
| **VPC** | 생성한 커스텀 VPC `mission-vpc`가 완전히 삭제되었는가? | [x] 완료 | 2026-09-18 |
| **기타 부가 리소스** | NAT Gateway, ALB, RDS 등 유료 서비스가 생성되지 않았음을 확인했는가? | [x] 완료 | 2026-09-18 |

---

## 2. 과금 방지 2차 검증

- [x] AWS Billing & Cost Management 대시보드 진입 확인
- [x] Seoul(`ap-northeast-2`) 리전 EC2 대시보드의 **Volumes**, **Instances(Running)** 숫자가 `0`인지 재확인