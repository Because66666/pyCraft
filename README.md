# pyCraft

Minecraft Python 客户端库！

本项目旨在成为一个现代化的、兼容 Python 3 的、文档完善的库，用于与 Minecraft 服务器进行通信。

开发者详细信息请参阅：`<http://pycraft.readthedocs.org/en/latest/>`

Because66666 接手该项目后，通过参考开源库
- [PrismarineJS/minecraft-data](https://github.com/PrismarineJS/minecraft-data)
- [PrismarineJS/node-minecraft-protocol](https://github.com/PrismarineJS/node-minecraft-protocol)
- [PrismarineJS/prismarine-auth](https://github.com/PrismarineJS/prismarine-auth)

使用Kimi-K3模型完成原代码仓库的协议升级。

仓库地址：[Because66666/pyCraft](https://github.com/Because66666/pyCraft)

`start.py` 是一个使用该库的无头客户端（headless client）基础示例，使用 `start.py --help` 查看选项。

详细的使用教程与示例请参见：[教程示例](TUTORIAL.md)。

## 支持的 Minecraft 版本

pyCraft 兼容以下 Minecraft 正式版本：

* 1.8, 1.8.1, 1.8.2, 1.8.3, 1.8.4, 1.8.5, 1.8.6, 1.8.7, 1.8.8, 1.8.9
* 1.9, 1.9.1, 1.9.2, 1.9.3, 1.9.4
* 1.10, 1.10.1, 1.10.2
* 1.11, 1.11.1, 1.11.2
* 1.12, 1.12.1, 1.12.2
* 1.13, 1.13.1, 1.13.2
* 1.14, 1.14.1, 1.14.2, 1.14.3, 1.14.4
* 1.15, 1.15.1, 1.15.2
* 1.16, 1.16.1, 1.16.2, 1.16.3, 1.16.4, 1.16.5
* 1.17, 1.17.1
* 1.18, 1.18.1, 1.18.2
* 1.19, 1.19.1, 1.19.2, 1.19.3, 1.19.4
* 1.20, 1.20.1, 1.20.2, 1.20.3, 1.20.4, 1.20.5, 1.20.6
* 1.21, 1.21.1, 1.21.2, 1.21.3, 1.21.4, 1.21.5, 1.21.6, 1.21.7, 1.21.8, 1.21.9, 1.21.10, 1.21.11

此外，还支持部分开发快照（snapshot）和预发布版本。
`minecraft/__init__.py` 中包含完整的受支持 Minecraft 版本列表及对应的协议版本号。

## 支持的功能

虽然 pyCraft 可以兼容任何受支持的服务器，但目前库中仅实现了解码/编码全部数据包中的一个子集：保持服务器连接所必需的数据包、用于聊天的数据包，以及其他一些数据包。

请注意，聊天消息签名（Minecraft 1.19 引入）已支持：当认证令牌带有聊天签名证书时（`MicrosoftAuthenticationToken` 在 `authenticate()` 时传入 `fetch_certificates=True`），发出的聊天消息会自动签名，因此设置了 `enforce-secure-chat=true` 的服务器也能正常聊天。未获取证书时，聊天消息仍以未签名方式发送，适用于离线模式（offline-mode）服务器和不强制安全聊天的服务器。

希望使用其他功能的开发者可以通过以下方式贡献代码：为所需的数据包实现数据包类，将它们添加到 `minecraft/networking/packets` 目录下，并提交 Pull Request。

## 支持的 Python 版本

pyCraft 兼容（至少）以下 Python 实现：

* Python 3.5
* Python 3.6
* Python 3.7
* Python 3.8
* Python 3.9
* PyPy

## 依赖要求

- [cryptography](https://github.com/pyca/cryptography#cryptography)
- [requests](http://docs.python-requests.org/en/latest/)
- [PyNBT](https://github.com/TkTech/PyNBT)

这些依赖也记录在 `setup.py` 中。

cryptography 库的安装说明请参阅：`<https://cryptography.io/en/latest/installation/>`，
基本上执行 `pip install -r requirements.txt` 即可安装所有依赖。

## 联系方式

本项目目前由 **Because66666** 进行维护，继承项目：[ammaraskar/pyCraft](https://github.com/ammaraskar/pycraft)。

### GitHub

首选的沟通方式是通过本项目的 GitHub 页面。

### 邮件

可以通过邮件联系：

* Because66666 <z66666z@163.com>
