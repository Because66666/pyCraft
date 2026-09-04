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
# 离线模式连接（无需账号）
python start.py -u 玩家名 -o -s 服务器地址:端口

# 正版模式连接（微软账号，设备码登录，无需密码）
python start.py -u 微软账号邮箱 -s 服务器地址:端口

# 查看全部选项
python start.py --help
```

正版模式下首次登录会打印一个设备码和链接，在浏览器中打开链接并输入设备码即可完成授权；之后令牌会缓存在本地，再次运行无需重复授权。

`examples/` 目录下还有若干可独立运行的示例脚本（均可用 `python examples/文件名.py` 直接运行）：

| 文件 | 说明 |
| --- | --- |
| `examples/connect_offline.py` | 离线模式连接 |
| `examples/connect_microsoft.py` | 微软账号设备码登录（正版验证）并连接 |
| `examples/chat_bot.py` | 完整聊天机器人：正版验证 + 全面的事件监听 + 发送聊天 |
| `examples/custom_packet.py` | 自定义数据包的定义方式 |

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
可运行的完整版本见 `examples/connect_offline.py`。

## 连接服务器（正版认证）

连接正版验证（online-mode）服务器时，需要先登录微软账号。pyCraft 使用
OAuth 2.0 设备码（device code）流程，**无需提供账号密码**：

```python
from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection

auth_token = authentication.MicrosoftAuthenticationToken()
def on_device_code(data):
    print(f"访问 {data['verification_uri']}?otc={data['user_code']} 以授权。")
try:
    auth_token.authenticate("你的微软账号邮箱",on_device_code=on_device_code)
except YggdrasilError as e:
    print("认证失败：", e)
    raise SystemExit

print("已登录为：%s" % auth_token.username)

connection = Connection("服务器地址", 25565, auth_token=auth_token)
connection.connect()
```

首次调用 `authenticate()` 时，会通过 `on_device_code` 回调（默认直接打印）
给出一个链接和设备码，在浏览器中打开链接、输入设备码并授权后，登录自动完成：

```python
def on_device_code(data):
    print("请打开 %s 并输入设备码 %s" % (
        data["verification_uri"], data["user_code"]))

auth_token.authenticate("你的微软账号邮箱", on_device_code=on_device_code)
```

令牌会缓存在本地（默认 `~/.minecraft/nmp-cache/`，可用 `cache_dir` 参数修改），
之后再次运行会自动复用缓存并静默刷新，无需重复授权。`username` 参数仅用于
区分缓存文件，可以留空。

如果需要 Minecraft 1.19+ 的聊天签名密钥，可以传入
`fetch_certificates=True`，结果保存在 `auth_token.certificates` 中。

> **注意**：切勿在日志或代码仓库中记录、提交访问令牌；缓存目录中的
> JSON 文件包含访问令牌和刷新令牌，同样不得提交。

旧的 Mojang/Yggdrasil 账号认证（`authentication.AuthenticationToken`，
账号密码登录）仍然保留，但 Mojang 已停用相关服务器，仅适用于私有的
Yggdrasil 兼容实现。`start.py` 中可通过 `-p 密码` 使用该方式。

可运行的完整版本见 `examples/connect_microsoft.py`。

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
`examples/chat_bot.py` 中演示了如何为所有已实现的数据包类型注册监听器，
包括注册在基类 `Packet` 上的兜底监听器。

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

完整可运行的聊天机器人见 `examples/chat_bot.py`。所有配置（微软账号邮箱、
服务器地址、端口、缓存目录）都硬编码在文件顶部的常量中，按需修改后直接运行：

```bash
python examples/chat_bot.py
```

相比教程中的精简片段，`examples/chat_bot.py` 演示了：

- 使用 `MicrosoftAuthenticationToken` 进行正版验证（设备码流程，令牌缓存复用）；
- 全部事件监听都使用 `@connection.listener(...)` 装饰器注册，
  覆盖所有已实现的数据包类型：加入游戏、重生、断线、全部四种聊天数据包
  （`ChatMessagePacket`、`PlayerChatPacket`、`SystemChatPacket`、
  `ProfilelessChatPacket`）、生命值、时间、方块变更、爆炸、声音、实体移动、
  战斗事件、玩家列表等，并为基类 `Packet` 注册了一个兜底监听器，
  打印所有未专门处理的数据包；
- 从标准输入发送聊天消息，并支持 `/respawn`（重生）和 `/quit`（退出）命令。

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

可运行的完整版本见 `examples/custom_packet.py`，更多细节请参考 `minecraft/networking/packets/` 下已有的数据包实现。

---

返回 [README.md](README.md)
