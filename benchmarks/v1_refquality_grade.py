"""Grades the 3 quality conditions of Option C. Answers are the subagents' replies transcribed; cases come from v1_refquality_build.py (seed 11)."""
import json,re
cases=json.load(open("/private/tmp/claude-501/refquality_cases.json"))
A={}  # condition -> {(case,line): text}
def mk(items): return {(c,l):t for c,l,t in items}
D='description: "Status and architecture of the Kálix videogame project (Godot top-down action game, narrative system archived)"'
common={
(0,3):D,(0,14):"**Current architecture (as of 2026-07-08):**",(1,5):"## tocarlo — esa localización todavía no está construida.",
(2,24):"  [OK] Llego al escritorio objetivo evitando desktops/estudiante",(2,28):"  [OK] No se salio de la plataforma (no se cayo)",
(3,31):"  [OK] No alcanzo el objetivo mas alla del borde (correcto)",(3,30):"  [OK] No se salio de la plataforma (no se cayo)",
(5,8):"[debug vision] to_player=(-100.0, 0.0) distance=100.0 facing=(-1.0, 0.0) angle_diff=0.00000865142221 ray_colliding=false",
(5,6):"[disparo] proyectiles antes=0 despues=1 disparo_ok=true",
(6,7):"c1b6e3a DEC-014: spatial block in the episode + analyze-2.0.0 prompt, evidence-gated",
(6,9):"71ac4cf ISSUE-016: analyze/reanalyze/extract/review are administrator-only (x-admin-key)",
(7,14):'[sub_resource type="RectangleShape2D" id="exit_shape"]',(7,5):'[ext_resource type="PackedScene" path="res://scenes/action/enemy/enemy.tscn" id="3"]',
(8,6):";   [section] ; section goes between []",(8,7):";   param=value ; assign values to parameters",
(9,20):'              <div className="font-semibold text-cream mb-2">Legal</div>',(9,4):"export default function Footer() {",
(10,16):"-rw-r--r--@  1 darwingperez  staff     8196 Jul  6 06:04 .DS_Store",(10,20):"-rw-r--r--@  1 darwingperez  staff      946 Jul  5 21:10 Baldora.png.import",
(11,13):"## Otros proyectos del estudio (sitios propios)",(11,18):"## Notas para agentes de IA"}
full=dict(common); full.update({(1,3):"## dejar el mapa con solo un punto navegable) pero no hace nada al",(4,46):"daralaz-project-1-key afbbb0b4d5774a00e238ce0d691866e8 d Today, 16:25:09",(4,52):"- Executed on tabId: 1439533014"})
leg=dict(common); leg.update({(1,3):"## location_scene_path está vacío, el marcador existe visualmente (para no",(4,46):"NAME HMAC KEY CREATED BY CREATED DEVELOPMENT KEY",(4,52):"Tab Context:"})
nol=dict(common); nol.update({(1,3):"## location_scene_path está vacío, el marcador existe visualmente (para no",(4,46):"daralaz-project-1-key afbbb0b4d5774a00e238ce0d691866e8 d Today, 16:25:09",(4,52):"- Executed on tabId: 1439533014"})
norm=lambda s:re.sub(r"^\d+\t","",s).strip()
for name,ans in [("full text",full),("pointers + legend",leg),("pointers, no legend",nol)]:
    ok=0;bad=[]
    for i,c in enumerate(cases):
        for q in c["qs"]:
            truth=norm(q["answer"])
            if norm(ans[(i,q["line"])])==truth.strip(): ok+=1
            else: bad.append((i,q["line"],truth.strip()[:60],norm(ans[(i,q["line"])])[:60]))
    print(f"{name:22} {ok}/24")
    for b in bad: print("   miss",b)
