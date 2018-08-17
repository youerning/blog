def gen_func():
    yield 1
    yield 2
    yield 3

if __name__ == '__main__':
    print()
    gen = gen_func()
    for i in gen:
        print(i)
