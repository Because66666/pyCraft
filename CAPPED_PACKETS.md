# 高版本封顶（未注册）的包清单

pyCraft 对协议的实现策略是"按需实现"：只注册保持连接、聊天等所需的包类。
部分包类在高版本协议中**封顶**——即 `get_packets(context)` 不再为那些协议
注册该类。被封顶的包到达客户端时，会回退为不解析字段的裸 `Packet` 并被静默
忽略，不会导致崩溃或断连；类本身保留，旧协议和手工构造仍然可用
（`tests/test_backward_compatible.py` 保证这些类的公开接口不被破坏）。

封顶分两类原因：

- **官方移除/重构**：Mojang 在该版本中删除或拆分了此包，不是 pyCraft 的缺口。
- **实现封顶**：线格式变化引入了 pyCraft 尚未支持的新类型（holder、
  Particle、lpVec3 等），该版本起不再注册。

## 封顶包列表（均为 clientbound / play 状态）

| 包类 | 模块 | 功能 | 不支持的协议 | 原因 |
|---|---|---|---|---|
| `ChatMessagePacket` | `minecraft/networking/packets/clientbound/play/__init__.py` | 旧版聊天广播（JSON 文本 + 位置 + 发送者） | 759+（MC 1.19+） | **官方移除**：拆分为 system chat 与 player chat。pyCraft 已支持 `SystemChatPacket` |
| `PlayerChatPacket` | 同上 | 带签名的玩家聊天消息 | 767+（MC 1.21+） | **实现封顶**：`type` 字段变为 registry entry holder（`ChatTypesHolder`）。已支持 759–766 |
| `ProfilelessChatPacket` | 同上 | 无签名玩家聊天（插件/代理服务器用） | 767+（MC 1.21+） | **实现封顶**：同上。已支持 761–766 |
| `SpawnPlayerPacket` | 同上（`__init__.py:499`） | 生成玩家实体 | 764+（MC 1.20.2+） | **官方移除**：并入 spawn_entity |
| `NamedSoundEffectPacket` | `clientbound/play/sound_effect_packet.py` | 按名称播放声音 | 761+（MC 1.19.3+） | **官方移除**：并入 `SoundEffectPacket` 的 holder 内联形式（已支持） |
| `ResourcePackSendPacket` | `clientbound/play/__init__.py:792` | 下发资源包 | 765+（MC 1.20.3+） | **官方重构**：拆分为 add_resource_pack / remove_resource_pack |
| `ExplosionPacket` | `clientbound/play/explosion_packet.py` | 爆炸效果 | 765+（MC 1.20.3+） | **实现封顶**：新增 Particle 粒子与 sound holder 字段。已支持 ≤764 |
| `MapPacket` | `clientbound/play/map_packet.py` | 地图画布数据 | 765+（MC 1.20.3+） | **实现封顶**：图标 `displayName` 由 JSON String 变为 NBT。已支持 ≤764（注：匿名根 NBT 现已支持，可低成本解封） |
| `SpawnObjectPacket` | `clientbound/play/spawn_object_packet.py` | 生成非玩家实体（掉落物、弹射物等） | 773+（MC 1.21.9+） | **实现封顶**：`velocity` 改用 lpVec3 变长量化编码且字段前移。已支持 ≤772（注：`LpVec3` 类型已实现，可低成本解封） |

## 补充说明

- **Serverbound（上行）方向无任何封顶**：keep alive、chat（含 ≥770 的
  checksum 字段）、chat command、client settings/information、
  teleport confirm、plugin message、configuration acknowledged 等全部
  支持到协议 774（MC 1.21.11）。
- **configuration 状态（764+）的 `registry_data` 刻意未实现**：它是整包
  忽略设计的核心——注册表数据体积巨大且 headless 客户端无需解析。同理
  cookie、transfer、dialog、code_of_conduct 等新包也未注册，均按未知包
  忽略。
- **旧版组合 `CombatEventPacket`**（1.17 之前）：其三个后继
  `EnterCombatEventPacket` / `EndCombatEventPacket` /
  `DeathCombatEventPacket` 全部支持到 774。
- 封顶判定代码集中在
  `minecraft/networking/packets/clientbound/play/__init__.py` 的
  `get_packets(context)`，每处均有注释说明封顶协议号与原因。
