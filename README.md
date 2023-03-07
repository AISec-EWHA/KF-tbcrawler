# KF-tbcrawler

# **🗒️**Instroduction

KF-tbcrawler의 디렉토리 구조는 다음과 같습니다:

```
tor-browser-crawler-master
├── 📁bin
│   └── tbcrawler.py
├── 📁tbcrawler
│   ├── __init__.py
│   ├── common.py
│   ├── crawler.py #screenshot chapture
│   ├── dumputils.py
│   ├── log.py
│   ├── pytbcrawler.py
│   ├── torcontroller.py #Tor network interface
│   └── style.css
├── Dockerfile #docker container 내부에서 crawler 실행 관리
├── Entrypoint.sh #Docker container의 실행 관리
├── Makefile #build와 run 설정
├── config.ini #batches와 visits 수 설정
├── requirements.txt #프로젝트 내에 import 할 라이브러리 관리
├── setup.py
└── sites.txt #Keywordlist
```

# **⚙️**Settings

KeywordFingerprinting 프로젝트를 사용하기 위해 다음과 같은 Docker 설정이 필요합니다:

### **Docker Ubuntu Linux installation**

```bash
sudo apt-get update
sudo apt-get install docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

### Give permission to “/var/run/docker.sock”

```bash
sudo chmod -R 777 /var/run/docker.sock
```

### Give permission to “home/docker/tbcrawl/Entrypoint.sh”

```bash
sudo chmod +x Entrypoint.sh
```
