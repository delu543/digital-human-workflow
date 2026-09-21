"""Resume until the next real dependency; completed paid steps are never replayed."""
import time
from . import alignment, cloud, composition, delivery, media, quality
from .storage import WorkflowError, read

def run(job, storyboard=None, wait_seconds=0):
    meta=job.load()
    if meta['stage']=='delivered': return {'status':'delivered','video':str(job.artifact('render')),'bundle':str(job.artifact('delivery'))}
    profile=job.profile();brief=read(job.path/'brief.json')
    if profile['heygen']['transport'] in ['api', 'mcp']:
        if gate := quality.next_gate(job): return gate
    if not job.artifact('voice') and not job.artifact('avatar'):
        calibration = brief.get('purpose') == 'calibration' or (
            job.artifact('quality_plan') and read(job.artifact('quality_plan'))['mode'] == 'calibration')
        if not calibration and not profile['approvals']['voice']:
            raise WorkflowError('正式制作前请先完成本人音色试听；校准任务使用 purpose=calibration')
        cloud.speech(job)
    if profile['heygen']['transport'] in ['api', 'mcp']:
        if gate := quality.next_gate(job): return gate
    if not job.artifact('avatar'):
        mode=profile['heygen']['transport']
        if mode=='api':
            cloud.submit_avatar(job)
            deadline=time.monotonic()+max(0,min(wait_seconds,60));delay=3
            while True:
                status=cloud.poll_avatar(job)
                if status['status']=='completed': break
                if time.monotonic()+delay>deadline: return {**status,'next':'Resume this same job with run; never submit another generation.'}
                time.sleep(delay);delay=min(delay*2,20)
        elif mode=='mcp': return cloud.mcp_begin(job)
        else: return {'status':'needs_avatar','next':'Import the user authorized avatar video; no provider or account is selected automatically.'}
    if not job.artifact('captions'): alignment.align(job)
    if brief.get('postproduction',{}).get('mode')=='independent':
        return {'status':'needs_edit_plan','captions':str(job.artifact('captions')),
            'next':'Codex prepares a semantic edit plan from clean digital-avatar media. Use edit-build; '
                   'edit-render produces the MP4 locally. Do not regenerate paid media.'}
    if not job.artifact('composition'):
        if not storyboard: return {'status':'needs_storyboard','captions':str(job.path/'captions.json'),'source_frames':media.frame(job),
            'next':'Codex designs semantic scenes and safe text placement, then passes --storyboard. The human need not hand-author JSON.'}
        composition.compose(job,storyboard)
    if not job.artifact('render'):
        media.hf(job,'check');media.hf(job,'render',timeout=3600)
    technical=delivery.verify(job)
    if not (job.path/'review.json').exists():
        return {'status':'needs_codex_review','video':str(job.artifact('render')),
            'frames':[str(job.path/p) for p in technical['frames']],
            'next':'Codex inspects/listens and records actual evidence with review. Do not fabricate passed fields.'}
    return {'status':'delivered','video':str(job.artifact('render')),'bundle':delivery.bundle(job)}
