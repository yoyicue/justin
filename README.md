## Manager Flexget Crontab 
这是一个很挫很挫的脚本, 用来管理 Flexget 的 Crontab 

### 使用
访问 `http://SeedboxIP:8118/flexget`  
把 `SeedboxIP` 替换成你的 SeedBox IP

### 配置
默认运行在 root 权限下
在 `run.py` 中配置命令行, 和运行时间间隔

```
cmd = "/usr/local/bin/flexget > /root/flexget.log 2>&1"
minutes = 2
```

### 安装
解压之后运行即可, 启动运行可配置到  `/etc/rc.lcoal` 当中

```
$ tar zxvf justin.tar.gz
$ /usr/bin/python /root/justin/run.py > /root/justin.log 2>&1 &
```

###  依赖

[bottle](http://bottlepy.org)  
[python-crontab](http://pypi.python.org/pypi?name=python-crontab&:action=display)

### Todo
缺少一个简单的验证


