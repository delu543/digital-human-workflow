"""HeyGen v3 API adapter; membership OAuth is handled by the Codex MCP bridge."""
from urllib.parse import quote
from ..config import credential
from ..network import Client
from ..storage import WorkflowError

class HeyGen:
    def __init__(self, workspace, profile, client=None):
        self.profile = profile
        if profile['heygen']['transport'] != 'api':
            raise WorkflowError('当前不是 API 计费路径；不会静默切换账单')
        self.client = client or Client('https://api.heygen.com',
            {'x-api-key':credential(workspace,'heygen')})

    def me(self):
        return self.client.call('GET','/v3/users/me')

    def looks(self):
        return self.client.call('GET','/v3/avatars/looks')

    def upload(self, path):
        if path.stat().st_size > 32*1024*1024:
            raise WorkflowError('配音超过 HeyGen 32MB 上传上限，请使用压缩 MP3')
        with path.open('rb') as f:
            result = self.client.call('POST','/v3/assets', files={'file':(path.name,f,'audio/mpeg')})
        data = result.get('data', {})
        asset_id = data.get('asset_id') or data.get('id')
        if not asset_id:
            raise WorkflowError('素材响应缺少 asset_id')
        return asset_id

    def payload(self, audio_asset_id, job_id):
        h = self.profile['heygen']; f = self.profile['format']
        if not h['avatar_id']:
            raise WorkflowError('尚未绑定用户已创建的数字人 look ID')
        ratio = '9:16' if f['height'] > f['width'] else ('16:9' if f['width'] > f['height'] else '1:1')
        return {'type':'avatar','avatar_id':h['avatar_id'],'audio_asset_id':audio_asset_id,
            'engine':{'type':h['engine']},'aspect_ratio':ratio,'resolution':h['resolution'],
            'output_format':'mp4','fit':'contain','title':'Digital Human '+job_id,
            'callback_id':job_id}

    def create(self, payload):
        return self.client.call('POST','/v3/videos',payload)

    def get(self, video_id):
        return self.client.call('GET','/v3/videos/'+quote(video_id,safe=''))
