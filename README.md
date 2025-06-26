# gauction
The Team Auction Page
본 소스코드는 초기 소스입니다. 실서비스는 다른점 유의 부탁드립니다. V1.0.3 - Beta
실서비스 가이드라인은 https://gauction-doc.netlify.app/ 에서 보실수있습니다.
# What is it?
단순한 경매페이지의 프론트엔드 / 백엔드 코드입니다. 백엔드는 파이썬으로 작성되었습니다.

# How to run This code?
#### 0. 선행조건
코드를 실행하기위해서 다음이 설치되어있어야합니다.

```
Python, Python-flask, Nginx, Gunicorn
```

> 다음조건에서 실행해야합니다.
```
Ubuntu 20.04 이상
```
#### 1. 다음코드로 본 리포지토리를 로컬로 가져옵니다.

```Bash
git clone https://github.com/heon0120/gauction.git

```

#### 2. 필수 라이브러리를 설치합니다.

```Bash
sudo apt-get update
sudo apt-get install python python-pip nginx gunicorn
pip install flask 
```

#### 3. ShellScript파일에 실행권한을 부여합니다.

```Bash
sudo chmod 755 app_run_single
```
#### 4. 다음명령어로 실행합니다.

```Bash
./app_run_single
```

##### 4-1. 실행옵션은 다음과 같습니다.


```
Usage: ./app_run_single [options]
Options:
  -b, --background    Run the server in the background
  -kill, --kill       Kill the background server if running
  -s, --silent        Run the server in foreground without debug/access logs (only info+)
  -status, --status   Check if the server is running
  -h, --help          Show this help message

```

> status는 포그라운드가 아닌 백그라운드 프로세스만 보여줍니다.
>
> 또한, gunicorn의 worker가 2이상이면 세션유지안되는게 있어서 단일 worker로 해야합니다. ~~원래는 세션을 로컬이나 redis로 처리하는 방법으로 할려했는데 급귀차니즘이 발동해서..ㅎ~~
