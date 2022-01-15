# Kubectl源码阅读

本章的任务主线任务如下

1. kubectl怎么启动
2. kubectl apply -f deployement.yaml发送了什么
3. kubectl logs -f deplyment/redis-leader发生了什么
4. kubectl exec -it redis-leader-xxxx-yyyy发生了什么
5. kubectl describe deployment/redis-leader发生了什么



> 2-5暂时不展开了



其实kubectl的每个子命令流程大体分为三步,

1. 解析命令行参数
2. 创建kubeconfig(具体的struct名字是ConfigFlags)对象, 基于这个对象创建对应的rest client(默认是一个本地缓存的client)
3. 基于命令参数的操作用rest client与api server进行交互



首先以下面的命令作为起始任务，看看kubectl的代码结构

```bash
kubectl get deploy
```



## 启动

kubernetes的所有组件入口函数几乎都是一致的，使用的命令行解析库是[cobra](https://github.com/spf13/cobra)

```go
func main() {
	rand.Seed(time.Now().UnixNano())

	command := cmd.NewDefaultKubectlCommand()

	// 命令行设置
    // 设置正则函数，将_转成-
	pflag.CommandLine.SetNormalizeFunc(cliflag.WordSepNormalizeFunc)
    // 兼容用原生flag库设置的命令行参数
	pflag.CommandLine.AddGoFlagSet(goflag.CommandLine)
    // 初始化日志
	logs.InitLogs()
	defer logs.FlushLogs()
	
    // 开始调用
	if err := command.Execute(); err != nil {
		os.Exit(1)
	}
}


```

为什么不直接用标准库的flag呢？因为标准库的flag库与linux下的POSIX命令行参数标准不兼容，比如linux下的命令行 -a -b可以连起来写成-ab, 而golang官方库的flag不支持。

> GNU POSIX命令行参数标准参考: http://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html

```go
// New一个对象  常规操作了
func NewDefaultKubectlCommand() *cobra.Command {
	return NewDefaultKubectlCommandWithArgs(NewDefaultPluginHandler(plugin.ValidPluginFilenamePrefixes), os.Args, os.Stdin, os.Stdout, os.Stderr)
}

func NewDefaultKubectlCommandWithArgs(pluginHandler PluginHandler, args []string, in io.Reader, out, errout io.Writer) *cobra.Command {
	cmd := NewKubectlCommand(in, out, errout)

    // 默认会检测命令行是否有调用插件的pluginHandler
	if pluginHandler == nil {
		return cmd
	}

    // 检查参数中是不是调用插件
	if len(args) > 1 {
        // 将kubectl get deploy 截断成 get deploy以检测后续命令是否是插件的命令行
        // 这里显然不是
		cmdPathPieces := args[1:]

		if _, _, err := cmd.Find(cmdPathPieces); err != nil {
            // 如果是调用插件就执行然后退出
			if err := HandlePluginCommand(pluginHandler, cmdPathPieces); err != nil {
				fmt.Fprintf(errout, "Error: %v\n", err)
				os.Exit(1)
			}
		}
	}

	return cmd
}

// 最终command在这里构造
func NewKubectlCommand(in io.Reader, out, err io.Writer) *cobra.Command {
	warningHandler := rest.NewWarningWriter(err, rest.WarningWriterOptions{Deduplicate: true, Color: term.AllowsColorOutput(err)})
	warningsAsErrors := false
	// 最顶级的Command对象, 多有子命令都挂载在这个对象之下
	cmds := &cobra.Command{
		Use:   "kubectl",
		Short: i18n.T("kubectl controls the Kubernetes cluster manager"),
		Long: templates.LongDesc(`
      kubectl controls the Kubernetes cluster manager.

      Find more information at:
            https://kubernetes.io/docs/reference/kubectl/overview/`),
		Run: runHelp,
		// cobra的Persistent关键字代表持久化，可继承的意思，即子命令会继承
        // 运行RunE之前
		PersistentPreRunE: func(*cobra.Command, []string) error {
			rest.SetDefaultWarningHandler(warningHandler)
			return initProfiling()
		},
        // 运行RunE之前
		PersistentPostRunE: func(*cobra.Command, []string) error {
			if err := flushProfiling(); err != nil {
				return err
			}
			if warningsAsErrors {
				count := warningHandler.WarningCount()
				switch count {
				case 0:
					// no warnings
				case 1:
					return fmt.Errorf("%d warning received", count)
				default:
					return fmt.Errorf("%d warnings received", count)
				}
			}
			return nil
		},
	}

	flags := cmds.PersistentFlags()
	flags.SetNormalizeFunc(cliflag.WarnWordSepNormalizeFunc) // 对于下划线 _ 的参数警告
	flags.SetNormalizeFunc(cliflag.WordSepNormalizeFunc)

    // 增加性能调优的参数开关
    // 统计CPU,内存等相关信息，用于性能优化
	addProfilingFlags(flags)

	flags.BoolVar(&warningsAsErrors, "warnings-as-errors", warningsAsErrors, "Treat warnings received from the server as errors and exit with a non-zero exit code")

    // ConfigFlags对象, 后续创建rest client的生成基本来自这
    // 创建空对象
	kubeConfigFlags := genericclioptions.NewConfigFlags(true).WithDeprecatedPasswordFlag()
    // 设置命令参数，将参数解析值绑定到kubeConfigFlags
	kubeConfigFlags.AddFlags(flags)
    // 包装一层，其实差不多就是加一个是否匹配client与server版本的参数match-server-version
	matchVersionKubeConfigFlags := cmdutil.NewMatchVersionFlags(kubeConfigFlags)
	matchVersionKubeConfigFlags.AddFlags(cmds.PersistentFlags())
	// Updates hooks to add kubectl command headers: SIG CLI KEP 859.
    // 为rest client 增加HTTP Header
    // 类似: Kubectl-Command: kubectl apply
	addCmdHeaderHooks(cmds, kubeConfigFlags)
    // 为持久化命令行参数对象也增加(兼容)原生flag命令行参数
	cmds.PersistentFlags().AddGoFlagSet(flag.CommandLine)

    // 最终kubeconfig对象被包装成一个工厂类型
    // 该对象实现了DynamicClient(), KubernetesClientSet(), NewBuilder()等接口
    // 这一层层的包装是委托者设计模式，见下文
	f := cmdutil.NewFactory(matchVersionKubeConfigFlags)

    // 将标准输入,输出,错误包装一下
	ioStreams := genericclioptions.IOStreams{In: in, Out: out, ErrOut: err}

    // 下面就是kubectl的所有子命令，其中proxyCmd不兼容
    // 跟CommandHeaderRoundTripper不兼容, 所以单独创建
	// clear the WrapConfigFn before running proxy command.
	proxyCmd := proxy.NewCmdProxy(f, ioStreams)
	proxyCmd.PreRun = func(cmd *cobra.Command, args []string) {
		kubeConfigFlags.WrapConfigFn = nil
	}
    
	groups := templates.CommandGroups{
		{
			Message: "Basic Commands (Beginner):",
			Commands: []*cobra.Command{
				create.NewCmdCreate(f, ioStreams),
				expose.NewCmdExposeService(f, ioStreams),
				run.NewCmdRun(f, ioStreams),
				set.NewCmdSet(f, ioStreams),
			},
		},
		{
			Message: "Basic Commands (Intermediate):",
			Commands: []*cobra.Command{
				explain.NewCmdExplain("kubectl", f, ioStreams),
                // 本次命令kubectl get deploy会调用的子命令
				get.NewCmdGet("kubectl", f, ioStreams),
				edit.NewCmdEdit(f, ioStreams),
				delete.NewCmdDelete(f, ioStreams),
			},
		},
		{
			Message: "Deploy Commands:",
			Commands: []*cobra.Command{
				rollout.NewCmdRollout(f, ioStreams),
				scale.NewCmdScale(f, ioStreams),
				autoscale.NewCmdAutoscale(f, ioStreams),
			},
		},
		{
			Message: "Cluster Management Commands:",
			Commands: []*cobra.Command{
				certificates.NewCmdCertificate(f, ioStreams),
				clusterinfo.NewCmdClusterInfo(f, ioStreams),
				top.NewCmdTop(f, ioStreams),
				drain.NewCmdCordon(f, ioStreams),
				drain.NewCmdUncordon(f, ioStreams),
				drain.NewCmdDrain(f, ioStreams),
				taint.NewCmdTaint(f, ioStreams),
			},
		},
		{
			Message: "Troubleshooting and Debugging Commands:",
			Commands: []*cobra.Command{
				describe.NewCmdDescribe("kubectl", f, ioStreams),
				logs.NewCmdLogs(f, ioStreams),
				attach.NewCmdAttach(f, ioStreams),
				cmdexec.NewCmdExec(f, ioStreams),
				portforward.NewCmdPortForward(f, ioStreams),
				proxyCmd,
				cp.NewCmdCp(f, ioStreams),
				auth.NewCmdAuth(f, ioStreams),
				debug.NewCmdDebug(f, ioStreams),
			},
		},
		{
			Message: "Advanced Commands:",
			Commands: []*cobra.Command{
				diff.NewCmdDiff(f, ioStreams),
				apply.NewCmdApply("kubectl", f, ioStreams),
				patch.NewCmdPatch(f, ioStreams),
				replace.NewCmdReplace(f, ioStreams),
				wait.NewCmdWait(f, ioStreams),
				kustomize.NewCmdKustomize(ioStreams),
			},
		},
		{
			Message: "Settings Commands:",
			Commands: []*cobra.Command{
				label.NewCmdLabel(f, ioStreams),
				annotate.NewCmdAnnotate("kubectl", f, ioStreams),
				completion.NewCmdCompletion(ioStreams.Out, ""),
			},
		},
	}
    // 将上面对象作为子命令添加到cobra.Command对象中
	groups.Add(cmds)

	filters := []string{"options"}

	// 然后是其他子命令
	alpha := NewCmdAlpha(ioStreams)
	if !alpha.HasSubCommands() {
		filters = append(filters, alpha.Name())
	}

	templates.ActsAsRootCommand(cmds, filters, groups...)

	util.SetFactoryForCompletion(f)
	registerCompletionFuncForGlobalFlags(cmds, f)

	cmds.AddCommand(alpha)
	cmds.AddCommand(cmdconfig.NewCmdConfig(clientcmd.NewDefaultPathOptions(), ioStreams))
	cmds.AddCommand(plugin.NewCmdPlugin(ioStreams))
	cmds.AddCommand(version.NewCmdVersion(f, ioStreams))
	cmds.AddCommand(apiresources.NewCmdAPIVersions(f, ioStreams))
	cmds.AddCommand(apiresources.NewCmdAPIResources(f, ioStreams))
	cmds.AddCommand(options.NewCmdOptions(ioStreams.Out))

	return cmds
}
```



### 委托者模式

在深入get.NewCmdGet("kubectl", f, ioStreams)之前，首先看看委托者模式

```go
package main

import "fmt"

type Client interface {
	Get(string)
}

type A struct {
}

func (a *A) Get(val string) {
	fmt.Printf("A Get %s\n", val)
}

type B struct {
	Delegate Client
}

func (b *B) Get(val string) {
	fmt.Println("from B to Delegate")
	b.Delegate.Get(val)
}

type C struct {
	Delegate Client
}

func (c *C) Get(val string) {
	fmt.Println("from C to Delegate")
	c.Delegate.Get(val)
}

func main() {
	a := A{}
	b := B{&a}
	c := C{&b}
	c.Get("hello world")
}
```

输出如下:

```bash
from C to Delegate
from B to Delegate
A Get hello world 
```

总的来书，具体的实现由Delegate实现，上层就是一层层的往下委托, 而kubectl中的f := cmdutil.NewFactory(matchVersionKubeConfigFlags)就是如此。

以ToRESTConfig方法为例,委托调用链如下

```bash
factoryImpl.ToRESTConfig -> f.clientGetter.ToRESTConfig() -> MatchVersionFlags.ToRESTConfig -> f.Delegate.ToRESTConfig() -> ConfigFlags.ToRESTConfig
```

委托模式使得我们可以用聚合来替代继承，它还使我们可以模拟mixin





## 运行子命令

```go
// kubectl get deploy对应的子命令
// 为了减少篇幅，就将模板代码及命令行参数去掉了
func NewCmdGet(parent string, f cmdutil.Factory, streams genericclioptions.IOStreams) *cobra.Command {
	o := NewGetOptions(parent, streams)

	cmd := &cobra.Command{
		Run: func(cmd *cobra.Command, args []string) {
            // 填充必要的默认值, 以便后续能够正常调用
			cmdutil.CheckErr(o.Complete(f, cmd, args))
            // 验证参数是否正确
			cmdutil.CheckErr(o.Validate(cmd))
            // 最终的运行逻辑
			cmdutil.CheckErr(o.Run(f, cmd, args))
		},
	}

	return cmd
}
```

每个cobra.Command的创建其实差不多

```go
func (o *GetOptions) Run(f cmdutil.Factory, cmd *cobra.Command, args []string) error {
	// 省略了raw,watch参数对应的操作
    
    // 构造者模式
    // 以构造者模式创建一个实现了访问者模式的Result对象
	r := f.NewBuilder().
    	// 以map的方式传输数据对象，对响应内容中的数据做一层封装，这样就可以保留所有字段而不需要首先解析成一个struct
		Unstructured().
    	// 基于命令行参数设置查询的namespace
		NamespaceParam(o.Namespace).DefaultNamespace().AllNamespaces(o.AllNamespaces).
    	// 解析文件名参数 参数 -f
        // 这里没有指定 所以b.paths为空
		FilenameParam(o.ExplicitNamespace, &o.FilenameOptions).
    	// 解析标签选择器 参数 -l
		LabelSelectorParam(o.LabelSelector).
        // 解析字段参数
		FieldSelectorParam(o.FieldSelector).
        // 是否分段请求, 避免响应过大
		RequestChunksOf(chunkSize).
        // kubectl get deploy 指定了资源为deployment
		ResourceTypeOrNameArgs(true, args...).
    	// 配置result对象在出现错误的行为, 意思很明显，在出错之后继续
		ContinueOnError().
    	// 获取最新对象
		Latest().
        // 将对象展开
        // 比如对象是[a, b], 如果没有flatten就是完成访问[a,b]作为一个整体，反之, 让外层函数分别访问a,b
		Flatten().
        // 配置一个在请求中修改request对象函数
		TransformRequests(o.transformRequests).
        // 基于之前的配置，生成最终的result对象
		Do()

	allErrs := []error{}
	errs := sets.NewString()
    // 获取数据
	infos, err := r.Infos()

    // 关于怎么输出，就省略了
    
    // 将所有错误聚合在一起返回
	return utilerrors.NewAggregate(allErrs)
}
```



在深入请求的逻辑之前先看看代码中用到的设计模式，其实还有一个装饰器模式，但其实就是在原函数的基础上包装一层，就不说了。



### 构建者模式

```go
package main

import "fmt"

type Car struct {
	name  string
	color string
	speed string
}

func (c *Car) Name(name string) {
	c.name = name
}

func (c *Car) Color(color string) {
	c.color = color
}

func (c *Car) Speed(speed int) {
	c.speed = fmt.Sprintf("%d km/h", speed)
}

func (c *Car) Run() {
	fmt.Printf("一辆叫做%s的%s汽车以%s速度在狂奔", c.name, c.color, c.speed)
}

func main() {
	c1 := &Car{}
	c1.Name("c1")
	c1.Color("red")
	c1.Speed(100)
	c1.Run()
}

```

访问者模式的好处在于将熟悉的配置抽象成方法，可以隐藏一些复杂的细节，以及控制内部属性



### 访问者模式

```go
package main

import (
	"encoding/json"
	"fmt"
)

type VisitFunc func(interface{}) ([]byte, error)

type Visitor interface {
	Visit(VisitFunc) ([]byte, error)
}

type Data struct {
	Name string `json:"name" xml:"name"`
	Age  int    `json:"age" xml:"age"`
}

func (d *Data) Visit(fn VisitFunc) ([]byte, error) {
	fmt.Println("最内层调用")
	return fn(d)
}

type JsonVisitor struct {
	visitor Visitor
}

func (j *JsonVisitor) Visit(fn VisitFunc) ([]byte, error) {
	return j.visitor.Visit(func(data interface{}) ([]byte, error) {
		fmt.Println("由JsonVisitor访问")
		buf, _ := json.MarshalIndent(data, "", " ")
		fmt.Println(string(buf))
		return fn(data)
	})
}

type XMLVisitor struct {
	visitor Visitor
}

func (x *XMLVisitor) Visit(fn VisitFunc) ([]byte, error) {
	return x.visitor.Visit(func(data interface{}) ([]byte, error) {
		fmt.Println("由XMLVisitor访问")
		buf, _ := json.MarshalIndent(data, "", " ")
		fmt.Println(string(buf))
		return fn(data)
	})
}

func main() {
	d1 := Data{"d1", 11}
	jv := JsonVisitor{&d1}
	xv := XMLVisitor{&jv}
	buf, _ := xv.Visit(func(interface{}) ([]byte, error) {
		return []byte("最外层调用"), nil
	})
	fmt.Println(string(buf))

}
```

输出如下

```bash
最内层调用
由JsonVisitor访问
{
 "name": "d1",
 "age": 11
}
由XMLVisitor访问
<Data>
 <name>d1</name>
 <age>11</age>
</Data>
最外层调用
```



访问者模式的好处在于定义统一的接口让外部与内部交流，解耦数据与数据处理逻辑。

> 设计模式一般在大型项目用的多，是否需要看自己需要



### 构造Result对象

从上文知道，result对象最终在Do方法中创建，所以看下它对应的实现。

```go
// 返回一个实现了Visitor接口的Result对象，这个对象对应的资源用构建者构造的时候配置
func (b *Builder) Do() *Result {
    // 基于参数创建result对象, 创建对应的rest client等资源
	r := b.visitorResult()
    // mapper是一个用于在k8s资源与响应内容之间的一个映射，差不多可以看做一个解码器，这里的mapper, 在构造者的Unstructured方法中指定
	r.mapper = b.Mapper()
    
    // 后面的判断都是在result对象的基础上加上一层又一层的包装
	if b.flatten {
        // 将数据列表扁平化，
		r.visitor = NewFlattenListVisitor(r.visitor, b.objectTyper, b.mapper)
	}
	helpers := []VisitorFunc{}
	if b.defaultNamespace {
        // 设置namespace属性
		helpers = append(helpers, SetNamespace(b.namespace))
	}
	if b.requireNamespace {
         // 如果数据对象没有namespace就设置一个，有就检验是否与需要的一致
		helpers = append(helpers, RequireNamespace(b.namespace))
	}
	helpers = append(helpers, FilterNamespace)
	if b.requireObject {
        // 检索资源, 在这里触发http 请求
		helpers = append(helpers, RetrieveLazy)
	}
	if b.continueOnError {
        // 遇到错误时继续
		r.visitor = NewDecoratedVisitor(ContinueOnErrorVisitor{r.visitor}, helpers...)
	} else {
		r.visitor = NewDecoratedVisitor(r.visitor, helpers...)
	}
	return r
}
```



那么从外层到内层的调用链如下:

```go
DecoratedVisitor -> ContinueOnErrorVisitor -> RetrieveLazy -> RequireNamespace -> FlattenListVisitor -> Result
```



构造对应的result对象

```go
func (b *Builder) visitorResult() *Result {
	// 如果指定了 -f 参数, 那么最终的result对象在这里创建
	if len(b.paths) != 0 {
		return b.visitByPaths()
	}

	// 基于选择器
	if b.labelSelector != nil || b.fieldSelector != nil {
		return b.visitBySelector()
	}

	// 如果参数是 resource_name/name 比如deployment/nginx
	if len(b.resourceTuples) != 0 {
		return b.visitByResource()
	}

	// 本文中的数据流在这 因为参数是kubectl get deploy, deploy就是那个name
	if len(b.names) != 0 {
		return b.visitByName()
	}
}
```

这个result对象的构造过程比较复杂，我也没完全看懂，等我看懂了在来写吧。



那么继续看看数据在哪里出发吧。

```go
// result的Infos方法可以多次调用，所以这里会判断对象是否已经有获取的结果
func RetrieveLazy(info *Info, err error) error {
	if err != nil {
		return err
	}
	if info.Object == nil {
		return info.Get()
	}
	return nil
}

// 基于构造的client及mapping获取对象解析对象
func (i *Info) Get() (err error) {
	obj, err := NewHelper(i.Client, i.Mapping).Get(i.Namespace, i.Name)
	if err != nil {
		if errors.IsNotFound(err) && len(i.Namespace) > 0 && i.Namespace != metav1.NamespaceDefault && i.Namespace != metav1.NamespaceAll {
			err2 := i.Client.Get().AbsPath("api", "v1", "namespaces", i.Namespace).Do(context.TODO()).Error()
			if err2 != nil && errors.IsNotFound(err2) {
				return err2
			}
		}
		return err
	}
	i.Object = obj
	i.ResourceVersion, _ = metadataAccessor.ResourceVersion(obj)
	return nil
}
```



## 总结

未完待续。。。。
