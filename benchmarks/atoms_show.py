import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl.atoms.schema import AtomGraph


def brief(g):
    s=[]
    for a in g.atoms:
        v=a.value if a.value is not None else ""
        s.append(f"{a.id}:{a.type[:4]}:{(a.concept or '').replace('ACT.','').replace('ENT.','').replace('PRP.','')}{v if v!='' else ''}{'/'+a.modality if a.modality not in (None,'DO') else ''}{'/-' if a.polarity!='+' else ''}{'/in '+a.scope if a.scope else ''}{'/'+a.status if a.status!='explicit' else ''}")
    return " ".join(s)+" | "+" ".join(f"{x}-{r}->{y}" for x,r,y in g.relations)
if __name__=="__main__":
    D=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data","atoms")
    texts={c["id"]:c for c in json.load(open(D+"/cases_dev.json"))}
    lo,hi=sys.argv[1],sys.argv[2]
    for l in open(D+"/gold_dev.jsonl"):
        r=json.loads(l)
        if lo<=r["id"]<=hi: print(r["id"],texts[r["id"]]["text"]); print("   ",brief(AtomGraph.from_dict(r)))
