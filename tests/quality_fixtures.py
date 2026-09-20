"""Fabricated test evidence only; never used as a real approval."""
from digital_human import quality
from digital_human.storage import now, file_hash

NOTE = 'Synthetic unit fixture, not a human or model quality judgement.'

def plan(job):
    h = job.profile()['heygen']
    return {'schema_version':1, 'mode':'calibration', 'sample_max_seconds':30,
        'source_review':dict.fromkeys(['provenance','observations','evidence'],NOTE),
        'look_review':dict(dict.fromkeys(['identity','eyes','hands','lighting','contact'],True),evidence=NOTE),
        'motion_review':{'pose_matches':True,'camera_angle_matches':True,'evidence':NOTE},
        'capability':{'avatar_id':h['avatar_id'],'engine':h['engine'],
            'supported_api_engines':[h['engine']],'reference_look_id':h.get('reference_look_id'),
            'reference_eligible':True,'evidence':NOTE,'checked_at':now()}}

def voice_review(job):
    return dict({k:{'status':'passed','evidence':NOTE} for k in ['wording','pronunciation','pauses','naturalness']},
                voice_sha256=file_hash(job.artifact('voice')),method='listened')

def ready_avatar(job):
    quality.save_plan(job,plan(job));quality.review_voice(job,voice_review(job))

def motion_review():
    return {'inspected_segments':[{'start':0,'end':1,'method':'video_playback','evidence':NOTE}],
            'audio_review':{'method':'listened','evidence':NOTE}}

def baseline_review(job):
    return dict({k:{'status':'passed','evidence':NOTE} for k in ['identity','gaze','motion','scene','sync','voice']},
                avatar_sha256=file_hash(job.artifact('avatar')),user_accepted=True,user_evidence=NOTE,
                **motion_review())
