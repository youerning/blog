# golang命令行cobra 快速入门教程

`cobra`也许是go语言现有最好的命令行框架了，在各大项目中皆有使用，比如最出名的`kubernetes`, 所以要写一个稍微复杂的命令行工具，使用cobra还是不错的，`cobra`内置了非常多有用的功能，包括但不限于，自动生成帮助文档,  生成命令行代码的脚手架工具, 智能提示等等。


## 命令行相关知识

在学习`cobra`之前我们应该先了解一下命令行下的参数类型，`cobra`将命令行参数分为了两类，一类叫做args(位置参数), 一类叫做flags(可选参数)。

以下面的命令为例

```sh
ls -l -a -h --color=auto /tmp  /var/log
```

上面的命令可以分为三个部分, `ls`, `-l -a -h`, `/tmp /var/log`, 第一部分是可执行文件名, 第二部分是可选参数, 第三部分是位置参数。

如果你使用linux命令足够多，你会注意到flags(可选参数)不都是上述说明的那样，比如下面的命令

```sh
ls -l -a -h --color=auto /tmp  /var/log
```

可以看到上面的命令多了`--color=auto`这样的flags。

总的来说在这两类参数中，flags(可选参数)总是以一个或多个`-`(横线)开头, 而命令行参数一般不以`-`(横线)开头。

> 但，事情总有意外, 比如linux的很多命令接受参数`-`(横线), 表示读取标准输出, 这个参数说实话，还真不好分类，个人倾向于分为位置参数。

如果你熟悉python的`typer`或者看过我写的[`typer`快速入门教程](https://youerning.top/post/typer-tutorial)的话，你会发现两者对于参数的定义是大同小异的, 虽然两者使用的术语不同。



## 快速入门

首先从一个超级简单的例子来了解一下cobra的使用。

```go
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var age int

var rootCmd = &cobra.Command{
	Use:   "cabra1 [Name]",
	Short: "cabra1 demo command",
	Args:  cobra.MinimumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("hello %s, your age is %d?", args[0], age)
	},
}

func init() {
	rootCmd.Flags().IntVarP(&age, "age", "a", 18, "how old are you?")
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func main() {
	rootCmd.Execute()
}
```

像所有命令行框架一样，它会自动生成帮助文档，命令如下:

```sh
go run main.go --help
# 下面为帮助文档
cabra1 demo command

Usage:
  cabra1 [Name] [flags]

Flags:
  -a, --age int   how old are you? (default 18)
  -h, --help      help for cabra1
```

如果直接运行会是以下结果。

```sh
go run main.go
# 输出如下
Error: requires at least 1 arg(s), only received 0
...省略帮助文档...
```

你会发现它会提示你至少需要一个args(位置参数), 而这个设置由`Args:  cobra.MinimumNArgs(1)`这部分代码设置。



所以我们至少需要一个参数，比如。

```sh
go run main.go zhangsan
# 输出如下
hello zhangsan, your age is 18?
```

当然了，我们也可以设置flags(可选参数), 比如

```sh
go run main.go zhangsan -a 188
# 输出如下
hello zhangsan, your age is 188?
```

> 注意: 这个简单的例子并不是cobra的最佳实践!!!



## 位置参数

cobra对于位置参数的支持其实并不多，提供的校验方法基本都是检查参数的个数而不是参数类型。

默认情况下，有以下默认方法

- `NoArgs` - 如果出现任何位置参数就报错
- `ArbitraryArgs` - 接受任意数量的位置参数
- `OnlyValidArgs` - 如果位置参数不在`ValidArgs`的参数列表中就报错
- `MinimumNArgs(int)` - 如果小于指定参数个数就报错
- `MaximumNArgs(int)` - 如果大于指定参数个数就报错
- `ExactArgs(int)` - 不完全等于指定参数个数就拨错
- `ExactValidArgs(int)` - 需要配合`ValidArgs`的参数列表使用, 在`ValidArgs`列表中且参数个数等于指定参数个数
- `RangeArgs(min, max)` - 位置参数的数量范围

> 就是简单的翻译了一下官方文档...

唯一需要注意的就是`ValidArgs`的配合使用， 比如。

```go
var rootCmd = &cobra.Command{
	Use:       "cabra1 [Name]",
	Short:     "cabra1 demo command",
	Args:      cobra.OnlyValidArgs,
    // validArgs的配置
	ValidArgs: []string{"zhangsan", "lisi"},
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("hello %s, your age is %d?", args[0], age)
	},
}


```

如果位置参数不在`ValidArgs`列表内就会报错, 如下:

```sh
go run main.go wangwu
# 报错如下
Error: invalid argument "wangwu" for "cabra1"
```



除此之外我们还可以自定义位置参数的验证方法，代码如下:

```go
var rootCmd = &cobra.Command{
	Use:   "cabra1 [Name]",
	Short: "cabra1 demo command",
	Args: func(cmd *cobra.Command, args []string) error {
		for _, arg := range args {
			_, err := strconv.Atoi(arg)
			if err == nil {
				return fmt.Errorf("仅支持字符串, 不支持使用数字[%s]作为参数", arg)
			}
		}
		return nil
	},
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("hello %s, your age is %d?", args[0], age)
	},
}
```

使用以下命令会报错

```sh
go run main.go 123123
Error: 仅支持字符串, 不支持使用数字[123123]作为参数
```



## 可选参数

可选参数大致可以分为两个部分，非持久化可选参数, 持久化可选参数(PersistentFlags), , 这个持久化的意思是说，该参数会传递到子命令, 有点继承的意思。



### 非持久化参数

因为Golang是静态语言所以，每种内置类型都有一个对应的方法，比如`int`对应`Int()`, `string`对应`String()`

简单列举一下常用的类型。

```go
var age int
var s *string
var i *int
var f *float64
var sa *[]string

func init() {
	rootCmd.Flags().IntVarP(&age, "age", "a", 18, "how old are you?")
	s = rootCmd.Flags().String("string", "", "specify string")
	i = rootCmd.Flags().Int("int", 0, "specify int")
	f = rootCmd.Flags().Float64("float64", 0.0, "specify float64")
	sa = rootCmd.Flags().StringArray("stringarray", []string{}, "specify string array")

}

func main() {
	rootCmd.Execute()
	fmt.Println("s:", *s, "i:", *i, "f:", *f, "sa:", *sa)
}

```

查看帮助文档如下:

```sh
cabra1 demo command

Usage:
  cabra1 [Name] [flags]

Flags:
  -a, --age int                   how old are you? (default 18)
      --float64 float             specify float64
  -h, --help                      help for cabra1
      --int int                   specify int
      --string string             specify string
      --stringarray stringArray   specify string array
```

> 注意: --stringarray的多参数需要, `--stringarray param1 --stringarray param2`这样指定!!!



可选参数用多种使用形式, 以Int为例有三种额外的形式，如`IntP`, `IntVar`,`IntVarP`

比如:

```go
var intp *int
var intVar int
var intVarP int

intp = rootCmd.Flags().IntP("intp", "i", 1, "intp set")
rootCmd.Flags().IntVar(&intVar, "intvar", 2, "intvar set")
rootCmd.Flags().IntVarP(&intVarP, "intvarp", "p", 3, "intvarp set")
```

各种形式的意义如下:

- `<Type>` 返回可选参数对应的类型指针, 不能设置参数缩写形式

- `<Type>P` 类似于前者， 不过可以设置参数的缩写形式

- `<Type>Var` 可传入指定类型的参数地址, 不能设置参数缩写形式
- `<Type>VarP` 类似于前者，不过可以设置参数的缩写形式

具体使用那种形式，根据自己的需求设置。



### 持久化参数

跟非持久化参数的差别主要是多了个`Persistent`， 比如下面的示例

```go
var pi *int
pi = rootCmd.PersistentFlags().Int("pi", 18, "persisten int")
```

如果要体现持久化参数的价值，需要设置一个子命令。比如下面的例子。

```go
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var pi *int

var childCmd = &cobra.Command{
	Use:   "child [Name]",
	Short: "child command",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("child command called")
	},
}

var rootCmd = &cobra.Command{
	Use:   "cabra1 [Name]",
	Short: "cabra1 demo command",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			fmt.Printf("hello %s", args[0])
		} else {
			fmt.Println("hello world")
		}

	},
}

func init() {
	rootCmd.AddCommand(childCmd)
	pi = rootCmd.PersistentFlags().Int("pi", 18, "persisten int")
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func main() {
	rootCmd.Execute()
}
```

上面的例子是在`rootCmd`上面加了一个持久化参数，并且增加了一个子命令`childCmd`。

然后查看child子命令的帮助文档，会发现可以设置持久化参数`--pi`

```sh
$ go run demo2/main.go  child --help
child command

Usage:
  cabra1 child [Name] [flags]

Flags:
  -h, --help   help for child

Global Flags:
      --pi int   persisten int (default 18)
```



## 子命令

子命令在前面已经简单的提到了，总的来说子命令和一般的命令没有什么明显的区别，各命令之间的层级关系是通过`cobra.Command`的`AddCommand`方法来构造的，比如前面的`rootCmd.AddCommand(childCmd)`就是将`childCmd`变成`rootCmd`的子命令, 反过来也可以，不过要注意的是，需要将根节点放在执行入口。



### 分组

子命令中还有一个有用的功能点，即分组，如果你使用过`kubectl`应该不默认。

这里再介绍一下如何分组，示例代码如下

```go
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var groups = []*cobra.Group{
	{ID: "1", Title: "Basic Commands (Beginner):"},
	{ID: "2", Title: "Troubleshooting and Debugging Commands:"},
}

var child1Cmd = &cobra.Command{
	Use:     "child1 [Name]",
	Short:   "child1 command",
	GroupID: "2",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("child command called")
	},
}

var child2Cmd = &cobra.Command{
	Use:     "child2 [Name]",
	Short:   "child2 command",
	GroupID: "1",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("child command called")
	},
}

var rootCmd = &cobra.Command{
	Use:   "cabra1 [Name]",
	Short: "cabra1 demo command",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			fmt.Printf("hello %s", args[0])
		} else {
			fmt.Println("hello world")
		}

	},
}

func init() {
	rootCmd.AddGroup(groups...)
	rootCmd.AddCommand(child1Cmd)
	rootCmd.AddCommand(child2Cmd)
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func main() {
	rootCmd.Execute()
}
```

然后查看帮助文档

```sh
$ go run demo3/main.go --help
cabra1 demo command

Usage:
  cabra1 [Name] [flags]
  cabra1 [command]

Basic Commands (Beginner):
  child2      child2 command

Troubleshooting and Debugging Commands:
  child1      child1 command

Additional Commands:
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command

Flags:
  -h, --help   help for cabra1

Use "cabra1 [command] --help" for more information about a command.
```

可以看到child1, child2两个子命令分别有了不同的分组



## 钩子函数

`Cobra`提供了许多钩子函数，比如`PreRun`在`主命令`之前执行, `PostRun`在`主命令`执行后执行

> 这里之所以用主命令而不是`Run`方法, 是因为, 还有一个`RunE`



下面是各个钩子函数的说明

- `PersistentPreRun`  持久化的PreRun, 即从父命令继承过来的PreRun
- `PreRun`  主命令之前前
- `Run`  主命令
- `PostRun`  主命令执行后
- `PersistentPostRun`  持久化的PostRun, 即从父命令继承过来的PostRun



## 脚手架工具

前面无论是单个命令还是多个命令都是在同一个文件中定义，这样自然是没问题的，但并不是`Cobra`推荐的最佳实践，为了让使用者可以更加方便的使用，`Cobra`提供了脚手架工具.



### 安装

可以通过下面命令安装

```sh
go install github.com/spf13/cobra-cli@latest
```



### 创建命令行

在自己的go项目中执行

> 如果还没有创建， 记得 `go mod init <你的模块名>`

```sh
cobra init 
```

然后可以得到下面的目录接口

```sh
.
├── cmd
│   └── root.go
├── go.mod
├── go.sum
├── LICENSE
└── main.go
```

> LICENSE是可以选的, 默认是空, 可选择的LICENSE列表有: **GPLv2**, **GPLv3**, **LGPL**, **AGPL**, **MIT**, **2-Clause BSD** or **3-Clause BSD**.

初始化完成之后就可以直接执行了

```sh
go run main.go help
# 默认只有长长的描述
A longer description that spans multiple lines and likely contains
examples and usage of using your application. For example:

Cobra is a CLI library for Go that empowers applications.
This application is a tool to generate the needed files
to quickly create a Cobra application.
```



### 添加子命令

添加子命令也是比较简单的

```sh
# 添加子命令child1, child2
# cobra-cli add child1
child1 created at /root/youerning.top/go-play/cobra
# cobra-cli add child2
child2 created at /root/youerning.top/go-play/cobra

# 查看帮助文档
# go run main.go help
A longer description that spans multiple lines and likely contains
examples and usage of using your application. For example:

Cobra is a CLI library for Go that empowers applications.
This application is a tool to generate the needed files
to quickly create a Cobra application.

Usage:
  cobratest [command]

Available Commands:
  child1      A brief description of your command
  child2      A brief description of your command
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command

Flags:
  -h, --help     help for cobratest
  -t, --toggle   Help message for toggle

Use "cobratest [command] --help" for more information about a command.
```

添加子命令之后的目录结构如下:

```sh
.
├── cmd
│   ├── child1.go
│   ├── child2.go
│   └── root.go
├── go.mod
├── go.sum
├── LICENSE
└── main.go
```



## 总结

`Cobra`的设计的还是很棒的，提供了脚手架工具，提供了比较完备的命令行框架, 前者可以让使用者遵循`Cobra`的最佳实践，后者可以让开发更有效率并且专注于业务(好的代码框架总是这样), 其实命令行工具还有一部分是必不可少的，那就是配置管理(`Cobra`的最佳拍档`viper`，它们是同一个作者)，但是这篇文章碍于篇幅就不介绍。

`viper`的快速入门: https://youerning.top/post/viper-tutorial



最后贴一下官方文档链接:

**cobra**: https://cobra.dev/

**cobra-cli**: https://github.com/spf13/cobra-cli/blob/main/README.md