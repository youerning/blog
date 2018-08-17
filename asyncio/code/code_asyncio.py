import asyncio


# 通过async声明一个协程
async def handle_echo(reader, writer):
    # 将需要io的函数使用await等待, 那么此函数就会停止
    # 当IO操作完成会唤醒这个协程
    # 可以将await理解为yield from
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))

    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()


# 创建事件循环
loop = asyncio.get_event_loop()
# 通过asyncio.start_server方法创建一个协程
coro = asyncio.start_server(handle_echo, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()