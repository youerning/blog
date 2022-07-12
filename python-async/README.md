# Python异步编程全攻略

如果你厌倦了多线程，不妨试试python的异步编程，在引入async, await关键字之后语法变得更加简洁和直观，又经过几年的生态发展，现在是一个很不错的并发模型。

下面介绍一下python异步编程的方方面面。

> 在python异步编程中，可能出现很多其他的对象，比如Future, Task, 后者继承自前者，但是为了统一，无论是Future还是Task，本文中统一称呼为协程。



## 与多线程的比较

因为GIL的存在，所以Python的多线程在CPU密集的任务下显得无力，但是对于IO密集的任务，多线程还是足以发挥多线程的优势的，而异步也是为了应对IO密集的任务，所以两者是一个可以相互替代的方案，因为设计的不同，理论上异步要比多线程快，因为异步的花销更少, 因为不需要额外系统申请额外的内存，而线程的创建跟系统有关，需要分配一定量的内存，一般是几兆，比如linux默认是8MB。



虽然异步很好，比如可以使用更少的内存，比如更好的控制并发(也许你并不这么认为:))。但是由于async/await 语法的存在导致与之前的语法有些割裂，所以需要适配，需要付出额外的努力，再者就是生态远远没有同步编程强大，比如很多库还不支持异步，所以你需要一些额外的适配。



## 用于测试的web服务

为了不给其他网站带来困扰，这里首先在自己电脑启动web服务用于测试，代码很简单。

```python
# web.py
import asyncio
from random import random

import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def index():
    await asyncio.sleep(1)
    return {"msg": "ok"}


@app.get("/random")
async def index():
    await asyncio.sleep(1)
    return {"msg": random()}


if __name__ == "__main__":
    # uvicorn.run(app)
    # 如果需要热加载(reload), 需要传入一个字符串而不是application对象
    uvicorn.run("web:app", reload=True)import asyncio

import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def index():
    await asyncio.sleep(1)
    return {"msg": "ok"}



if __name__ == "__main__":
    uvicorn.run(app)
```



本文所有依赖如下:

- Python > 3.7+
- fastapi
- aiohttp
- uvicorn



所有依赖可通过代码仓库的requirements.txt一次性安装。

```bash
pip install requirements.txt
```





## 并发，并发，并发

首先看一个错误的例子

```python
# test1.py
import asyncio
from datetime import datetime
import aiohttp

async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        for _ in range(workers):
            async with sess.get(url) as resp:
                print("响应内容", await resp.json())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/"))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```shell
$ python test1.py
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
耗时: 0:00:03.011565
```

发现花费了3秒，不符合预期呀。。。。这是因为虽然用了协程，但是每个协程是串行的运行，也就是说后一个等前一个完成之后才开始，那么这样的异步代码并没有并发，所以我们需要让这些协程并行起来

```python
# test2.py
import asyncio
from datetime import datetime
import aiohttp


async def run(sess: aiohttp.ClientSession, url: str):
    async with sess.get(url) as resp:
        print("响应内容", await resp.json())


async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        for _ in range(workers):
            asyncio.ensure_future(run(sess, url))
        await asyncio.sleep(1.1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/"))
    end = datetime.now()
    print("耗时:", end - start)
```

为了让代码变动的不是太多，所以这里用了一个笨办法来等待所有任务完成, 之所以在main函数中等待是为了不让ClientSession关闭, 如果你移除了main函数中的等待代码会发现报告异常`RuntimeError: Session is closed`,而代码里的解决方案非常的不优雅，需要手动的等待，为了解决这个问题，我们再次改进代码。

```python
# test3.py
import asyncio
from datetime import datetime
import aiohttp


async def run(sess: aiohttp.ClientSession, url: str):
    async with sess.get(url) as resp:
        print("响应内容", await resp.json())


async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        futures = []
        for _ in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url)))
        
        done, pending = await asyncio.wait(futures)
        print(done, pending)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/"))
    end = datetime.now()
    print("耗时:", end - start)
```

这里解决的方式是通过`asyncio.wait`方法等待一个协程列表，默认是等待所有协程结束后返回，会返回一个完成(done)列表，以及一个待办(pending)列表。



如果我们不想要协程对象而是结果，那么我们可以使用`asyncio.gather`

```python
# test4.py
import asyncio
from datetime import datetime
import aiohttp


async def run(sess: aiohttp.ClientSession, url: str, id: int):
    async with sess.get(url) as resp:
        print("响应内容", await resp.json())
        return id


async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        futures = []
        for i in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url, i)))
        
        # 注意: 这里要讲列表解开
        rets = await asyncio.gather(*futures)
        print(rets)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/"))
    end = datetime.now()
    print("耗时:", end - start)
```

结果输出如下:

```bash
$ python test4.py
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
[0, 1, 2]
耗时: 0:00:01.011840
```



### 小结

通过`asyncio.ensure_future`我们就能创建一个协程，跟调用一个函数差别不大，为了等待所有任务完成之后退出，我们需要使用`asyncio.wait`等方法来等待，如果只想要协程输出的结果，我们可以使用`asyncio.gather`来获取结果。



## 同步

虽然前面能够随心所欲的创建协程，但是就像多线程一样，我们也需要处理协程之间的同步问题，为了保持语法及使用情况的一致，多线程中用到的同步功能，asyncio中基本也能找到, 并且用法基本一致，不一致的地方主要是需要用异步的关键字，比如`async with/ await`等



### 锁 lock

通过锁让并发慢下来，让协程一个一个的运行。

```python
# test5.py
import asyncio
from datetime import datetime
import aiohttp


lock = asyncio.Lock()

async def run(sess: aiohttp.ClientSession, url: str, id: int):
    async with lock:
        async with sess.get(url) as resp:
            print("响应内容", await resp.json())
            return id

async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        futures = []
        for i in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url, i)))
        
        # 注意: 这里要讲列表解开
        rets = await asyncio.gather(*futures)
        print(rets)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/"))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```bash
$ python test5.py
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
响应内容 {'msg': 'ok'}
[0, 1, 2]
耗时: 0:00:03.007251
```

通过观察很容易发现，并发的速度因为锁而慢下来了，因为每次只有一个协程能获得锁，所以并发变成了串行。



### 事件 event

通过事件来通知特定的协程开始工作，假设有一个任务是根据http响应结果选择是否激活。

```python
# test6.py
import asyncio
from datetime import datetime
import aiohttp


big_event = asyncio.Event()
small_event = asyncio.Event()


async def big_waiter():
    await small_event.wait()
    print(f"{datetime.now()} big waiter 收到任务事件")


async def small_waiter():
    await big_event.wait()
    print(f"{datetime.now()} small waiter 收到任务事件")


async def run(sess: aiohttp.ClientSession, url: str, id: int):
    async with sess.get(url) as resp:
        ret = await resp.json()
        print("响应内容", ret)
        data = ret["msg"]
        if data > 0.5:
            big_event.set()
        else:
            small_event.set()
        return data

async def main(workers: int, url: str):
    asyncio.ensure_future(big_waiter())
    asyncio.ensure_future(big_waiter())
    asyncio.ensure_future(small_waiter())
    asyncio.ensure_future(small_waiter())

    async with aiohttp.ClientSession() as sess:
        futures = []
        for i in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url, i)))
        await asyncio.wait(futures)

    if not big_event.is_set():
        big_event.set()
    
    if not small_event.is_set():
        small_event.set()

    # 等到其他pending可马上运行完成的任务运行结束
    await asyncio.sleep(0)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/random"))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```bash
响应内容 {'msg': 0.9879470259657458}
2022-07-11 10:16:51.577579 small waiter 收到任务事件
2022-07-11 10:16:51.577579 small waiter 收到任务事件
响应内容 {'msg': 0.33312954919903903}
2022-07-11 10:16:51.578574 big waiter 收到任务事件
2022-07-11 10:16:51.578574 big waiter 收到任务事件
响应内容 {'msg': 0.41934453838367824}
耗时: 0:00:00.996697
```

可以看到事件(Event)等待者都是在得到响应内容之后输出，并且事件(Event)可以是多个协程同时等待。



### 条件 Condition

上面的事件虽然很棒，能够在不同的协程之间同步状态，并且也能够一次性同步所有的等待协程，但是还不够精细化，比如想通知指定数量的等待协程，这个时候Event就无能为力了，所以同步原语中出现了Condition。

```python
# test7.py
import asyncio
from datetime import datetime
import aiohttp


cond = asyncio.Condition()


async def waiter(id):
    async with cond:
        await cond.wait()
        print(f"{datetime.now()} waiter[{id}]等待完成")


async def run(sess: aiohttp.ClientSession, url: str, id: int):
    async with sess.get(url) as resp:
        ret = await resp.json()
        print("响应内容", ret)
        data = ret["msg"]
        async with cond:
            # cond.notify()
            # cond.notify_all()
            cond.notify(2)
        return data

async def main(workers: int, url: str):
    for i in range(workers):
        asyncio.ensure_future(waiter(i))

    async with aiohttp.ClientSession() as sess:
        futures = []
        for i in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url, i)))
        await asyncio.wait(futures)


    # 等到其他pending可马上运行完成的任务运行结束
    await asyncio.sleep(0)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/random"))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```bash
$ python test7.py
响应内容 {'msg': 0.587516452693613}
2022-07-11 10:26:13.482781 waiter[0]等待完成
2022-07-11 10:26:13.483778 waiter[1]等待完成
响应内容 {'msg': 0.3391774763719556}
响应内容 {'msg': 0.2653464378663153}
2022-07-11 10:26:13.484771 waiter[2]等待完成
耗时: 0:00:01.013655
```

可以看到，前面两个等待的协程是在同一时刻完成，而不是全部等待完成。



### 信号量 Semaphore

通过创建协程的数量来控制并发并不是非常优雅的方式，所以可以通过信号量的方式来控制并发。

```python
# test8.py
import asyncio
from datetime import datetime
import aiohttp


semp = asyncio.Semaphore(2)


async def run(sess: aiohttp.ClientSession, url: str, id: int):
    async with semp:
        async with sess.get(url) as resp:
            ret = await resp.json()
            print(f"{datetime.now()} worker[{id}] 响应内容", ret)
            data = ret["msg"]
            return data

async def main(workers: int, url: str):
    async with aiohttp.ClientSession() as sess:
        futures = []
        for i in range(workers):
            futures.append(asyncio.ensure_future(run(sess, url, i)))
        await asyncio.wait(futures)


    # 等到其他pending可马上运行完成的任务运行结束
    await asyncio.sleep(0)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3, "http://127.0.0.1:8000/random"))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```bash
$ python test8.py
2022-07-11 10:30:40.634801 worker[0] 响应内容 {'msg': 0.21337652123021056}
2022-07-11 10:30:40.634801 worker[1] 响应内容 {'msg': 0.7591980200967501}
2022-07-11 10:30:41.636346 worker[2] 响应内容 {'msg': 0.8282581038608438}
耗时: 0:00:02.011661
```

可以发现，虽然同时创建了三个协程，但是同一时刻只有两个协程工作，而另外一个协程需要等待一个协程让出信号量才能运行。



### 小结

无论是协程还是线程，任务之间的状态同步还是很重要的，所以有了应对各种同步机制的同步原语，因为要保证一个资源同一个时刻只能一个任务访问，所以引入了锁，又因为需要一个任务等待另一个任务，或者多个任务等待某个任务，因此引入了事件(Event)，但是为了更精细的控制通知的程度，所以又引入了条件(Condition),  通过条件可以控制一次通知多少的任务。

有时候的并发需求是通过一个变量控制并发任务的并发数而不是通过创建协程的数量来控制并发，所以引入了信号量(Semaphore)，这样就可以在创建的协程数远远大于并发数的情况下让协程在指定的并发量情况下并发。



## 兼容多线程，多进程

不得不承认异步编程相比起同步编程的生态要小的很多，所以不可能完全异步编程，因此需要一种方式兼容。

多线程是为了兼容同步得代码。

多进程是为了利用CPU多核的能力。

```python
# test9.py
import time
from datetime import datetime

import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


semp = asyncio.Semaphore(2)


def wait_io(id: int):
    # 为了简单起见，直接使用sleep模拟io
    time.sleep(1)
    return f"threading({id}): done at {datetime.now()}"

def more_cpu(id: int):
    sum(i * i for i in range(10 ** 7))
    return f"process({id}): done at {datetime.now()}"


async def main(workers: int):
    loop = asyncio.get_event_loop()
    futures = []
    thread_pool = ThreadPoolExecutor(workers+1)
    process_pool = ProcessPoolExecutor(workers)
    ret = loop.run_in_executor(thread_pool, wait_io, 0, )


    for i in range(workers):
        futures.append(loop.run_in_executor(thread_pool, wait_io, i))

    for i in range(workers):
        futures.append(loop.run_in_executor(process_pool, more_cpu, i))

    print("\n".join(await asyncio.gather(*futures)))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    start = datetime.now()
    loop.run_until_complete(main(3))
    end = datetime.now()
    print("耗时:", end - start)
```

输出如下:

```bash
threading(0): done at 2022-07-11 15:38:36.073547
threading(1): done at 2022-07-11 15:38:36.074540
threading(2): done at 2022-07-11 15:38:36.074540
process(0): done at 2022-07-11 15:38:36.142233
process(1): done at 2022-07-11 15:38:36.177190
process(2): done at 2022-07-11 15:38:36.162244
耗时: 0:00:01.107643
```

可以看到总耗时1秒，说明所有的线程跟进程是同时运行的。



## 生态

下面是本人使用过的一些异步库，仅供参考

web框架

- fastapi  超级棒的web框架，使用过就不再想使用其他的了

http客户端

- httpie  
- aiohttp

数据库

- aioredis  redis异步库
- motor  mongodb异步库

ORM

- sqlmodel  超级棒的ORM

虽然异步库发展得还算不错，但是中肯的说并没有覆盖方方面面。

## 总结

虽然我鼓励大家尝试异步编程，但是本文的最后却是让大家谨慎的选择开发环境，如果你觉得本文的并发，同步，兼容多线程，多进程不值得一提，那么我十分推荐你尝试以异步编程的方式开始一个新的项目，如果你对其中一些还有疑问或者你确定了要使用的依赖库并且大多数是没有异步库替代的，那么我还是建议你直接按照自己擅长的同步编程开始。

异步编程虽然很不错，不过，也许你并不需要。

