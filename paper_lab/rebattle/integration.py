from .config import load_config
from .utils import read_text_ro
from .backends import AG2Backend
from .engine import ReBattleEngine
from .audit import EvidenceAuditRunner


def _runtime(paper_path, problem_path, config_path):
    cfg=load_config(config_path); rb=cfg['rebattle']
    paper=read_text_ro(paper_path, rb.get('max_paper_chars',120000)); problem=read_text_ro(problem_path,50000)
    backend=AG2Backend(cfg['models'])
    model_map={
        'judges':rb['judges'],
        'audit_model':rb.get('audit_model',rb['chair_model']),
        'rebuttal_model':rb['rebuttal_model'],
        'chair_model':rb['chair_model'],
    }
    return rb,paper,problem,backend,model_map


def run_evidence_audit_from_command(*, paper_path, problem_path, config_path='config.yaml', output_dir='runs/audit'):
    rb,paper,problem,backend,model_map=_runtime(paper_path,problem_path,config_path)
    return EvidenceAuditRunner(backend,model_map['audit_model']).run(paper=paper,problem=problem,out_dir=output_dir)


def run_rebattle_from_command(*, paper_path, problem_path, config_path='config.yaml', output_dir='runs/rebattle'):
    rb,paper,problem,backend,model_map=_runtime(paper_path,problem_path,config_path)
    return ReBattleEngine(backend,model_map,rb.get('difficulty','strict')).run(paper,problem,output_dir)
