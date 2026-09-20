"""Compile digital-avatar edit decisions to an editor-independent timeline."""
from copy import deepcopy
import math
import re
from .storage import WorkflowError

SCHEMA = 'digital-human-edit/v1'
CHANNELS = {'x': (-1, 1), 'y': (-1, 1), 'scale': (.05, 5),
            'rotation': (-360, 360), 'opacity': (0, 1)}

def require(ok, message):
    if not ok: raise WorkflowError(message)

def fields(value, allowed, label):
    require(isinstance(value, dict) and not set(value) - set(allowed), label+' 有未知字段')

def number(value, low, high, label):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high, label+' 数值无效')
    return value

def us(value):
    return round(value * 1_000_000)

def visual(raw, duration, width):
    fields(raw, {'x','y','scale','rotation','opacity','fit','mask','font_size','color','keyframes'}, '画面设置')
    out = {key: number(raw.get(key, default), *CHANNELS[key], key)
           for key, default in [('x',0),('y',0),('scale',1),('rotation',0),('opacity',1)]}
    require(raw.get('fit','contain') in ['contain','cover'], 'fit 只能是 contain/cover')
    require(raw.get('mask','none') in ['none','circle'], '当前通用蒙版支持 none/circle')
    out.update(fit=raw.get('fit','contain'), mask=raw.get('mask','none'),
               font_size=number(raw.get('font_size',width*.045),12,200,'font_size'), color=raw.get('color','#FFFFFF'))
    require(isinstance(out['color'],str) and re.fullmatch(r'#[0-9a-fA-F]{6}',out['color']), '颜色必须是 #RRGGBB')
    frames=raw.get('keyframes',{});fields(frames,CHANNELS,'关键帧')
    out['keyframes']={}
    for channel, points in frames.items():
        require(isinstance(points,list) and 2 <= len(points) <= 100, '每组关键帧需要 2–100 个点')
        previous=-1;checked=[]
        for point in points:
            fields(point,{'time','value'},'关键帧点')
            at=us(number(point.get('time'),0,duration,'关键帧时间'))
            require(at>previous, '关键帧必须按时间递增，不能重复')
            previous=at;checked.append({'time':at/1e6,'value':number(point.get('value'),*CHANNELS[channel],channel)})
        require(checked[0]['time']==0, '关键帧第一点必须从片段开头开始')
        out[channel]=checked[0]['value'];out['keyframes'][channel]=checked
    return out

def compile_plan(plan, source_duration, cues, fmt, assets):
    """Ranges are source seconds; overlays/audio use final timeline seconds."""
    fields(plan,{'schema','ranges','overlays','audio','captions','presenter'},'剪辑计划')
    require(plan.get('schema')==SCHEMA, '需要 digital-human-edit/v1 剪辑计划')
    ranges=plan.get('ranges',[{'start':0,'end':source_duration}])
    require(isinstance(ranges,list) and 1<=len(ranges)<=500,'需要 1–500 段保留区间')
    cap=plan.get('captions',{});fields(cap,{'style','replacements'},'字幕设置')
    replacements=cap.get('replacements',{})
    require(isinstance(replacements,dict) and all(isinstance(k,str) and k.isdigit() and int(k)<len(cues) for k in replacements), '字幕替换键必须是原字幕序号')
    result=[];cursor=0;mapped=[]
    for i,span in enumerate(ranges):
        fields(span,{'start','end','speed','reason','visual'},'保留片段')
        start=us(number(span.get('start'),0,source_duration,'片段开始'))
        end=us(number(span.get('end'),0,source_duration,'片段结束'))
        require(start<end,'保留片段长度必须大于零')
        require(all(end<=us(assets[k]['duration']) for k in ['avatar','narration']), '保留区间超过人物或声音的实际长度')
        speed=number(span.get('speed',1),.25,4,'速度')
        length=round((end-start)/speed)
        require(length>=1e6/fmt['fps'], '保留片段不得短于一帧')
        group=f'line-{i}'
        common={'start_us':cursor,'duration_us':length,'source_start':start/1e6,'speed':speed,'sync_group':group}
        style=visual(span.get('visual',plan.get('presenter',{})),length/1e6,fmt['width'])
        result.append(dict(common,id=f'avatar-{i}',kind='video',role='avatar',track=0,asset='avatar',volume=0,visual=style))
        result.append(dict(common,id=f'voice-{i}',kind='audio',role='narration',track=10,asset='narration',volume=1,fade_in=0,fade_out=0))
        for n,cue in enumerate(cues):
            a,b=us(cue['start']),us(cue['end'])
            if b<=start or a>=end: continue
            require(a>=start and b<=end, '剪口穿过字幕/发音区间；请选择句间边界或先提供校验过的精细对齐')
            text=replacements.get(str(n),cue['text'])
            require(isinstance(text,str) and text.strip() and len(text)<=2000,'字幕不能为空或过长')
            at=cursor+round((a-start)/speed);stop=min(cursor+length,cursor+round((b-start)/speed))
            item={'id':f'caption-{i}-{n}','kind':'text','role':'caption','track':100,
                  'start_us':at,'duration_us':stop-at,'text':text,'source_caption':n,
                  'visual':visual({'y':-.72,**cap.get('style',{})},(stop-at)/1e6,fmt['width'])}
            result.append(item);mapped.append({'start':at/1e6,'end':stop/1e6,'text':text})
        cursor+=length
    require(cursor<=3_600_000_000,'单条剪辑最长一小时')
    for collection, kinds in [('overlays',{'video','image','text'}),('audio',{'audio'})]:
        entries=plan.get(collection,[])
        require(isinstance(entries,list) and len(entries)<=500,'叠加片段列表过长')
        for i,raw in enumerate(entries):
            fields(raw,{'id','kind','asset','text','start','duration','source_start','speed','volume','track','visual','fade_in','fade_out'},'叠加片段')
            kind=raw.get('kind','audio' if collection=='audio' else None)
            require(kind in kinds,'叠加素材类型无效')
            cid=raw.get('id',f'{collection}-{i}')
            require(isinstance(cid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,70}',cid), '片段 ID 需要英文字母/数字/短横线')
            at=us(number(raw.get('start'),0,cursor/1e6,'叠加开始'))
            length=us(number(raw.get('duration'),1/fmt['fps'],cursor/1e6,'叠加时长'))
            require(at+length<=cursor,'叠加片段超出人物口播时间轴')
            track=raw.get('track',20+i if kind=='audio' else (110+i if kind=='text' else 1+i))
            require(type(track) is int and (20<=track<100 if kind=='audio' else 110<=track<=999 if kind=='text' else 1<=track<10),'轨道编号不在该类型范围')
            item={'id':cid,'kind':kind,'role':'supplement','track':track,'start_us':at,'duration_us':length}
            if kind=='text':
                require(isinstance(raw.get('text'),str) and 0<len(raw['text'].strip())<=2000,'标题文字无效')
                item['text']=raw['text']
            else:
                aid=raw.get('asset');require(aid in assets and assets[aid]['kind']==kind,'素材未登记或类型不符')
                item.update(asset=aid,source_start=number(raw.get('source_start',0),0,3600,'素材入点'),
                            speed=number(raw.get('speed',1),.25,4,'素材速度'),volume=0 if kind!='audio' else number(raw.get('volume',.15),0,2,'音量'))
                if kind=='image': require(item['source_start']==0 and item['speed']==1,'图片不能设置入点或变速')
                else: require(item['source_start']+length/1e6*item['speed']<=assets[aid]['duration']+.00001,'素材长度不足，不能静默循环/截断')
            if kind!='audio': item['visual']=visual(raw.get('visual',{}),length/1e6,fmt['width'])
            else:
                require('visual' not in raw,'音频片段不能设置画面效果')
                for key in ['fade_in','fade_out']: item[key]=number(raw.get(key,0),0,length/1e6,key)
                require(item['fade_in']+item['fade_out']<=length/1e6,'音频淡入淡出不能重叠')
            result.append(item)
    require(len({c['id'] for c in result})==len(result),'片段 ID 重复')
    for track in {c['track'] for c in result}:
        clips=sorted((c for c in result if c['track']==track),key=lambda c:c['start_us'])
        require(all(a['start_us']+a['duration_us']<=b['start_us'] for a,b in zip(clips,clips[1:])),'同轨片段重叠；叠画请使用不同轨道')
    return {'schema':'digital-human-timeline/v1','format':deepcopy(fmt),'duration':cursor/1e6,
            'duration_us':cursor,'clips':sorted(result,key=lambda c:(c['track'],c['start_us'])),
            'assets':deepcopy(assets),'captions':mapped,'scenes':[],
            'timing_basis':'source acoustic cues; integer microseconds, renderer samples at project fps'}
