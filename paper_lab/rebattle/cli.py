import argparse
from .config import load_config
from .utils import read_text_ro
from .backends import MockBackend, AG2Backend
from .engine import ReBattleEngine
from .audit import EvidenceAuditRunner

JUDGES=['national_modeling_judge','math_rigor_judge','evidence_repro_judge','writing_clarity_judge','devil_advocate_judge']

def main():
    ap=argparse.ArgumentParser(description='Math Modeling ReBattle + CUMCM Evidence Audit')
    ap.add_argument('--paper',required=True); ap.add_argument('--problem',required=True)
    ap.add_argument('--config',default='config.yaml'); ap.add_argument('--out',default='runs/rebattle')
    ap.add_argument('--mock',action='store_true')
    ap.add_argument('--audit-only',action='store_true',help='只执行 CUMCM Evidence Audit，不进入 ReBattle')
    args=ap.parse_args()
    paper=read_text_ro(args.paper); problem=read_text_ro(args.problem)
    if args.mock:
        model_map={'judges':{k:'mock' for k in JUDGES},'audit_model':'mock','rebuttal_model':'mock','chair_model':'mock'}
        backend=MockBackend(); diff='strict'
    else:
        cfg=load_config(args.config); rb=cfg['rebattle']
        model_map={'judges':rb['judges'],'audit_model':rb.get('audit_model',rb['chair_model']),'rebuttal_model':rb['rebuttal_model'],'chair_model':rb['chair_model']}
        backend=AG2Backend(cfg['models']); diff=rb.get('difficulty','strict')
    if args.audit_only:
        idx,audit,check=EvidenceAuditRunner(backend,model_map['audit_model']).run(paper=paper,problem=problem,out_dir=args.out)
        score=audit.score_summary.normalized_score if audit.score_summary else None
        print(f'Evidence Audit complete: gate={check["passed"]}, score={score} -> {args.out}')
        return
    chair=ReBattleEngine(backend,model_map,diff).run(paper,problem,args.out)
    print(f'ReBattle complete: {chair.decision} -> {args.out}')

if __name__=='__main__': main()
