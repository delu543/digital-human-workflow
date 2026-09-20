"""MiniMax official HTTP API. Model/voice/region are per-user configuration."""
from ..config import HOSTS, credential
from ..network import Client
from ..storage import WorkflowError

class MiniMax:
    def __init__(self, workspace, profile, client=None):
        self.profile = profile
        self.client = client or Client(HOSTS[profile['minimax']['region']],
            {'Authorization': 'Bearer ' + credential(workspace, 'minimax')})

    def voices(self):
        return self.client.call('POST', '/v1/get_voice', {'voice_type':'voice_cloning'})

    def speech_payload(self, text, voice_id=None):
        m = self.profile['minimax']
        voice_id = voice_id or m['voice_id']
        if not voice_id:
            raise WorkflowError('尚未绑定本人音色')
        value = {'model':m['model'], 'text':text, 'stream':False,
            'voice_setting':{'voice_id':voice_id,'speed':m['speed'],'vol':1,'pitch':0},
            'audio_setting':{'sample_rate':32000,'bitrate':128000,'format':'mp3','channel':1},
            'language_boost':'Chinese', 'output_format':'hex', 'subtitle_enable':True}
        if m.get('emotion'):
            value['voice_setting']['emotion'] = m['emotion']
        return value

    def speech(self, payload):
        return self.client.call('POST', '/v1/t2a_v2', payload)

    def upload_voice(self, path):
        with path.open('rb') as f:
            result = self.client.call('POST', '/v1/files/upload',
                files={'file':(path.name, f, 'audio/wav')}, data={'purpose':'voice_clone'})
        file_id = result.get('file', {}).get('file_id')
        if not file_id:
            raise WorkflowError('上传响应缺少 file_id')
        return file_id

    def clone(self, file_id, voice_id, text):
        return self.client.call('POST', '/v1/voice_clone', {'file_id':file_id,
            'voice_id':voice_id, 'text':text, 'model':self.profile['minimax']['model'],
            'need_noise_reduction':False,'need_volume_normalization':False})
