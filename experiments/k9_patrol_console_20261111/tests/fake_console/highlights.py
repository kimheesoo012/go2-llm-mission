"""Excerpt of the console's highlights.py selection path (compact / validate_selection / ask / _select),
copied from heesoo-standing-rule-llm-speed.patch (11/07) so that eval/selection_eval.py can be
exercised without the console. The prompt text is replaced by a placeholder.
"""
import json
from ollama_connection import chat

OPTIONS={'temperature':0,'num_ctx':8192}
KEEP_ALIVE='30m'
SYSTEM='(test fixture)'


def compact(sources):
    aliases={f'r{i}':s for i,s in enumerate(sources,1)}
    rows=[]
    for alias,s in aliases.items():
        row={'id':alias}
        for e in s['evidence']:
            row[e['id']]=e['text'][:19] if e['id']=='time' else e['text']+(' (일부 발췌)' if e['truncated'] else '')
        rows.append(row)
    return aliases,rows


def validate_selection(value, aliases, limit):
    if not isinstance(value,dict) or set(value)!={'selections'}:raise ValueError('선정 출력 형식 오류')
    rows=value['selections']
    if not isinstance(rows,list) or len(rows)>limit:raise ValueError('선정 개수 오류')
    seen=set();out=[]
    for item in rows:
        if not isinstance(item,dict) or set(item)!={'id','reason','evidence'}:raise ValueError('선정 항목 형식 오류')
        alias=item['id']
        if not isinstance(alias,str) or alias not in aliases or alias in seen:raise ValueError('잘못되거나 중복된 원본 기록 참조')
        seen.add(alias)
        if not isinstance(item['reason'],str) or not 1<=len(item['reason'].strip())<=700:raise ValueError('선택 이유 형식 오류')
        ids=item['evidence'];allowed={e['id'] for e in aliases[alias]['evidence']}
        if not isinstance(ids,list) or not 1<=len(ids)<=6 or any(not isinstance(x,str) for x in ids):raise ValueError('근거 참조 형식 오류')
        if len(ids)!=len(set(ids)) or any(x not in allowed for x in ids):raise ValueError('존재하지 않는 근거 참조')
        if all(x=='time' for x in ids):raise ValueError('시각 외의 발화·사람·자세 근거가 필요합니다.')
        out.append(dict(record_id=aliases[alias]['record_id'],reason=item['reason'],evidence_ids=ids))
    return out


def ask(model, system, data, schema, num_predict):
    payload=dict(model=model,stream=False,format=schema,keep_alive=KEEP_ALIVE,
                 messages=[{'role':'system','content':system},{'role':'user','content':json.dumps(data,ensure_ascii=False)}],
                 options=dict(OPTIONS,num_predict=num_predict))
    if model.lower().startswith(('qwen3:', 'qwen3.', 'qwen3-')):payload['think']=False
    return json.loads(chat(payload)['message']['content'])


class HighlightsService:
    def _select(self,sources,model,limit):
        aliases,rows=compact(sources)
        schema={'type':'object'}
        return validate_selection(ask(model,SYSTEM,{'max_selections':limit,'records':rows},schema,64+110*limit),aliases,limit)
