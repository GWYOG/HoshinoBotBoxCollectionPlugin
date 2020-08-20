# Box统计插件 for HoshinoBot

A [HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot) based [PCR](http://priconne-redive.jp/) plugin which can make the bot collect clan member's box automatically.  .


## 简介

基于 [HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot) 开发的box统计插件，群管理可在QQ群中设置机器人统计box的相关参数，之后机器人会自动私聊公会成员统计他们的box。现支持统计角色的星级和Rank。

统计完的box可以在群内通过指令查看，也可以自动生成excel文档到服务器后台。

更进一步，如果机器人可以发图并且服务器装有中文字体库的话，则机器人可以自动生成图片形式的excel表格并发到群中。


## 注意事项

与酷Q不同，Mirai不支持机器人对非好友主动发起临时会话(参考这个[issue](https://github.com/Mrs4s/go-cqhttp/issues/117))。所以在Mirai上使用此插件时，大部分群员很可能会收不到机器人私聊发送的录入box提醒，机器人也很可能不会回复响应群员私聊发送的"录入box"指令。目前唯一可行的解决办法是公会所有人都添加机器人为QQ好友。


## 功能介绍

详细功能和具体使用方法请在QQ群中发送“帮助pcrbox统计”查看，主要功能目前有：

- **一键box统计**：让机器人私聊统计box的主指令
- **设置box统计**：配置box统计的相关参数，包括存放的数据库名、需要私聊统计box的公会成员名单、私聊统计box时一并发送过去的统计说明、需要统计的角色名单
- **查看box统计**：可设置多种参数，分类汇总统计结果供查看
- **删除box数据**：删除指定qq号的全部录入数据或者指定角色的全部录入数据
- **查看box数据库名**：查看所有数据库的名称
- **查看已统计角色**：查看所有已统计过星级的角色
- **导出box统计表**：自动导出统计结果到后台并保存为csv文件
- **发送box统计图**：以图片的形式在QQ群中发送统计结果的汇总表格，需要机器人能够发图且服务器装有`simsun.ttc`字体


## 安装方式

1. clone或者下载此仓库的代码

2. 将boxcolle文件夹放入`hoshino/modules/`文件夹中

3. 打开`hoshino/config/`文件夹中的`__bot__.py`文件，在`MODULES_ON`中加入一行`'boxcolle',`