# 部署文档
1. 构建镜像
```bash
mkdir -p app
cp ../backend/* app/
cp ../frontend/app/unpackage/dist/build/h5/index.html app/
cp ../frontend/app/unpackage/dist/build/h5/static app
sed -i "s/127.0.0.1/db/" app/app.yaml

docker build -t video .
```

2. 启动容器
docker-compose up