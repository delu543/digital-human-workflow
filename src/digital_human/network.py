"""No implicit retries or credential-bearing redirects. Public media downloads only."""
import ipaddress
import os
import socket
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from .storage import WorkflowError

class ProviderError(WorkflowError):
    pass

class Client:
    def __init__(self, base, headers, session=None):
        if base not in ['https://api.heygen.com','https://api.minimax.io','https://api.minimaxi.com']:
            raise WorkflowError('不支持的凭证发送地址')
        self.base, self.headers = base, headers
        self.session = session or requests.Session()

    def call(self, method, path, payload=None, files=None, data=None):
        if not path.startswith('/') or '://' in path:
            raise WorkflowError('无效服务接口路径')
        try:
            r = self.session.request(method, self.base + path, headers=self.headers,
                json=payload, files=files, data=data, timeout=(15, 180), allow_redirects=False)
        except requests.RequestException:
            raise ProviderError('服务请求未确认完成；错误详情和密钥不会写入日志') from None
        if not 200 <= r.status_code < 300:
            raise ProviderError('服务返回 HTTP ' + str(r.status_code) + '；请核对账号状态，不自动重试')
        try:
            result = r.json()
        except ValueError:
            raise ProviderError('服务返回格式无法识别；不能判断收费请求结果') from None
        if not isinstance(result, dict):
            raise ProviderError('服务响应不是对象')
        status = result.get('base_resp', {}).get('status_code', 0)
        if status != 0:
            raise ProviderError('MiniMax 返回错误码 ' + str(status))
        if result.get('error'):
            raise ProviderError('服务报告任务错误；请查看供应商控制台')
        return result

def public_https(url):
    try:
        u = urlparse(url)
        if u.scheme != 'https' or u.username or u.password or not u.hostname or u.port not in [None,443]:
            raise ValueError()
        addresses = socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError()
    except (ValueError, OSError):
        raise WorkflowError('媒体地址必须是公网 HTTPS，不能访问本机或私有网络') from None
    return url

def download(url, target, max_bytes=1024**3):
    target = Path(target)
    if target.exists():
        raise WorkflowError('下载目标已存在；先核对当前任务素材，不覆盖')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.' + uuid.uuid4().hex + '.partial')
    session = requests.Session()
    try:
        for _ in range(6):
            public_https(url)
            r = session.get(url, stream=True, timeout=(15,60), allow_redirects=False)
            if r.status_code in [301,302,303,307,308]:
                location = r.headers.get('Location'); r.close()
                if not location:
                    raise WorkflowError('媒体重定向缺少目标')
                url = urljoin(url, location); continue
            if r.status_code != 200:
                r.close(); raise WorkflowError('媒体下载失败，请刷新原任务下载地址')
            with r, temp.open('xb') as f:
                total = 0
                for chunk in r.iter_content(1024*1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise WorkflowError('媒体文件超过允许大小')
                    f.write(chunk)
                f.flush(); os.fsync(f.fileno())
            if total == 0:
                raise WorkflowError('媒体下载为空')
            os.replace(temp, target)
            return target
        raise WorkflowError('媒体重定向次数过多')
    except requests.RequestException:
        raise WorkflowError('媒体下载中断；可以恢复下载，不需要重新生成') from None
    finally:
        session.close()

def put_presigned(url, path, headers):
    public_https(url)
    if any(k.lower() in ['authorization','cookie','x-api-key'] for k in headers):
        raise WorkflowError('预签名上传不能附加账号密钥或 Cookie')
    with Path(path).open('rb') as f:
        try:
            r = requests.put(url, data=f, headers=headers, timeout=(15,120), allow_redirects=False)
        except requests.RequestException:
            raise WorkflowError('预签名上传中断；先核实同一 asset，不重复创建视频') from None
    if not 200 <= r.status_code < 300:
        raise WorkflowError('素材上传失败：HTTP ' + str(r.status_code))
    return {'uploaded': True}
