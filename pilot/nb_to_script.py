"""Turn the pilot notebook's code cells into a plain script that also saves its data.
Usage: python nb_to_script.py notebook.ipynb out.py"""
import json, sys
nb = json.load(open(sys.argv[1], encoding='utf-8'))
parts = ["import matplotlib\nmatplotlib.use('Agg')\n"]
for c in nb['cells']:
    if c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    lines = [l for l in src.split('\n') if not l.lstrip().startswith('!')]
    src = '\n'.join(lines)
    parts.append(src)
    if 'log = pd.DataFrame' in src:
        parts.append("log.to_csv('log.csv', index=False)")
    if 'per_seed = pd.DataFrame(records)' in src:
        parts.append("per_seed.to_csv('per_seed.csv', index=False)\nsummary.to_csv('summary.csv')\nprint(summary.to_string())")
    if 'sens = pd.DataFrame(sens)' in src:
        parts.append("sens.to_csv('sens.csv', index=False)\nprint(sens.round(3).to_string())")
open(sys.argv[2], 'w', encoding='utf-8').write('\n\n'.join(parts))
