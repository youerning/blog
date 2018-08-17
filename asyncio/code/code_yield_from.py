def gen_func():
    a = yield 1
    print("a: ", a)
    b = yield 2
    print("b: ", b)
    c = yield 3
    print("c: ", c)
    return 4


def middle():
    gen = gen_func()
    ret = yield from gen
    print("ret: ", ret)
    return "middle Exception"


def main():
    mid = middle()
    for i in range(4):
        if i == 0:
            print(mid.send(None))
        else:
            try:
                print(mid.send(i))
            except StopIteration as e:
                print("e: ", e)


if __name__ == '__main__':
    main()
