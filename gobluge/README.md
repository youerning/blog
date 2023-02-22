# 使用golang和bluge打造自己的全文搜索引擎

全文搜索引擎有许多，其中最出名的是elasticsearch, 无论是性能还是体验都是最顶尖的，但是对小应用来不友好，因为小应用的硬件资源比较少，所以能够通过库/模块的方式内置在应用中会是比较好的选择，就像sqlite3一样。

鉴于此，本文选择bluge，一个go语言的全文搜索库

> bluge还有一个历史版本bleve, 如果搜索bluge相关问题找不到的话，可以搜索bleve, 不过两者的接口还是会有些不同的，需要手动适配。



其他全文搜索数据库:

- typesense
- melisearch
- redissearch

> 本文总会粘贴完整的代码，是为了大家复制方便，也为了我自己以后复制代码方便^_^



## 一些必要的前置知识

假设有以下文本, 每行是一篇文章

```txt
文章1 hello world
文章2 hello china
文章3 hello hunan
```

如果我们要搜素那篇文章包含`hello`, 我们可以遍历每篇文章然后依次搜索，很显然这是一个比较低效的做法，如果有10w篇文章，每次搜索都遍历10w遍，那肯定是无法接受的，所以有人提出了倒排索引。



### 倒排索引

还是上面的文本, 我们可以建立一个map, 用来存储上面的文本, 效果如下

```go
index := map[string][]string{
		"hello": []string{"文章1", "文章2", "文章3"},
		"world": []string{"文章1"},
		"china": []string{"文章2"},
		"hunan": []string{"文章3"},
	}
```

基于上面的数据结构我们再次搜索`hello`可以很快的发现`"文章1", "文章2", "文章3"`三篇文章都包含该关键词, 即使是10w篇文章，我们也能很快的找到对应的文章。

这里有一个小问题,  hello world可以通过空格的方式来将其分成一个个单词, 那么中文呢? `你好世界`肯定不应该变成`"你", "好", "世", "界"`. 这个问题的答案叫做**分词**，后续文章在详细说明。



### 小结

上面只是简单的介绍一下倒排索引的基本原理, 具体的实现肯定要复杂一些。





## 简陋的hello world

全文搜索引擎总结起来就两个功能, 创建索引, 搜索，首先来两个简单的示例预览一下效果，也引入一些问题并在后续文章中解决。

### 创建索引

```go
package main

import (
	"log"

	"github.com/blugelabs/bluge"
)

func main() {
	lines := []string{
		"hello world",
		"hello china",
		"hello hunan",
	}
	indexPath := "helloworld"
	writer, err := bluge.OpenWriter(bluge.DefaultConfig(indexPath))
	panicErr("创建索引文件失败,", err)
	defer func() {
		err := writer.Close()
		if err != nil {
			log.Fatal("关闭writer失败")
		}
	}()

	batch := bluge.NewBatch()
	for _, line := range lines {
		doc := bluge.NewDocument(line)
		doc.AddField(bluge.NewTextField("content", line))
		batch.Update(doc.ID(), doc)
	}

	err = writer.Batch(batch)
	panicErr("批量插入失败, ", err)
}

func panicErr(s string, err error) {
	if err != nil {
		log.Fatal(s, err)
	}
}
```

通过运行上面的代码，如果没有报错的话，会在工作目录新建一个`helloworld`的目录, 里面会存在若干的文件，那是bluge的索引文件。



### 搜索

```go
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/blugelabs/bluge"
)

func main() {
	var err error
	indexPath := "helloworld"
	writer, err := bluge.OpenWriter(bluge.DefaultConfig(indexPath))
	panicErr("创建索引文件失败,", err)
	defer func() {
		err := writer.Close()
		if err != nil {
			log.Fatal("关闭writer失败")
		}
	}()

	reader, err := writer.Reader()
	panicErr("获取reader对象失败,", err)
	query := bluge.NewMatchQuery("hello").SetField("content")
	request := bluge.NewTopNSearch(10, query)
	ctx := context.TODO()
	dmi, err := reader.Search(ctx, request)
	panicErr("搜索失败,", err)
	dm, err := dmi.Next()
	panicErr("迭代数据失败", err)
	for dm != nil && err == nil {
		dm.VisitStoredFields(func(field string, value []byte) bool {
			fmt.Printf("%s => %s\n", field, value)
			return true
		})
		dm, err = dmi.Next()
	}
	panicErr("迭代数据过程中失败", err)

}

func panicErr(s string, err error) {
	if err != nil {
		log.Fatal(s, err)
	}
}
```

输出结果如下:

```shell
_id => hello world
_id => hello china
_id => hello hunan
```

如果你眼尖的话会发现，只有`_id`字段! content字段呢? 按照预期应该是有两个字段, `_id`, `content`。但是现实狠狠的打脸了，之所以这样，是因为我们只索引了这个字段而没有存储这个字段。

在前文我们提到，倒排索引可以提升搜索速度, 做法是将文本**分词**, 然后建立一个映射的数据结构(**倒排索引**)用于检索数据, 如果文本被分词了，我们还会存储**分词**前的文本么? bluge的默认选择是不存储, 所以想要将字段存储在索引里面，需要显示的说明。

只需在建立索引的时候将`doc.AddField(bluge.NewTextField("content", line))`改成`doc.AddField(bluge.NewTextField("content", line).StoreValue())`即可。

重新建立索引后在搜索，结果如下。

```shell
_id => hello world
content => hello world
_id => hello china
content => hello china
_id => hello hunan
content => hello hunan
```



### 小结

bluge默认只保存`_id`字段, 其他字段要想在搜索结果中可以获取，需要显式的设置。



## 中文分词

bluge是外国人写的, 支持英文很正常，但是我们要存储的肯定是中文，所以需要自己分词。

首先看看bluge自带的分词方法。

```go
package main

import (
	"fmt"

	"github.com/blugelabs/bluge/analysis/analyzer"
)

func main() {
	lines := []string{
		"hello world",
		"你好世界",
	}

	a := analyzer.NewStandardAnalyzer()
	for _, line := range lines {
		fmt.Println("line: ", line)
		tokens := a.Tokenizer.Tokenize([]byte(line))
		for _, token := range tokens {
			fmt.Println(string(token.Term))
		}
		fmt.Println("============")
	}
}
```

输出如下:

```shell
line:  hello world
hello
world
============
line:  你好世界
你
好
世
界
============
```

直接使用自带的分词不是不可以用，只是不够精确，假设我们搜索`你好`, 搜索的内容会首先被**分词**，变成`"你" "好"`两个字段, 那么文章里面包含了两者的内容会被搜索出来，比如`好的, 鸡你太美`, 这样的内容也会被判断为符合条件, 因为这句话里面分别有**你**, **好**两个词，但是按照我们的预期，应该是搜索包含`你好`这样的一个词语而非两个字段。

为了解决这个问题，我们需要使用额外的分词模块.比较出名的有gojieba, 但是windows下编译C源码不是太方便，这里就使用一个纯Go写的分词模块(github.com/huichen/sego).



使用如下:

```go
package main

import (
	"fmt"

	"github.com/huichen/sego"
)

func main() {
	// 载入词典
	var segmenter sego.Segmenter
	// dictionary.txt可以去https://github.com/huichen/sego/blob/master/data/dictionary.txt下载到本地
	segmenter.LoadDictionary("dictionary.txt")

	// 分词
	text := []byte("你好世界")
	segments := segmenter.Segment(text)
	// 处理分词结果
	fmt.Println(sego.SegmentsToSlice(segments, false))
}

```

输出如下:

```shell
2023/02/21 18:04:39 载入sego词典 dictionary.txt
2023/02/21 18:04:40 sego词典载入完毕
[你好 世界]
```



### 小结

为了符合中文习惯，我们需要支持中文分词。



## 一个实际例子

使用中文分词的代码

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"

	"github.com/blugelabs/bluge"
	"github.com/blugelabs/bluge/analysis"
	"github.com/huichen/sego"
)

const dataPath = "news"

var chineseTokenizer *SegoAnalyzer

var news = []string{"二十届二中全会2月26日至28日召开",
	"拜登波兰演讲：提了10次普京的名字",
	"网友呼吁接回旅美大熊猫丫丫",
	"出政策抓项目 夺取“开门红”",
	"“芳香型”贪官:花84万在单位装香氛",
	"长沙凌晨1点马路人流量惊人",
	"美国工厂“两班倒”疯狂生产炮弹",
	"座位被占女子爬火车行李架睡觉",
	"拜登宣布美国将主办明年北约峰会",
	"60岁分拣工不属于劳动者？网友炸锅",
	"周杰伦演唱会",
	"美国再发生重大火车脱轨事故",
	"章子怡担任中戏表演系考官",
	"女儿考研437分喜极而泣 母亲哽咽",
	"智障男子因身揣逃犯身份证坐牢9年",
	"女子拒接反诈电话被骗122万",
	"女子卖气球城管要没收 当场全放飞",
	"普京：整个地球都点缀着美军基地",
	"“试管婴儿放错胚胎”事件初步和解",
	"普京：在战场上战胜俄罗斯不可能",
	"女子试戴金戒指断两半遭索赔",
	"女子连刷10个差评商家找上门怒怼",
	"林志颖问谁还记得《放羊的星星》",
	"武契奇：坚持不对俄实施制裁",
	"俞敏洪说想给董宇辉在北京买房子",
	"发3000元收回2800元 慈善主播被行拘",
	"网传苏州有游艇女仆party？警方回应",
	"音悦台将回归",
	"北大方正集团财务公司进入破产程序",
	"全球第5位艾滋病治愈者出现",
	"泽连斯基站在拜登身后悄悄抹泪",
	"拜拜, 登登",
}

func index(writer *bluge.Writer, lines []string) error {
	batch := bluge.NewBatch()
	for i, line := range lines {
		doc := bluge.NewDocument(fmt.Sprintf("%d", i))
		// 不指定Analyzer的话会使用默认的Analyzer
		doc.AddField(bluge.NewTextField("content", line).StoreValue().WithAnalyzer(chineseTokenizer))
		batch.Update(doc.ID(), doc)
	}
	return writer.Batch(batch)
}

func newWriter(config bluge.Config) (*bluge.Writer, error) {
	return bluge.OpenWriter(config)
}

func main() {
	var err error
	var writer *bluge.Writer
	config := bluge.DefaultConfig(dataPath)

	var segmenter sego.Segmenter
	segmenter.LoadDictionary("dictionary.txt")
	chineseTokenizer = &SegoAnalyzer{core: segmenter}
	// 之所以不直接替代DefaultSearchAnalyzer是因为默认的Analyzer还有一个filters
	config.DefaultSearchAnalyzer.Tokenizer = chineseTokenizer
	// 每次创建query并设置搜索的字段很没意思
	config.DefaultSearchField = "content"

	if !fileExist(dataPath) {
		writer, err = newWriter(config)
		panicErr("创建索引文件失败,", err)
		err = index(writer, news)
		panicErr("创建索引失败,", err)
		// 刷新数据到磁盘
		err = writer.Close()
		panicErr("保存writer失败", err)
		writer = nil
	}
	if writer == nil {
		writer, err = newWriter(config)
		panicErr("创建索引文件失败,", err)
	}

	defer func() {
		err = writer.Close()
		panicErr("保存writer失败", err)
	}()

	reader, err := writer.Reader()
	panicErr("获取reader对象失败", err)
	query := bluge.NewMatchQuery("拜登")
	request := bluge.NewTopNSearch(10, query)
	// request := bluge.NewAllMatches(query)

	dmi, err := reader.Search(context.TODO(), request)
	panicErr("搜索请求失败, ", err)
	dm, err := dmi.Next()
	for dm != nil && err == nil {
		dm.VisitStoredFields(func(field string, value []byte) bool {
			if field == "_id" {
				return true
			}
			fmt.Printf("%s => %s\n", field, value)
			return true
		})
		dm, err = dmi.Next()
	}
	panicErr("迭代数据过程中失败", err)

}

func panicErr(msg string, err error) {
	if err != nil {
		log.Fatal(msg, err)
	}
}

func fileExist(path string) bool {
	_, err := os.Stat(path)
	return !errors.Is(err, os.ErrNotExist)
}

type SegoAnalyzer struct {
	core sego.Segmenter
}

func (s *SegoAnalyzer) Tokenize(input []byte) analysis.TokenStream {
	tokens := analysis.TokenStream{}
	words := s.core.Segment(input)
	for _, word := range words {
		tokens = append(tokens, &analysis.Token{
			Start:        word.Start(),
			End:          word.End(),
			Term:         []byte(word.Token().Text()),
			KeyWord:      true,
			PositionIncr: 1,
		})
	}

	return tokens
}

func (s *SegoAnalyzer) Analyze(input []byte) analysis.TokenStream {
	tokens := analysis.TokenStream{}
	words := s.core.Segment(input)
	for _, word := range words {
		tokens = append(tokens, &analysis.Token{
			Start:        word.Start(),
			End:          word.End(),
			Term:         []byte(word.Token().Text()),
			KeyWord:      true,
			PositionIncr: 1,
		})
	}

	return tokens
}
```

输出结果如下:

```shell
2023/02/22 11:11:58 载入sego词典 dictionary.txt
2023/02/22 11:11:59 sego词典载入完毕
content => 拜登宣布美国将主办明年北约峰会 1.586332
content => 泽连斯基站在拜登身后悄悄抹泪 1.586332
content => 拜登波兰演讲：提了10次普京的名字 1.381888
```

不使用中文分词的代码:

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"

	"github.com/blugelabs/bluge"
)

const dataPath = "news2"

var news = []string{"二十届二中全会2月26日至28日召开",
	"拜登波兰演讲：提了10次普京的名字",
	"网友呼吁接回旅美大熊猫丫丫",
	"出政策抓项目 夺取“开门红”",
	"“芳香型”贪官:花84万在单位装香氛",
	"长沙凌晨1点马路人流量惊人",
	"美国工厂“两班倒”疯狂生产炮弹",
	"座位被占女子爬火车行李架睡觉",
	"拜登宣布美国将主办明年北约峰会",
	"60岁分拣工不属于劳动者？网友炸锅",
	"周杰伦演唱会",
	"美国再发生重大火车脱轨事故",
	"章子怡担任中戏表演系考官",
	"女儿考研437分喜极而泣 母亲哽咽",
	"智障男子因身揣逃犯身份证坐牢9年",
	"女子拒接反诈电话被骗122万",
	"女子卖气球城管要没收 当场全放飞",
	"普京：整个地球都点缀着美军基地",
	"“试管婴儿放错胚胎”事件初步和解",
	"普京：在战场上战胜俄罗斯不可能",
	"女子试戴金戒指断两半遭索赔",
	"女子连刷10个差评商家找上门怒怼",
	"林志颖问谁还记得《放羊的星星》",
	"武契奇：坚持不对俄实施制裁",
	"俞敏洪说想给董宇辉在北京买房子",
	"发3000元收回2800元 慈善主播被行拘",
	"网传苏州有游艇女仆party？警方回应",
	"音悦台将回归",
	"北大方正集团财务公司进入破产程序",
	"全球第5位艾滋病治愈者出现",
	"泽连斯基站在拜登身后悄悄抹泪",
	"拜拜, 登登",
}

func init() {
	if fileExist(dataPath) {
		return
	}

}

func index(writer *bluge.Writer, lines []string) error {
	batch := bluge.NewBatch()
	for i, line := range lines {
		doc := bluge.NewDocument(fmt.Sprintf("%d", i))
		doc.AddField(bluge.NewTextField("content", line).StoreValue())
		batch.Update(doc.ID(), doc)
	}
	return writer.Batch(batch)
}

func newWriter(config bluge.Config) (*bluge.Writer, error) {
	return bluge.OpenWriter(config)
}

func main() {
	var err error
	var writer *bluge.Writer
	config := bluge.DefaultConfig(dataPath)
	// 每次创建query并设置搜索的字段很没意思
	config.DefaultSearchField = "content"

	if !fileExist(dataPath) {
		writer, err = newWriter(config)
		panicErr("创建索引文件失败,", err)
		err = index(writer, news)
		panicErr("创建索引失败,", err)
		// 刷新数据到磁盘
		err = writer.Close()
		panicErr("保存writer失败", err)
		writer = nil
	}
	if writer == nil {
		writer, err = newWriter(config)
		panicErr("创建索引文件失败,", err)
	}

	reader, err := writer.Reader()
	panicErr("获取reader对象失败", err)
	query := bluge.NewMatchQuery("拜登")
	request := bluge.NewTopNSearch(10, query)

	dmi, err := reader.Search(context.TODO(), request)
	panicErr("搜索请求失败, ", err)
	dm, err := dmi.Next()
	for dm != nil && err == nil {
		dm.VisitStoredFields(func(field string, value []byte) bool {
			if field == "_id" {
				return true
			}
			fmt.Printf("%s => %s %f\n", field, value, dm.Score)
			return true
		})
		dm, err = dmi.Next()
	}
	panicErr("迭代数据过程中失败", err)

}

func panicErr(msg string, err error) {
	if err != nil {
		log.Fatal(msg, err)
	}
}

func fileExist(path string) bool {
	_, err := os.Stat(path)
	return !errors.Is(err, os.ErrNotExist)
}

```

输出结果如下:

```shell
content => 拜拜, 登登 5.235475
content => 泽连斯基站在拜登身后悄悄抹泪 2.977241
content => 拜登波兰演讲：提了10次普京的名字 2.889334
content => 拜登宣布美国将主办明年北约峰会 2.889334
```

可以发现，不使用中文分词会搜索到不符合预期的结果，而且结果的打分还比预期的搜索结果高，这是因为**拜登**出现了**两次** , 即使是分开的。





## 后记

不过bluge的资料实在少的可怜，本文也只是简单的介绍了全文搜索功能, 即只使用了文本字段(TextField)，除了文本字段，还有数字，geo，时间类型的数据可以索引, 除此之外还有丰富的聚合操作，总得来说还是一应俱全的，但是发展需要时间。

如果对bluge的使用有问题，可以看看zinc的源代码, 抄zinc的代码是个不错的选择。

最后在说一个小技巧: 如果是嵌套的数据结构怎么处理? 将其扁平化。具体可抄zinc。
