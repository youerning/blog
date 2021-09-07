mkdir -p app
rm -fr app/*
cp ../backend/* app/
cp ../frontend/app/unpackage/dist/build/h5/index.html app/
cp -ar ../frontend/app/unpackage/dist/build/h5/static app
sed -i "s/127.0.0.1/db/" app/app.yaml

docker build -t video .