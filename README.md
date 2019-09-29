# LFI-With-PHPInfo-Assitance

- 利用条件
    - 存在lfi漏洞
    - 存在可访问phpinfo网页

- 利用原理
    - php会把post请求, 存储在临时文件中, 并在请求结束后删除临时文件
    - phpinfo中会显示_FILE变量, 其中会显示临时文件路径
    - 所以可以通过发送数据量大的请求, 拖延php删除临时文件的时间, 同时查看_FILE得到临时文件位置, 并使用lfi漏洞对其进行包含从而执行

- 利用步骤
    1. 发送post请求到phpinfo,  post的内容为一个创建shell文件的payload
    2. 通过有lfi漏洞的页面包含payload, payload被执行然后创建shell文件
    3. 通过lfi页面包含shell文件, 并传参, 从而进行利用

- 环境部署
    - https://github.com/dhgdhg/LFI-With-PHPInfo-Assitance

- 测试结果
    - ![](https://img2018.cnblogs.com/blog/1043898/201909/1043898-20190929145648321-1378560911.png)

    - ![](https://img2018.cnblogs.com/blog/1043898/201909/1043898-20190929145556471-1449404554.png)

- 参考: https://dl.packetstormsecurity.net/papers/general/LFI_With_PHPInfo_Assitance.pdf
