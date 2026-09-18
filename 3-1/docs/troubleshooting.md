# 인프라 구축 트러블슈팅 보고서

## [사례 1] 외부 브라우저 접속 시 연결 시간 초과(Connection Timed Out) 발생

### 1. 증상 (Problem Statement)
- EC2 인스턴스에 퍼블릭 IP가 정상 할당되었고, SSH 접속 후 내부에서 `curl http://localhost` 실행 시 200 OK 응답을 확인했으나, 로컬 PC 브라우저에서 `http://<EC2_퍼블릭IP>` 접속 시 응답이 없으며 브라우저에 `ERR_CONNECTION_TIMED_OUT` 에러 발생.

### 2. 원인 가설 (Hypotheses)
1. **가설 A**: 인스턴스에 적용된 보안 그룹(Security Group)에 HTTP(80) 포트 인바운드 규칙이 누락되었거나 IP 제한이 걸려 있다.
2. **가설 B**: 퍼블릭 서브넷 라우팅 테이블(Route Table)에 Internet Gateway(`0.0.0.0/0 -> igw-xxx`) 경로가 정의되어 있지 않아 외부 패킷 수신/반환 경로가 단절되었다.
3. **가설 C**: Ubuntu OS 내부의 UFW 방화벽이 활성화되어 80 포트를 차단하고 있다.

### 3. 검증 방법 (Verification)
1. **가설 C 검증**: 인스턴스 터미널에서 `sudo ufw status` 실행
   - 결과: `Status: inactive` 확인. (OS 방화벽 원인 배제)
2. **가설 A 검증**: AWS 콘솔 > EC2 > 보안 그룹(`web-sg`) 인바운드 규칙 확인
   - 결과: `TCP 80 0.0.0.0/0` 규칙이 정상 등록되어 있음. (보안 그룹 원인 배제)
3. **가설 B 검증**: AWS 콘솔 > VPC > 서브넷 > `public-subnet-2a`와 연결된 라우팅 테이블 규칙 확인
   - 결과: `10.0.0.0/16 -> local` 경로만 존재하며, `0.0.0.0/0` 대상 IGW 경로가 누락되어 있음을 확인.

### 4. 조치 내용 (Action Taken)
1. VPC 콘솔 > 라우팅 테이블(`mission-public-rt`) 선택.
2. [라우팅 편집(Edit routes)] 진입.
3. [경로 추가(Add route)] 클릭 후 대상 지정:
   - 대상(Destination): `0.0.0.0/0`
   - 타겟(Target): Internet Gateway(`mission-igw`) 선택.
4. [변경 사항 저장(Save changes)] 완료.

### 5. 결과 (Resolution)
- 로컬 PC 브라우저 및 외부 터미널에서 `curl -I http://<EC2_퍼블릭IP>/health` 호출 시 즉각적으로 `HTTP/1.1 200 OK` 응답 반환 확인.

### 6. 재발 방지 대책 (Post-mortem & Prevention)
- **체크리스트 표준화**: 서브넷을 "Public"으로 지정할 경우 다음 3가지 요건을 필수 확인 항목으로 문서화.
  1. 서브넷 설정의 '퍼블릭 IPv4 주소 자동 할당' 활성화
  2. 서브넷 라우팅 테이블에 `0.0.0.0/0 -> IGW` 바인딩 확인
  3. 인터넷 게이트웨이의 VPC Attach 상태 확인
  