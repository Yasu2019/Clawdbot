#!/usr/bin/env python3
import json, sys
weights = {'business_value':25,'safety':20,'implementation_ease':15,'cost_effectiveness':15,'clawstack_fit':15,'future_value':10}
data=json.load(open(sys.argv[1],encoding='utf-8'))
total=sum(min(max(int(data.get(k,0)),0),w) for k,w in weights.items())
risk=data.get('confidentiality_risk','medium')
if risk in ['high','blocked']: status='reject'
elif total >= 85: status='prod_candidate'
elif total >= 70: status='propose'
elif total >= 50: status='store_only'
else: status='watch'
print(json.dumps({'score':total,'adoption_status':status,'risk':risk},ensure_ascii=False,indent=2))
