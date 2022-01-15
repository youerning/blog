# Kubernetes源码阅读

保姆级别的源码阅读，死扣各个细节和代码。



代码版本:  release-1.22(b68064208b29e5956cdff79a94831b52dc50d89a)



本系列主要围绕k8s的各个部分的源码来阅读。适合深入k8s内部原理的童鞋阅读，暂时没有介绍基础概念及使用的打算。

整个kubenetes源代码的组件阅读顺序，由以下任务主线作为线索进行逐个击破。

**创建一个deployment到底发生了什么事？**



那么涉及的顺序如下

1. kubectl 
2. kube-apiserver
3. kube-scheduler
4. kube-controller-manager
5. kubelet
6. kube-proxy

之所以是上面的这个顺序，那是因为在创建一个deployment的时候涉及的组件顺序大致如下(当然了，不可能完全单向的数据流，这里的数据流是为了简化)。

首先有一个deployment.yaml文件  -> 使用kubectl apply -f deployment.yaml创建该资源  -> kubectl会把文件处理之后发给api-server ->

api-server会把数据存在etcd  -> kube-scheduler监控到了这个事件所以选择一个节点，然后发出一个事件  -> kube-controller-manager也监控到了这个事件 -> 最后kubelet收到事件就创建对应的容器 -> kube-proxy会设置对应的网络环境



这里的deployment.yaml如下, 之后的deployment对象都是来自于它。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: leader
        image: "docker.io/nginx:latest"
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
        ports:
        - containerPort: 80
```



kubernetes的代码结构如下

```bash
├── CHANGELOG
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── LICENSES
├── Makefile
├── Makefile.generated_files
├── OWNERS
├── OWNERS_ALIASES
├── README.md
├── SECURITY_CONTACTS
├── SUPPORT.md
├── api
├── build
├── cluster
├── cmd
│   ├── OWNERS
│   ├── clicheck
│   ├── cloud-controller-manager
│   ├── dependencycheck
│   ├── gendocs
│   ├── genkubedocs
│   ├── genman
│   ├── genswaggertypedocs
│   ├── genutils
│   ├── genyaml
│   ├── importverifier
│   ├── kube-apiserver
│   ├── kube-controller-manager
│   ├── kube-proxy
│   ├── kube-scheduler
│   ├── kubeadm
│   ├── kubectl
│   ├── kubectl-convert
│   ├── kubelet
│   ├── kubemark
│   ├── linkcheck
│   └── preferredimports
├── code-of-conduct.md
├── docs
│   └── OWNERS
├── go.mod
├── go.sum
├── hack
├── logo
├── pkg
│   ├── OWNERS
│   ├── api
│   ├── apis
│   ├── auth
│   ├── capabilities
│   ├── client
│   ├── cloudprovider
│   ├── cluster
│   ├── controller
│   ├── controlplane
│   ├── credentialprovider
│   ├── features
│   ├── fieldpath
│   ├── generated
│   ├── kubeapiserver
│   ├── kubectl
│   ├── kubelet
│   ├── kubemark
│   ├── printers
│   ├── probe
│   ├── proxy
│   ├── quota
│   ├── registry
│   ├── routes
│   ├── scheduler
│   ├── security
│   ├── securitycontext
│   ├── serviceaccount
│   ├── util
│   ├── volume
│   └── windows
├── plugin
│   ├── OWNERS
│   └── pkg
├── staging
│   ├── OWNERS
│   ├── README.md
│   ├── publishing
│   └── src
├── test
├── third_party
│   ├── OWNERS
│   ├── etcd.BUILD
│   ├── forked
│   ├── multiarch
│   └── protobuf
```



k8s所有组件都有对应的二进制执行文件，全部放在cmd目录，每个子目录对应一个组件。



## 文章列表:

1. kubectl
   1. [kubectl (一)](https://github.com/youerning/blog/blob/master/kubernetes/kubectl1.md)



## 番外篇

- [ingress-nginx-controller代码阅读](https://github.com/youerning/blog/blob/master/kubernetes/nginx-ingress-controller.md)

