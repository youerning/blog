# python命令行typer 快速入门教程
typer的作者与著名项目FastAPI是同一个作者，作者擅长在已有库的基础上大幅度的提升用户体验，typer自然也不例外,  因为作者也大力提倡python的类型标注，所以typer的使用在Python 3.6+才能获得最佳体验。

> 类型标注很棒的一个点在于编程的时候有方法补全即类型验证。

在学习`typer`之前我们应该先了解一下命令行下的参数类型，typer将命令行参数分为了两类，一类叫做Argument(位置参数), 一类叫做Options(可选参数)。

以下面的命令为例

```sh
ls -l -a -h --color=auto /tmp  /var/log
```

上面的命令可以分为三个部分, `ls`, `-l -a -h`, `/tmp /var/log`, 第一部分是可执行文件名, 第而部分是Options(可选参数), 第三部分是Arguments(位置参数)。

如果你使用linux命令足够多，你会注意到Options(可选参数)不都是上述说明的那样，比如下面的命令

```sh
ls -l -a -h --color=auto /tmp  /var/log
```

可以看到上面的命令多了`--color=auto`这样的Options。



总的来说在这两类参数中，Options(可选参数)总是以一个或多个`-`(横线)开头, 而命令行参数一般不以`-`(横线)开头。

> 但，事情总有意外, 比如linux的很多命令接受参数`-`(横线), 表示读取标准输出, 这个参数说实话，还真不好分类，个人倾向于分为Arguments(命令行参数)。



## 快速入门

推荐安装一个全功能的`typer`, 这样可以获得最棒的体验。

```python
pip install "typer[all]"
```



一个官方的例子

```python
import typer


def main(name: str):
    print(f"Hello {name}")


if __name__ == "__main__":
    typer.run(main)
```



不传参的情况

```sh
python simple.py
# 输出如下
Usage: simple.py [OPTIONS] NAME
Try 'simple.py --help' for help.

Error: Missing argument 'NAME'.
```

提示缺少参数`NAME`



传参的情况下

```sh
python simple.py world
# 输出如下
Hello world
```

可以看到输出正常了，那么为什么呢?



就像FastAPI一样，作者极大的减少了显式的标注参数及其类型(相对于click而言)， 上面简单的例子，我们并不需要像使用 [Click](https://click.palletsprojects.com/en/8.1.x/) 一样通过显示的标注参数类型(比如`@click.argument('name')`)，因为typer按照约定将参数分类了，这样我可以减少很多烦人的标注代码，更多的专注于自己的业务。



默认情况下python的命令行参数会被转化成Arguments(位置参数), 而可选参数会转化成Options(可选参数)。以下面代码为例

```python
import typer


def main(name: str, age: int = 18):
    print(f"Hello {name}, your age is {age}")


if __name__ == "__main__":
    typer.run(main)
```

下面是使用及输出

```sh
python simple2.py zhangsan .
# 不设置options，则使用默认参数
Hello zhangsan, your age is 18

python simple2.py zhangsan --age=188
# 手动设置options, 则覆盖默认参数
Hello zhangsan, your age is 188
```

并且我们也可以看看typer帮我们生成的帮助文档

```sh
python simple2.py --help
Usage: simple2.py [OPTIONS] NAME

Arguments:
  NAME  [required]

Options:
  --age INTEGER         [default: 18]
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or
                        customize the installation.

  --help                Show this message and exit.
```

非常棒，不是吗? 这个命令行的内容几乎和一个正常的脚本相同，唯一的不同是引入了typer并调用了它的`typer.run`方法，仅仅增加两行代码，就得到了一个看起来像模像样的命令行程序了。

> 注意: 如果age参数传一个字符串会报错，这是因为我们类型标注了age的类型是int!!!



## Arguments(命令行参数)

仅仅通过将python的语法按照约定转换成参数自然是很方便的，不过为了更多的控制，显然需要更复杂的类型标注，所以我们需要显示的设置`Arguments`的各个值。既然也要显式的标注，那这和`Click`有啥区别? 个人觉得typer更符合直觉(当然了, 这是比较主观的看法).

下面看看`Arguments`各方面的常用配置。

**设置默认值**

```python
def main(name: str = typer.Argument("Wade Wilson")):
    print(f"Hello {name}")
```

**设置提示文字**

```python
def main(name: str = typer.Argument(..., help="The name of the user to greet")):
    print(f"Hello {name}")
```

**读取环境变量**

```python
def main(name: str = typer.Argument("World", envvar="AWESOME_NAME")):
    print(f"Hello Mr. {name}")
```



## Options(可选参数)

像`Arguments`一样, Options也有各种选项。

**标记可选参数必须设置**

```python
def main(name: str, lastname: Annotated[str, typer.Option()]):
    print(f"Hello {name} {lastname}")
```



**如果参数没有设置，会提示**

```python
def main(name: str, lastname: str = typer.Option(..., prompt=True)):
    print(f"Hello {name} {lastname}")
```



**重复确认**

```python
def main(
    name: str, email: str = typer.Option(..., prompt=True, confirmation_prompt=True)
):
    print(f"Hello {name}, your email is {email}")
```



**密码字段隐藏**

```python
def main(
    name: str,
    password: str = typer.Option(
        ..., prompt=True, confirmation_prompt=True, hide_input=True
    ),
):
    print(f"Hello {name}. Doing something very secure with password.")
    print(f"...just kidding, here it is, very insecure: {password}")
```



## Command(子命令)

除非极其简单的命令，不然一般会有多个子命令，所以支持子命令是一个理所当然的事情，示例代码如下

```python
import typer

app = typer.Typer()


@app.command()
def create(item: str):
    print(f"Creating item: {item}")


@app.command()
def delete(item: str):
    print(f"Deleting item: {item}")


@app.command()
def sell(item: str):
    print(f"Selling item: {item}")


if __name__ == "__main__":
    app()
```

如果我们查看帮助文档会有以下提示

```sh
python cm.py --help
Usage: cm.py [OPTIONS] COMMAND [ARGS]...

Options:
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or
                        customize the installation.

  --help                Show this message and exit.

Commands:
  create
  delete
  sell
```

每个子命令的参数也可像上面没有使用`@app.command()`装饰器一样那样类型标注。



## 总结

如果你习惯了使用python的类型标注，那么写起typer来还是比较轻松自然的，如果还不习惯python的类型标注就去尝试一下`FastAPI`这个非常棒的python web框架吧, 在深入使用之后你会爱上python的类型标注的。

更多参数及配置参考官方文档[Typer](https://typer.tiangolo.com/)


