在深度学习训练的时候使用GPU而不是CPU我想已经是不争的事实了，虽然MX150并不在下面的官网列表，但是其实MX150也是支持CUDA的。

https://developer.nvidia.com/cuda-gpus

## 环境
小米笔记本Air 13
- OS: win10
- CPU: I7 7500U
- GPU: MX150
- GPU驱动: 425.25
- tensorflow: 1.13.1
- tensorflow-gpu: 1.13.1
- visual studio: 2019

## 安装TensorFlow
现在TensorFlow的whl文件已经打包的非常好了，基本上是可以安装上的，但是如果没有CUDA之类的驱动的话，在导入tensorflow的时候会报错。
```
pip install tensorflow tensorflow-gpu
```

## 安装依赖
为了装上英伟达的CUDA套件还需要安装visual studio, 因为windows的相关编译环境跟visual studio绑在了一起，即使你只想装其中一部分，还是得装上visual studio

### 安装visual studio
而windows的安装程序不会太难，就是下一步，下一步。

### 安装 cuda toolkits
CUDA toolkits 10.0  

https://developer.nvidia.com/cuda-zone

默认安装即可，下一步下一步。


### 安装cudnn
cudnn 7.6.0.64

https://developer.nvidia.com/cudnn
> 注意千万不要贪最新的版本，tensorflow官方不一定支持!

cudnn解压后放在C:\tools\cuda

最后加入环境变量:

```
C:\tools\cuda\bin
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v10.1\extras\CUPTI\lib64
```

官方说明如下:
> 软件要求

> 必须在系统中安装以下 NVIDIA® 软件：
>NVIDIA® GPU 驱动程序 - CUDA 10.0 需要 410.x 或更高版本。

> CUDA® 工具包 - TensorFlow 支持 CUDA 10.0（TensorFlow 1.13.0 及更高版本）

> CUDA 工具包附带的 CUPTI。
cuDNN SDK（7.4.1 及更高版本）
（可选）

> TensorRT 5.0，可缩短在某些模型上进行推断的延迟并提高吞吐量。

参考页面:
https://www.tensorflow.org/install/gpu

各个版本的兼容测试情况
https://www.tensorflow.org/install/source#linux


安装参考: 

https://towardsdatascience.com/installing-tensorflow-with-cuda-cudnn-and-gpu-support-on-windows-10-60693e46e781

https://medium.com/@johnnyliao/%E5%9C%A8nvidia-mx150%E7%9A%84win10%E5%AE%89%E8%A3%9Dcuda-toolkit-cudnn-python-anaconda-and-tensorflow-91d4c447b60e
