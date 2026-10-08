import json
import re
import sys

cand=[]


if __name__ == "__main__":

    src,dst=sys.argv[1],sys.argv[2]
    for l in open(src,errors="ignore"):
        try:o=json.loads(l)
        except:continue
        m=o.get("message") if isinstance(o,dict) else None
        if isinstance(m,dict) and m.get("role")=="assistant" and isinstance(m.get("content"),list):
            for b in m["content"]:
                if b.get("type")=="tool_use" and "andback" in b.get("name",""):
                    inp=b.get("input",{}); cand.append(json.dumps(inp) if not isinstance(inp,str) else inp); cand[-1]=inp
                if b.get("type")=="text" and b.get("text","").strip(): cand.append(b["text"])
    if not cand: print("nothing found"); sys.exit(1)
    last=cand[-1]
    if isinstance(last,dict):
        last=next((v for v in last.values() if isinstance(v,str) and len(v)>200),json.dumps(last))
    s=re.sub(r"^```(?:json)?\s*|\s*```$","",last.strip())
    i=s.find("{"); s=s[i:]
    try:
        d=json.loads(s); json.dump(d,open(dst,"w")); print("ok", {k:len(v) for k,v in d.items()})
    except Exception as e:
        open(dst+".raw","w").write(last); print("invalid json:",e,"len",len(last))
