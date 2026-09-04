# pyCraft 教程示例

本文档通过一系列示例，介绍如何使用 pyCraft 库与 Minecraft 服务器进行通信。

## 目录

1. [安装](#安装)
2. [快速上手：使用 start.py 示例客户端](#快速上手使用-startpy-示例客户端)
3. [连接服务器（离线模式）](#连接服务器离线模式)
4. [连接服务器（正版认证）](#连接服务器正版认证)
5. [监听数据包](#监听数据包)
6. [发送数据包](#发送数据包)
7. [完整示例：一个简单的聊天机器人](#完整示例一个简单的聊天机器人)
8. [自定义数据包](#自定义数据包)

## 安装

```bash
pip install -r requirements.txt
```

这会以可编辑模式安装 pyCraft 及其依赖（`cryptography`、`requests`、`pynbt`）。

## 快速上手：使用 start.py 示例客户端

`start.py` 是一个基于本库实现的无头（headless）命令行客户端，可以直接使用：

```bash
# 离线模式连接（无需密码）
python start.py -u 玩家名 -o -s 服务器地址:端口

# 查看全部选项
python start.py --help
```

## 连接服务器（离线模式）

离线模式（offline-mode）服务器无需 Mojang 认证，只需提供用户名：

```python
from minecraft.networking.connection import Connection

connection = Connection(
    "localhost", 25565,      # 服务器地址与端口
    username="MyBot",        # 游戏内显示的用户名
)
connection.connect()
```

`connect()` 会启动后台线程处理网络读写，主线程可以继续执行其他逻辑。

## 连接服务器（正版认证）

连接正版验证（online-mode）服务器时，需要先通过 Mojang/Yggdrasil 认证：

```python
from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection

auth_token = authentication.AuthenticationToken()
try:
    auth_token.authenticate("你的账号邮箱", "你的密码")
except YggdrasilError as e:
    print("认证失败：", e)
    raise SystemExit

print("已登录为：%s" % auth_token.username)

connection = Connection("服务器地址", 25565, auth_token=auth_token)
connection.connect()
```

> **注意**：切勿在日志或代码仓库中记录、提交账号密码和访问令牌。

## 监听数据包

通过 `register_packet_listener` 注册回调函数，当收到指定类型的数据包时会被调用：

```python
from minecraft.networking.packets import clientbound

def handle_join_game(join_game_packet):
    print("已加入游戏！")

def print_chat(chat_packet):
    print("聊天消息（%s）：%s" % (
        chat_packet.field_string('position'), chat_packet.json_data))

connection.register_packet_listener(
    handle_join_game, clientbound.play.JoinGamePacket)

connection.register_packet_listener(
    print_chat, clientbound.play.ChatMessagePacket)
```

也可以使用装饰器写法：

```python
from minecraft.networking.packets.clientbound.play import ChatMessagePacket

@connection.listener(ChatMessagePacket)
def print_chat(chat_packet):
    print("聊天内容：", chat_packet.json_data)
```

数据包可用的字段名可以查看对应数据包类的 `definition` 属性。

## 发送数据包

找到需要的数据包类，实例化后按其 `definition` 中的字段名赋值，然后调用 `write_packet` 发送：

```python
from minecraft.networking.packets import serverbound

# 发送聊天消息
packet = serverbound.play.ChatPacket()
packet.message = "大家好！"
connection.write_packet(packet)

# 重生
packet = serverbound.play.ClientStatusPacket()
packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
connection.write_packet(packet)
```

## 完整示例：一个简单的聊天机器人

以下是一个完整的可运行示例：连接离线模式服务器，打印收到的聊天消息，并从标准输入发送聊天内容。

```python
import sys
from minecraft.networking.connection import Connection
from minecraft.networking.packets import clientbound, serverbound

# 1. 建立离线模式连接
connection = Connection("localhost", 25565, username="ChatBot")

# 2. 注册监听器：加入游戏
def handle_join_game(join_game_packet):
    print("已连接到服务器。")

connection.register_packet_listener(
    handle_join_game, clientbound.play.JoinGamePacket)

# 3. 注册监听器：聊天消息
def print_chat(chat_packet):
    print("收到消息：%s" % chat_packet.json_data)

connection.register_packet_listener(
    print_chat, clientbound.play.ChatMessagePacket)

# 4. 开始连接
connection.connect()

# 5. 主循环：从标准输入读取并发送聊天
while True:
    try:
        text = input()
        packet = serverbound.play.ChatPacket()
        packet.message = text
        connection.write_packet(packet)
    except KeyboardInterrupt:
        print("再见！")
        sys.exit()
```

## 自定义数据包

如果你需要库中尚未实现的数据包，可以通过继承 `Packet` 类来实现：

```python
from minecraft.networking.packets import Packet
from minecraft.networking.types import VarInt, String

class MyCustomPacket(Packet):
    id = 0x00                      # 数据包 ID
    packet_name = "my packet"      # 数据包名称（用于日志）
    definition = [                 # 字段定义：字段名 -> 类型
        {'some_id': VarInt},
        {'some_text': String},
    ]
```

如果数据包 ID 或结构因协议版本而异，可以重写 `get_id(context)` 或 `get_definition(context)` 方法，通过 `context.protocol_version` 判断当前协议版本。

更多细节请参考 `minecraft/networking/packets/` 下已有的数据包实现。

---

返回 [README.md](README.md)
