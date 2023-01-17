# casbin使用指南
无论什么项目只要涉及到多个用户的操作都会开始考虑权限控制, 权限管理是一个很常见部分，所以出现了单独处理这个部分的开源项目，即本文要介绍的casbin项目。

casbin支持很多的编程语言, 本文选择golang作为使用语言。



## 认证还是授权?

在大型项目中认证(Authentication)和授权(Authorization)一般是分开的，前者用于甄别用户是谁, 而后者用于判断用户有什么权限，授权不管认证, 认证也不管授权, 这点很重要, 但是很多时候为了简单会将两者放在一起，比如仅是判断用户是否认证，认证了就可以访问该资源，而本文主要讨论授权的问题,  所以不会关心认证的问题, 即没有验证用户名密码是否认证通过的业务逻辑。



## 准入

权限最开始总是准入，即只有两个选择，允许或者拒绝。

比如这样的场景，存在四个用户，zhangsan, lisi, wangwu, zhaoliu, 我们允许前三人可以访问我们的网站。

所以我们将策略描述如下.

```csv
zhangsan
lisi
wangwu
```

在这个列表中的用户表示允许，反之不允许。



## 资源控制

随着项目的增长我们自然发现用户可以操作的项目多起来了, 所以需要在之前的策略里加上用户对应的资源。

比如这样的场景, 还是之前那四个用户，但是我们的网站变成了2个, 我们允许张三访问两者，后三人只能访问第二个网站。

所以我们将策略描述如下.

```csv
zhangsan, web1
zhangsan, web2
lisi, web2
wangwu, web2
zhaoliu, web2
```

还是一样的逻辑，只是多了一个字段

> 我们可以将第一列称为user，第二列称为website。
>
> 

与此同时，我们还需要对用户有更精细的控制，比如张三可以读写所有网站，但是其他三个人只读第二个网站，所以策略可以描述如下。

```csv
zhangsan, web1, read
zhangsan, web1, write
zhangsan, web2, read
zhangsan, web2, write
lisi, web2, read
wangwu, web2, read
zhaoliu, web2, read
```

> 我们将第三列称为action

至此我们基本上完成了权限控制，但是稍稍有点不完美, 这里的不完美是策略文件跟匹配模型太耦合, 比如我们还是上面的策略文件，但是网站变成了10个，并且我们希望只要在列表中的用户就能访问所有网站，又或者不管第二个字段，只根据第三个字段来判断用户的可读可写权限，最简单直接的办法自然是直接重写一遍策略文件并相应的修改代码，但是太无聊太枯燥了，所以我们需要将其**模型**提炼出来。

比如我们可以定义一个这样的模型

```toml
# 策略定义的意思
[policy_definition]
p = user, website, action

# 匹配逻辑
[matchers]
m = user == p.user && website == website && action == action
```

这样我们就可以解决之前的问题了

比如只匹配第一个字段, 那我们可以定义如下

```toml
# 策略定义的意思
[policy_definition]
p = user, website, action

# 匹配逻辑
[matchers]
m = user == p.user
```

又比如只匹配第一个和第三个字段

```toml
# 策略定义的意思
[policy_definition]
p = user, website, action

# 匹配逻辑
[matchers]
m = user == p.user && action == p.action
```

至此我们可以在不改动策略文件的情况下仅仅改变比较小的内容就可以很快的完成匹配模型的转换，这样就会灵活很多，但是现在的模型还有些不太严谨， 我们通过`p = user, website, action `定义了策略文件的各个字段，却没有定义用户请求的各个字段， 比如要求用户请求应该填上哪些字段，所以我们需要再次改一下我们的匹配模型，修改如下:

```toml
# 请求定义的意思
[request_definition]
r = user, website, action

# 策略定义的意思
[policy_definition]
p = user, website, action

# 匹配逻辑
[matchers]
m = r.user == p.user && r.action == p.action
```

这样子我们的匹配模型看起来要严谨许多了，但是模型中请求定义(request_definition), 策略定义(policy_definition)在toml中的语法其实都是列表, 即我们可以定义多个策略和请求定义，比如:

```toml
# 请求定义的意思
[request_definition]
r = user, website, action
r2 = user, action

# 策略定义的意思
[policy_definition]
p = user, website, action
p2 = user, action

# 匹配逻辑
[matchers]
m = r.user == p.user && r.website == p.website && r.action == p.action
m2 = r2.user == p2.user && r2.action == p2.action
m3 = r.user == p.user && r.action == p.action
```

这样我们可以在一套模型中定义多个不同的组合，比如(r,p,m), (r2,p2,m2), (r,p,m3), 总的来说我们的匹配模型灵活性大大提高，但是我们的策略模型可能出现了不严谨的地方，即策略文件中的每一行是策略p, 还是策略p2? 我们无法判断，所以为了解决这个问题，我们需要在策略文件中多加一个字段.

策略文件定义如下:

```
p, zhangsan, web1, read
p, zhangsan, web1, write
p, zhangsan, web2, read
p, zhangsan, web2, write
p, lisi, web2, read
p, wangwu, web2, read
p, zhaoliu, web2, read
p2, sunqi, read
```

可以看到，我们增加了一个用户sunqi, 他不需要定义website，因为策略p2不需要website这个字段。

现在我们稍稍将名称再提炼一下，假设我们多了程序接口，也就是说使用者不是用户而是终端，我们可以称其为用户，但是稍稍有些别扭，我们可以将其统称为主体(subject)，我们的项目也不可能总是网站，所以我们可以称其为对象(object), 而操作权限我们可以归纳为动作(action).

所以仅仅是为了让我们的模型的语言看起来更加的泛化，所以我们将其改成如下

```toml
# 请求定义的意思
[request_definition]
r = subject, object, action
r2 = subject, action

# 策略定义的意思
[policy_definition]
p = subject, object, action
p2 = subject, action

# 匹配逻辑
[matchers]
m = r.subject == p.subject && r.object == p.object && r.action == p.action
m2 = r2.subject == p2.subject && r2.action == p2.action
m3 = r.subject == p.subject && r.action == p.action
m3 = r.subject == p.subject && r.action == p.action
```

这个时候又来了新的需求，即再多加一个用户(zhouba)，只需要这个用户不能访问web10(假设已经有10个网站。)即可，一种做法是为这个用户添加18条记录，即web1,web2,...,we9,  分别对应read和write, 作为一个程序员自然是讨厌这些枯燥无聊的工作的。

所以我们可以继续改进我们的匹配模型, 我们发现我们的匹配模型对于结果的判断过于单一，即只能允许，我们无法在已有的框架下扩展，这其实是因为我们没有处理匹配的结果，我们应该对匹配的结果进一步做处理，我们可以将匹配的结果称之为result, 而result有允许和拒绝(deny)两种, 在这个结果下，我们可以定义这样的语法，匹配到任意一个允许(allow)就放行，又或者没有任何一个拒绝(deny)就放行，而后者就是我们想要的解决方案，这样我们只要写一条拒绝访问web10的规则就可以达到目的。

所以模型定义如下:

```toml
# 请求定义的意思
[request_definition]
r = subject, object, action
r2 = subject, action

# 策略定义的意思
[policy_definition]
p = subject, object, action
p2 = subject, action
p3 = subject, object, result

# 策略结果的意思
[policy_result]
e = some(where (p.result == allow))
e2 = !some(where (p.result == deny))


# 匹配逻辑
[matchers]
m = r.subject == p.subject && r.object == p.object && r.action == p.action
m2 = r2.subject == p2.subject && r2.action == p2.action
m3 = r.subject == p.subject && r.action == p.action
m3 = r.subject == p.subject && r.action == p.action
m4 = r.subject == p.subject && r.object == p3.object
```

这里我们多定义了一个段落policy_result, 这个段落有两个执行逻辑，前者代表只要有一行的策略匹配结果是allow就放行，后者是没有一行的策略匹配结果是deny就放行。

> 为啥语法要定义成这样? 因为这是casbin的语法, 我只是拙劣的模仿，并且按照自己的理解来一步步推到casbin模型...语法只是一套要记住的规则而已，如果我们不需要自己解析的话，死记硬背即可，当然了，它的这个语法也不是难以理解的那种。

而新的策略规则如下:

```csv
p, zhangsan, web1, read
p, zhangsan, web1, write
p, zhangsan, web2, read
p, zhangsan, web2, write
p, lisi, web2, read
p, wangwu, web2, read
p, zhaoliu, web2, read
p2, sunqi, read
p3, sunqi, web10, deny
```

至此整个模型基本完成了，可以适配大多数的访问控制(ACL)情况了，但是对于RBAC还是有些问题，但是这里就不继续演进了。后面通过代码来看看ACL, RBAC的是用。

当然了，你可能觉得模型的演进还是有很多问题，比如casbin使用的是简写sub，而这里使用的是subject全称，这里策略效果写的段落名是policy_result，而casbin写的是policy_effect, 不过这些不同之处在我看来只是小问题，只需替换即可。



## 代码示例

这一节直接使用golang来演示。



## ACL

假设场景: 存在网站web1，web2， 张三可读写两者，李四只读web1。

模型定义如下:

```toml
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
```

策略定义如下:

```csv
p, zhangsan, web1, read
p, zhangsan, web1, read
p, zhangsan, web2, read
p, zhangsan, web2, write
p, lisi, web1, read
```

代码如下:

```go
package acl1

import (
	"log"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/casbin/casbin/v2"
)

func TestACL1(t *testing.T) {
	e, err := casbin.NewEnforcer("model.conf", "policy.csv")
	if err != nil {
		log.Fatal("创建策略引擎失败: ", err)
	}
	tests := [][]interface{}{
		{"zhangsan", "web1", "read"},
		{"zhangsan", "web1", "write"},
		{"zhangsan", "web2", "read"},
		{"zhangsan", "web2", "write"},
		{"zhangsan", "webx", "write"},
		{"lisi", "web1", "read"},
		{"lisi", "web2", "read"},
		{"lisi", "webx", "read"},
	}
	expected := []bool{true, true, true, true, false, true, false, false}

	for i := 0; i < len(tests); i++ {
		ok, err := e.Enforce(tests[i]...)
		if err != nil {
			t.Fatalf("请求: %v 对应的期待是是: %t, 发生错误: %s", tests[i], expected[i], err)
		}
		assert.Equal(t, expected[i], ok)
	}
}

```

在此基础上我们需要一个超级管理员，就称其为root

所以模型如下:

```toml
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
# 唯一的不同是是加了|| p.sub == "root", 只要用户名是root就允许
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act || p.sub == "root"
```

策略文件不变。

测试代码如下

```go
package acl1

import (
	"fmt"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/casbin/casbin/v2"
)

func TestACL2(t *testing.T) {
	e, err := casbin.NewEnforcer("model.conf", "policy.csv")
	if err != nil {
		log.Fatal("创建策略引擎失败: ", err)
	}
	tests := [][]interface{}{
		{"zhangsan", "web1", "read"},
		{"zhangsan", "web1", "write"},
		{"zhangsan", "web2", "read"},
		{"zhangsan", "web2", "write"},
		{"zhangsan", "webx", "write"},
		{"lisi", "web1", "read"},
		{"lisi", "web2", "read"},
		{"lisi", "webx", "read"},
		{"root", "web1", "read"},
		{"root", "webx", "update"},
	}
	expected := []bool{true, true, true, true, false, true, false, false, true, true}

	for i := 0; i < len(tests); i++ {
		ok, err := e.Enforce(tests[i]...)
		fmt.Println(tests[i], expected[i])
		if err != nil {
			t.Fatalf("请求: %v 对应的期待是是: %t, 发生错误: %s", tests[i], expected[i], err)
		}
		assert.Equal(t, expected[i], ok)
	}
}
```

测试结果也是通过的，可以看到root的测试用例中即使请求不存在的资源或者不存在的操作也是true, 因为模型中只判断用户是否为root。



## RBAC

假设场景:   存在网站web1，web2， 可读角色(reader)可读写两个web，可读角色(writer)可写两个web，管理员角色(admin)可读写两者, 张三属于可读角色，李四属于可写角色，王五属于admin角色，赵六既属于可读角色也属于可写角色。

模型描述如下:

```go
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

RBAC与ACL的不同之处在于多了一个role_definition, 多了一层抽象自然需要一个新的定义，这没什么奇怪的，就像request_definition, policy_definition.  不过它的语法又稍稍不同，首先它不用sub, obj之类的对象名称，仅用"_"作为所需参数的占位符， 两个下划线说明需要两个参数。

比较难以理解的是`g(r.sub, p.sub)`, g是role_definition定义的一个角色操作符,  但是这个需要对照策略文件查看。

策略文件如下:

```csv
# 策略定义
p, reader, web1, read
p, reader, web2, read
p, writer, web1, write
p, writer, web2, write
p, admin, web1, read
p, admin, web1, write
p, admin, web2, read
p, admin, web2, write
# 定义用户属于哪些角色
g, zhangsan, reader
g, lisi, writer
g, wangwu, admin
g, zhaoliu, reader
g, zhaoliu, writer
```

策略文件中分为两个部分，第一部分属于常见策略定义，不过这里定义的主体(sub)是后面定义的角色，即角色绑定到了具体的对象及操作，而g定义了用户属于哪些角色，比如`g, zhangsan, reader`代表zhangsan属于可读角色(reader)，而可读角色(reader)可以读写web1, web2, 从来可以推导出zhangsan可读web1，web2。

在回过头看`g(r.sub, p.sub)`我们可以理解为g操作符将`r.sub`映射成了对应的角色，再将其角色与`p.sub`比较。因为请求中没有角色的数据，所以必然需要一个映射函数将其转换成对应的角色，casbin使用的角色定义的**g**。



测试代码如下:

```go
package acl1

import (
	"fmt"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/casbin/casbin/v2"
)

func TestRBAC(t *testing.T) {
	e, err := casbin.NewEnforcer("model.conf", "policy.csv")
	if err != nil {
		log.Fatal("创建策略引擎失败: ", err)
	}
	tests := [][]interface{}{
		{"zhangsan", "web1", "read", true},
		{"zhangsan", "web2", "read", true},
		{"zhangsan", "web1", "write", false},
		{"lisi", "web1", "write", true},
		{"lisi", "web2", "write", true},
		{"lisi", "web1", "read", false},
		{"wangwu", "web1", "read", true},
		{"wangwu", "web1", "read", true},
		{"zhaoliu", "web1", "read", true},
		{"zhaoliu", "web2", "write", true},
	}

	for i := 0; i < len(tests); i++ {
		ok, err := e.Enforce(tests[i][:3]...)
		fmt.Println(tests[i], tests[i][3])
		if err != nil {
			t.Fatalf("请求: %v 对应的期待是是: %t, 发生错误: %s", tests[i], tests[i][3], err)
		}
		assert.Equal(t, tests[i][3], ok)
	}
}
```

测试自然是成功的。

> 值得注意的是: 虽然策略里面定义了角色的权限，但是也可以定义用户的权限，比如加一行`p, zhangsan, web1, write`, 可也是可以的，但是初学起来觉得奇怪。熟悉之后可以任意的测试和组合。



## 上下文切换

在之前的模型推导过程中，模型总是定义了不止一个策略，不止一个匹配器，那么怎么在代码中体现呢?

模型定义如下:

```toml
[request_definition]
r = sub, obj, act
r2 = sub, obj

[policy_definition]
p = sub, obj, act
p2 = sub, obj

[policy_effect]
e = some(where (p.eft == allow))
e2 = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
m2 = r2.sub == p2.sub && r2.obj == p2.obj
```

会发现每个对象都多了一份, 比如r2的定义说明只需要两个参数，而r需要三个参数，其他意思差不多。



策略定义如下:

```csv
# 策略定义
p, zhangsan, web1, read
p, zhangsan, web2, read
p2, wangwu, web1
p2, wangwu, web2
```

分别为策略p, p2定义不同的策略，需要的参数不同



测试代码如下:

```go
package acl1

import (
	"log"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/casbin/casbin/v2"
)

func TestRBAC(t *testing.T) {
	e, err := casbin.NewEnforcer("model.conf", "policy.csv")
	if err != nil {
		log.Fatal("创建策略引擎失败: ", err)
	}
	tests1 := [][]interface{}{
		{"zhangsan", "web1", "read", true},
		{"zhangsan", "web2", "read", true},
		{"zhangsan", "web1", "write", false},
		{"wangwu", "web1", "write", false},
		{"wangwu", "web2", "write", false},
	}

	ctx2 := casbin.NewEnforceContext("2")

	tests2 := [][]interface{}{
		{ctx2, "wangwu", "web1", true},
		{ctx2, "wangwu", "web2", true},
		{ctx2, "wangwu", "web3", false},
	}

	for i := 0; i < len(tests1); i++ {
		ok, err := e.Enforce(tests1[i][:3]...)
		// t.Log(tests1[i], tests1[i][3])
		if err != nil {
			t.Fatalf("请求: %v 对应的期待是是: %t, 发生错误: %s", tests1[i], tests1[i][3], err)
		}
		assert.Equal(t, tests1[i][3], ok)
	}

	for i := 0; i < len(tests2); i++ {
		ok, err := e.Enforce(tests2[i][:3]...)
		// t.Log(tests2[i], tests2[i][3])
		if err != nil {
			t.Fatalf("请求: %v 对应的期待是是: %t, 发生错误: %s", tests2[i], tests2[i][3], err)
		}
		assert.Equal(t, tests2[i][3], ok)
	}
}

```

这与之前的不同在于第一个参数是context，这里为了简单没有单独的设置各个部分的值，比如这里的`casbin.NewEnforceContext("2")`说明使用(r2,p2,e2,m2), 但是e2跟e分明是一样的，所以可以单独设置context的EType为**“e”**,   这里就不展开了。。。



## 一些额外的技巧

一些常使用的技巧



### 黑名单策略

本文全篇都是白名单策略，即允许才放行，但是有时候很名单更有效，比如网站的反爬策略，大多数链接都是允许的，只有一部分是不允许的, 所以用白名单去放行所有资源显然有点不现实及不高效，所以我们可以将策略结果进行如下设置

```toml
[policy_effect]
e = !some(where (p.eft == deny))
```

该语法声明的是，不存在任何决策结果为`deny`的匹配规则，则最终决策结果为`allow`

但是什么时候`p.eft == deny `呢?  其实策略定义中可配置eft这个属性，定义如下

```toml
[policy_definition]
p = sub, obj, act, eft
```

然后对应的策略定义如下:

```csv
p, zhangsan, web1, read, allow
p, zhangsan, web2, read, deny
```



### 数据源适配

一般来说模型文件是放在本地，并且很少更改，而策略文件可以放在很多地方，比如数据库，代码如下。

```go
import (
    "log"

    "github.com/casbin/casbin/v2"
    "github.com/casbin/casbin/v2/model"
    xormadapter "github.com/casbin/xorm-adapter/v2"
    _ "github.com/go-sql-driver/mysql"
)

// 使用MySQL数据库初始化一个Xorm适配器
a, err := xormadapter.NewAdapter("mysql", "mysql_username:mysql_password@tcp(127.0.0.1:3306)/casbin")
if err != nil {
    log.Fatalf("error: adapter: %s", err)
}

m, err := model.NewModelFromString(`
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
`)
if err != nil {
    log.Fatalf("error: model: %s", err)
}

e, err := casbin.NewEnforcer(m, a)
if err != nil {
    log.Fatalf("error: enforcer: %s", err)
}
```

> 代码摘自: https://casbin.org/zh/docs/get-started





## casbin编辑器

在线地址: https://casbin.org/zh/editor

在线编辑器虽然可以很方便的验证想法，但是使用稍稍有些限制，只不过对于大多数人不是问题，因为不需要上下文切换。



## 总结

自己写一个ACL或者RBAC倒是不太复杂，但是枯燥无味就像写CRUD一样并且不够灵活，而Casbin是比较强大的，它支持超级多的模型，ACL, RBAC, ABAC等多种策略模型。





