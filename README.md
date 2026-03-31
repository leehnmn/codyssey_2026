# codyssey_2026
## 1. 프로젝트 개요
이 프로젝트는 Docker, 터미널, Git을 활용하여 개발환경을 구축합니다.
- 로컬 환경에서 실행된 코드가 다른환경에서도 동일하게 동작하도록 구성
- Docker 기반 웹 서버 실행 및 검증
## 2. 실행환경 
| 항목 | 내용 |
|-----|-----|
| OS | macOS(OrbStack) |
| Shell | zsh | 
| Docker | 28.5.2 |
| Git| 2.53.0 |
Bash
docker --version
git --version
## 3. 수행항목 체크 리스트
- 터미널 명령어 싷습
- Docker 설치 및 점검
- 컨테이너 실행 및 관리 
- Dockerfile 기반 이미지 생성
- 웹 서버 컨테이너 실행
- 포트 매핑 검증
- 바인드 마운트 실습
- Docker 볼륨 실습
- Git/GitHub 연동
## 4. 터미널 조작 로그
bash
pwd //현위치
ls -al //ls = 목록확인 -al = all
mkdir docker-project // mkdir = 폴더생성 , 파일이름
cd docker-project // cd = 폴더로 이동
touch test.txt // touch = 파일 생성
cp test.txt new.txt // cp = 카피, cp 원본파일 카피파일이름
mv new.txt copy.txt // mv = 이동,이름바꾸기 
rm copy.txt // rm = 삭제
cat test.txt // 내용출력ddd
    



