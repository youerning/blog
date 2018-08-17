def gen_func():
    a = yield 1
    print("a: ", a)
    b = yield 2
    print("b: ", b)
    c = yield 3
    print("c: ", c)
    return "finish"

if __name__ == '__main__':
    gen = gen_func()
    for i in range(4):
        if i == 0:
            print(gen.send(1))
        else:
            # 因为gen生成器里面只有三个yield，那么只能循环三次。
            # 第四次循环的时候,生成器会抛出StopIteration异常,并且return语句里面内容放在StopIteration异常里面
            try:
                print(gen.send(i))
            except StopIteration as e:
                print("e: ", e)



