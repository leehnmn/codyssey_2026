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
ls -al //ls = 목록확인 -la = all  la 도 가능 a = all  //파일도 옵션이 들어가야

mkdir docker-project // mkdir = 폴더생성 , 파일이름  
cd docker-project // cd = 폴더로 이동 
touch test.txt // touch = 파일 생성  
cp test.txt new.txt // cp = 카피, cp 원본파일 카피파일이름   //파일도 옵션이 들어가야 -r 
mv new.txt copy.txt // mv = 이동,이름바꾸기  
rm copy.txt // rm = 삭제  
cat test.txt // 내용출력  
## 5. docker 기본실습 
Bash  
docker --version  
docker info  
이미지 생성후 진입  
Bash  
docker run hello-world // 이미지 생성  
docker run -it ubuntu bash // 컨테이너 생성 실행 // bash로 진입  
exit  
docker ps //실행중 없음  
docker start // 현재위치에서 실행  
컨테이너 종료시: attach 기존 실헬 프로세스에는 불가하다. 기존 bash 연결 //  
exec 컨테이너 안에서 "새프로세스를 시작한다. 새 bash 연결 
## 기존 Dockerfile 기반 커스텀 이미지 제작 
이미지 빌드 제작  
docker build -t my-web . // . 현재경로 위치 , -t 이름 태그  
컨테이너 실행  
docker run -d -p 8080:80 my-web // -d 백그라운드 -p 포트연결  
nginx 기반 커스텀 웹서버 이미지 제작  
docker start (name cmd v)  
docker volume create my-volme 볼륨 생성  
docker run -it -v my-volume:/data ubuntu bash 볼륨 시작  
echo "hello volume" > /data/test.txt 볼륨 안에 파일 생성  
컨테이너 삭제 후 볼륨 살아있는지 확인  
exit  
docker stop (컨테이너 id)  
docker rm (컨테이너 id)  
docker run -it -v my-volume:/data ubuntu bash  
cat /data/test.txt  
## 이미지와 컨테이너 차이
이미지 = 컨테이너 내부의 실행파일  
컨테이너 이미지를 구성하는 전체적인 환경  
## 포트 및 볼륨설정 재현가능
동일 환경에서 누구나 동일 결과값을 얻을 수있도록 포트 매핑과 볼륨설정을 명령어 기반으로 재현하였다.  
bash ..8080 호스트 80 내부포트  
## 컨테이너 내부 포트로 직접접속못하는 이유
컨테이너는 호스틀와 분리되어 격리된 네트워크 환경에서만 실행 가능  
보안 때문에 외부에서 자율적으로 접근한다면 공격과 무단 접근 가능성이 높아진다.  
## 절대경로 상대경로 차이 
절대경로 루트 / 처음 부터 시작  
상대경로 현재위치 기준으로 이동하는 경로  
## 권한 설정 변경 
ls -al 
권한 확인후 
chmod 755 파일명
ls -al 후 변경 확인