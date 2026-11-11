"""Test double for the console's ollama_connection: a scripted model, no network."""
import json

calls = []


def start_background():
    pass


def chat(payload):
    """Pretends to be a careless model: always picks the first two records."""
    calls.append(payload)
    data = json.loads(payload['messages'][-1]['content'])
    picked = [dict(id=r['id'], reason='가짜 모델의 선정 이유', evidence=[k for k in ('speech', 'person', 'pose') if k in r][:1])
              for r in data['records'][:min(2, data['max_selections'])]]
    return {'message': {'content': json.dumps({'selections': picked}, ensure_ascii=False)}}
