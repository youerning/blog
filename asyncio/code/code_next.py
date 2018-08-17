def gen_func():
    yield 1
    yield 2
    yield 3

if __name__ == '__main__':
    gen = gen_func()
    print(next(gen))
    print(next(gen))
    print(next(gen))