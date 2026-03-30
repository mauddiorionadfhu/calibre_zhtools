
# 脚本
- `Calibre中文目录修复工具.py`修改已有的数据库中的中文路径名称
- `remove_tags.py`去除除指定数据库中元素外的所有标签，标签清洗
- `删除Calibre库中的所有空白文件夹.py`删除各种原因导致的Calibre中的错误的，空白的文件夹
# calibre-do-not-translate-my-path
## 准备工作

1. 需要去GitHub下载一个文件，地址是：https://github.com/Cirn09/calibre-do-not-translate-my-path。名字很有意思，calibre不要翻译我的路径...

2. 找到Releases，最新的版本是7.2，上周刚更新的。


3. 找到对应的版本下载好，解压出来。

文件说明：
- backend.zip：只实现了路径不翻译。
- backend+update.zip：在 backend 的基础上还 patch 了更新检查链接和新版本下载链接。使用这个补丁，Calibre 检查更新时会以本项目的版本为准，下版本下载链接也被替换成了本项目 latest releases 地址。
- .msi/.txz：将 backend+update 补丁重新打包后的完整安装包


## 使用方法：

Windows：

解压好之后有一个文件名叫：python-lib.bypy.frozen，放到calibre安装目录下Calibre2\app\bin，直接替换，重启calibre即可。

MacOs：

1. 解压下载的包，得到 `python-lib.bypy.frozen` 文件。

2. 打开 `Finder`，进入“应用程序” (/Applications)，右键点击“Calibre——显示包内容”，进入 `Contents/Frameworks/plugins` (对应的完整路径是`/Applications/calibre.app/Contents/Frameworks/plugins` )。将第 1 步下载包里的 `python-lib.bypy.frozen`，拷贝覆盖过来、关闭 `Finder` 窗口，正常打开 `Calibre` 即可。



## 将已有的书库改成非英文路径：

备份你的书库（可选，建议）

打开书库，按下 Ctrl+A 选中所有书籍

右键 - 编辑元数据 - 批量编辑元数据 - “查找替换”页

查找模式：正则表达式，查找的字段：title，搜索：$，替换为：__DELME__

点击“应用”，等待 Calibre 完成（点击前注意看一下下面的替换预阅，新书名应当是原书名+__DELME__）

查找模式：字符匹配，查找的字段：title，搜索：__DELME__，“替换为”保持为空。

点击“确定”，等待 Calibre 完成（点击前注意看一下下面的替换预阅，此时的新书名应当是原本的书名）

作者：Marklin_BL https://www.bilibili.com/read/cv28827159/?opus_fallback=1 出处：bilibili
