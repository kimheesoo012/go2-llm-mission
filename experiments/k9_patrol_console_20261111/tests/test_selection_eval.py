import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKE = ROOT / 'tests' / 'fake_console'


def run(tmp_path, *args):
    out = tmp_path / 'result.md'
    p = subprocess.run([sys.executable, str(ROOT / 'eval' / 'selection_eval.py'), '--out', str(out), *args],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return out.read_text(encoding='utf-8')


def test_scenarios_file_is_consistent():
    data = json.loads((ROOT / 'eval' / 'selection_scenarios.json').read_text(encoding='utf-8'))
    assert len(data['scenarios']) == 10
    for s in data['scenarios']:
        ids = [r['id'] for r in s['records']]
        assert len(ids) == len(set(ids)) and len(ids) <= 40
        assert set(s['must']) <= set(ids) and set(s['must_not']) <= set(ids) and not set(s['must']) & set(s['must_not'])
        assert s['first'] is None or s['first'] in s['must']
        assert len(s['must']) <= s['limit']
        assert all(set(r) <= {'id', 'time', 'speech', 'person', 'pose'} for r in s['records'])


def test_rule_mode_passes_every_scenario(tmp_path):
    assert '통과 10/10' in run(tmp_path, '--mode', 'rule')


def test_llm_mode_runs_the_console_selection_path_and_catches_a_careless_model(tmp_path):
    text = run(tmp_path, '--mode', 'llm', '--console', str(FAKE))
    # The fake model always picks the first two records: it misses and picks ordinary ones.
    assert '통과 0/10' in text and '| 2 | 일상 기록만 | 10 | 없음 | r1, r2 | - | r1, r2 |' in text


def test_merged_mode_keeps_rule_picks_even_with_a_careless_model(tmp_path):
    text = run(tmp_path, '--mode', 'merged', '--console', str(FAKE))
    row1 = next(line for line in text.splitlines() if line.startswith('| 1 |'))
    assert '| r6, r5, r1, r2 | - | r1 |' in row1  # must records kept; the model's extra pick is still counted
    row8 = next(line for line in text.splitlines() if line.startswith('| 8 |'))
    assert '| r4, r1, r2 | - | r1, r2 |' in row8
