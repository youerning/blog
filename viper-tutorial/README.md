# Golang配置管理viper快速入门教程

几乎所有程序都是可以配置的，这些配置信息一般以配置文件的方式存在，各编程语言有自己的配置管理方案，而Golang的一个非常流行和强大的配置管理库是`viper`, 是`cobra`作者写来跟`cobra`一起配合使用而编写的。

> 不知道cobra是什么? 可以参考我的文章[cobra快速入门](https://youerning.top/post/cobra-tutorial)



## 快速入门

假设当前工作目录存在配置文件`config.yaml`, 其内容如下:

```yaml
age: 188
name: zhangsan
```

viper使用起来还是比较简单的，因为viper考虑到大多数人只会有一个配置的数据源, 所以采用了单例设计模式，也就是不需要手动的初始化一个实例，引入即可使用，非常方便，下面看一个简单的例子。

```go
package main

import (
	"fmt"

	"github.com/spf13/viper"
)

func main() {
	// 设置配置文件相关信息
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	// 显式的调用读取方法
	err := viper.ReadInConfig()
	if err != nil {
		fmt.Println("读取配置文件失败:", err)
		panic(err)
	}

	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
}

```

输出如下:

```sh
hello zhangsan, your age is 188
```

可以看到, viper的是用还是比较简单的，设置配置文件的必要信息, 文件名, 文件类型, 然后就可以读取了, 获取也是调用相应类型的Get方法即可。

viper支持多种类型的配置文件，如: JSON, TOML, YAML, HCL, envfile, Java properties文件等。

在获取键值的时候你可能有一些疑问, 如果本身的数据时`int`, 但是我通过`GetString`方法会报错么? 或者相反的情况会怎么样? 键值的大小写写错了会怎么样? 这些疑问在获取键值那一节再进行说明，这里暂时按下不表。



## 设置键值

配置管理总的来说就两件事，设置键值，获取键值。所以`viper`的功能在本文中被分为了这两部分。



### 读取配置

值得注意的是配置不总是以配置文件的方式存在，它可能存在数据库，可能存在源代码里，所以这里为了归纳所有情况就写成了读取配置。

### 读取配置文件

假设配置文件叫`config.yaml`并且在程序执行时的工作目录, 那么读取代码如下

```go
// 设置配置文件相关信息
// 设置文件名
viper.SetConfigName("config")
// 设置文件类型
viper.SetConfigType("yaml")
// 文件搜索路径
viper.AddConfigPath(".")
// 显式的读取配置文件
err := viper.ReadInConfig()
```

这一部分其实在前文已经简单的介绍过了，不过更详细的注释了一下，值得注意的是`viper.AddConfigPath`可以调用多遍，比如我们希望先搜索`/etc/<你的配置目录>`目录, 然后搜索用户家目录`~`, 最后才是当前工作目录， 一般来说，这是比较常见的用法，搜索的优先级是你添加的路径的次序。



### 读取代码中的配置

这种情况感觉比较少见，因为配置文件一般独立于源代码，如果在源代码里面，那么改配置文件还要重新编译，会是一件比较头疼的事，不过这个接口可以在`viper`不支持的远端存储类型情况下，很好的扩展自己使用配置文件的方式。

代码如下

```go
package main

import (
	"bytes"
	"fmt"

	"github.com/spf13/viper"
)

func main() {
	viper.SetConfigType("yaml")
	var yamlExample = []byte(`
age: 188
name: zhangsan
`)

	viper.ReadConfig(bytes.NewBuffer(yamlExample))
	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
}
```



### 读取远端存储

常用的配置中心主要由两个`etcd`, `consul`, 这里以`etcd3`为例

> 值得注意的是: etcd, etcd3是不一样的，两者的协议不一样!!!

```go
package main

import (
	"fmt"

	"github.com/spf13/viper"
	_ "github.com/spf13/viper/remote"
)

func main() {
	viper.AddRemoteProvider("etcd3", "http://<etcd3的地址和端口>", "/viper/config")
	viper.SetConfigType("yaml")
	err := viper.ReadRemoteConfig()
	if err != nil {
		fmt.Println("读取etcd3配置失败", err)
		panic(err)
	}

	// 获取各字段的值
	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
}
```

你可以用下面的命令在etcd中设置配置内容(注意: 是etcd3)

```sh
cat /tmp/config.yaml |etcdctl put "/viper/config"
```



### 设置默认值

一般来说，一个良好的程序总有友好的默认参数，即用户什么都不设置也能跑起来。

> 实名diss BFE的配置参数!!! 设置太复杂了。

viper的默认值设置比较简单，代码如下

```go
func main() {
	viper.SetConfigType("yaml")
	var yamlExample = []byte(`
name: zhangsan
`)
	viper.SetDefault("age", 188)
	viper.ReadConfig(bytes.NewBuffer(yamlExample))

	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
}
```



### 绑定命令行参数

`viper`被设计成`cobra`的最佳拍档，所以必然可以跟命令行参数绑定。

```go
package main

import (
	"bytes"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var rootCmd = cobra.Command{
	Use: "demo",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
	},
}

func init() {
	viper.SetConfigType("yaml")

	var yamlExample = []byte(`
name: zhangsan
`)

	viper.ReadConfig(bytes.NewBuffer(yamlExample))
	rootCmd.Flags().Int("age", 0, "your age")
	viper.BindPFlags(rootCmd.Flags())
}

func main() {
	rootCmd.Execute()
}
```

然后我们可以在命令行参数指定`age`对应的值。

```sh
go run demo5/main.go --age 18
# 输出如下
hello zhangsan, your age is 18
```



### 环境变量

读取环境变量还是比较简单的

```go
package main

import (
	"bytes"
	"fmt"
	"os"

	"github.com/spf13/viper"
)

func main() {
	viper.SetConfigType("yaml")

	var yamlExample = []byte(`
name: zhangsan
`)

	viper.ReadConfig(bytes.NewBuffer(yamlExample))
	viper.SetEnvPrefix("spf") // 会转成大写SPF
	viper.BindEnv("age")

	// 设置环境变量
	os.Setenv("SPF_AGE", "188")
	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
}
```

值得注意的是， 这里为了演示方便才直接在代码里面设置环境变量，一般来说，环境变量在程序外部，比如通过下面命令手动设置环境变量

```sh
export SPF_AGE=188
```

> 环境变量必须全部大写，因为viper对于环境变量的变量名是大小写敏感的!!!



### 保存配置文件

最后就是我们可以将配置保存下来，因为这些配置可能从多个地方获取如环境变量，命令行参数等，保存的方法一共有三个接口

- viper.WriteConfig 从哪读保存回哪
- viper.WriteConfigAs 配置文件另存为
- viper.SafeWriteConfigAs  指定路径文件不存在的情况下，才配置文件另存为



## 获取键值

设置了键值自然要获取，因为是静态语言所以内置的类型都有对应的方法，比如`int`对应`GetInt`, `sting`对应`GetString`。

值得注意的是, viper在获取键值的时候，**键是大小写不敏感的**，也就是说字段`age`通过下面多种方式都是可以的。

```go
viper.GetInt("age")
viper.GetInt("Age")
viper.GetInt("AGE")
viper.GetInt("aGe"))
```

> 妈妈再也不用担心我写错键名(key)了。



还有就是你尽管获取，参数类型不对，我来转换，比如`age: 18`, 不通过`GetInt`也是可以的。

```go
fmt.Println("GetBool:", viper.GetBool("age"))  //非数字0都是true
fmt.Println("GetString:", viper.GetString("age"))
fmt.Println("GetStringSlice:", viper.GetStringSlice("age"))
```

输出如下:

```sh
GetBool: true
GetString: 188
GetStringSlice: [188]
```

这个些转换就是见仁见智了，有的人觉得不错，有的人觉得不行，一般来说不会这样使用。



### 优先级

前文展示了各种设置键值的方法，很容易会出现多种设置方法同时使用的情况，所以`viper`对于这种情况自然设置一定的优先级。

优先级如下:

- explicit call to `Set`
- flag
- env
- config
- key/value store
- default



### 获取语法

有时候配置文件并不是像前文写得那样扁平，而是嵌套的数据接口，`viper`对于这种情况也是早有预料的。

```go
package main

import (
	"bytes"
	"fmt"

	"github.com/spf13/viper"
)

func main() {
	viper.SetConfigType("yaml")
	var yamlExample = []byte(`
age: 188
name: zhangsan
scores:
  yuwen: 61
  shuxue: 88
programs: ["python", "golang", "javascript", "rust"]`)

	if err := viper.ReadConfig(bytes.NewBuffer(yamlExample)); err != nil {
		panic(fmt.Sprintf("读取配置文件失败, %v", err))
	}
	fmt.Printf("hello %s, your age is %d\n", viper.GetString("name"), viper.GetInt("age"))
	fmt.Printf("yuwen: %d\n", viper.GetInt("scores.yuwen"))
	fmt.Printf("favorite program: %s\n", viper.GetString("programs.0"))
}
```

可以看到只要将层级结构用分隔符 **.**（点）组合在一起就可以了，而数组可以通过数字来索引。

>  viper可以通过`viper.KeyDelimiter`方法手动设置分隔符, 这可以避免数据字段中本来就存在"."的情况。



### 监听配置文件更新

有时候我们需要实时的监听配置文件修改，以便在不重启应用的情况下更新，所以监听配置文件还是很有用的，viper自然也支持。

```go
viper.OnConfigChange(func(e fsnotify.Event) {
	fmt.Println("Config file changed:", e.Name)
})
viper.WatchConfig()
```

`viper.OnConfigChange`用户注册钩子函数, `viper.WatchConfig`用于启用实时监听功能。



## 总结

程序总是要配置的，特别是静态语言，因为要编译, 还不是一下就能编译完，所以参数配置放在代码里面会显得很不方便，因此大多数程序的做法是将参数配置独立的放在一个配置文件里面,  配置文件的格式有很多，还有很多通用的操作，比如绑定参数到命令行参数，读取远程配置，这些自己写起来太麻烦了，所以出现了`viper`。



更多参数说明请参考官方文档:https://github.com/spf13/viper