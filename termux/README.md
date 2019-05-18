# termux软件安装-持续更新
termux安装包安装填坑指南

### 必要更新

```
apt update
apt upgrade
```

### 大多数安装包的依赖库

```
apt install python python-dev clang fftw libzmq libzmq-dev freetype freetype-dev libpng libpng-dev pkg-config zlib zlib-dev libiconv libiconv-dev curl
```

### 补充软件仓库

```
$ curl -L https://its-pointless.github.io/setup-pointless-repo.sh | sh
```


### 科学计算三剑客

```
pip install numpy pandas matplotlib
```

### 基础机器学习
```
pkg install scipy 
pip install scikit-learn
```

### 安装dlib 人脸识别

```
LDFLAGS=" -llog -lpython3" python3 setup.py install --set 'DCMAKE_INSTALL_PREFIX=$PREFIX'
```


### debug命令

```
pkg-config --cflags freetype2
```

## TODO
- tensorflow
- keras



