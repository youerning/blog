# minikube环境安装

前言: 记录k8s实验过程, 分享一些碰到的问题以及解决方案

## 前置条件
- 科学上网代理
- centos7虚拟机

> 参考: https://kubernetes.io/docs/tasks/tools/install-minikube/


## 第一步 安装hypervisor
> For Linux, install VirtualBox or KVM.
> 参考:  https://www.linuxtechi.com/install-kvm-hypervisor-on-centos-7-and-rhel-7/    

> 这里选择使用kvm作为hypervisor,即将k8s集群环境安装在kvm虚拟机里面,值得注意的是这相当于虚拟机里面装虚拟机,性能有很大的问题,我是在kvm虚拟机里面装kvm

### 1.1 查看是否支持虚拟化

```
grep -E '(vmx|svm)' /proc/cpuinfo
```


### 1.2 安装kvm

```
yum install qemu-kvm qemu-img virt-manager libvirt libvirt-python libvirt-client virt-install virt-viewer bridge-utils
```


### 1.3 启动libvirtd

```
systemctl start libvirtd
systemctl enable libvirtd
```


### 1.4 检查kvm module 是否加载成功

```
lsmod | grep kvm
kvm_intel             162153  0
kvm                   525409  1 kvm_intel
```



## step2 安装kubectl
> 参考:https://kubernetes.io/docs/tasks/tools/install-kubectl/

### 2.0 配置代理
由于kubectl源在google, 所以配置代理

```
[root@k8s ~]# export https_proxy=http://<your_proxy>
[root@k8s ~]# export http_proxy=http://<your_proxy>
```


> 如果你没有代理,我也无能为力了..

### 2.1 配置google源

```
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
> [kubernetes]
> name=Kubernetes
> baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
> enabled=1
> gpgcheck=1
> repo_gpgcheck=1
> gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
> EOF
```


### 2.2 安装kubectl

```
yum install -y kubectl
```


### step3 安装minikube
> 参考:https://blog.csdn.net/guizaijianchic/article/details/78421800
https://yq.aliyun.com/articles/221687

### 3.1.1 下载安装(官方安装)

```
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin/
```


### 3.1.2 安装阿里云修改版本(个人使用推荐)

```
curl -Lo minikube http://kubernetes.oss-cn-hangzhou.aliyuncs.com/minikube/releases/v0.28.0/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin/
```

> 使用阿里云修改版本,会加速整个集群的安装, 因为会拉国内的镜像.


### 3.2 安装驱动
> 参考: https://github.com/kubernetes/minikube/blob/master/docs/drivers.md#kvm-driver
https://github.com/kubernetes/minikube/blob/master/docs/drivers.md#kvm2-driver


```
curl -LO https://storage.googleapis.com/minikube/releases/latest/docker-machine-driver-kvm2 && chmod +x docker-machine-driver-kvm2 && sudo mv docker-machine-driver-kvm2 /usr/local/bin/
```



### 3.3.1 启动minukube(官方)

```
minikube start
```


### 3.3.2 启动minikube

```
minikube start --registry-mirror=https://registry.docker-cn.com --docker-env HTTP_PROXY=http://<your_proxy> --docker-env HTTPS_PROXY=http://<your_proxy>
```


> 由于众所周知的原因需要为docker配置代理,不然会很慢

## step4 配置集群环境
默认配置有点少, 加点内存,cpu

### 4.1 配置k8s内存、cpu

```
minikube config set memory 8192
minikube config set cpus 4
```




