import unittest
from paper_lab.rebattle.audit_schemas import ProblemIndex, EvidenceAudit
from paper_lab.rebattle.audit_checker import check_audit_consistency, compute_score
from paper_lab.rebattle.audit_rules import DIMENSION_WEIGHTS
from paper_lab.rebattle.backends import MockBackend
from paper_lab.rebattle.audit import EvidenceAuditRunner
import tempfile
from pathlib import Path


def mock_objects():
    b=MockBackend()
    idx=ProblemIndex.model_validate(b.complete(agent_name='problem_indexer',model_key='mock',system_prompt='',user_prompt=''))
    aud=EvidenceAudit.model_validate(b.complete(agent_name='evidence_auditor',model_key='mock',system_prompt='',user_prompt=''))
    aud.score_summary=compute_score(aud)
    return idx,aud

class AuditTests(unittest.TestCase):
    def test_valid_mock_audit_passes_gate(self):
        idx,aud=mock_objects()
        check=check_audit_consistency(idx,aud)
        self.assertTrue(check['passed'],check['errors'])
        self.assertTrue(check['score_summary']['score_allowed'])
        self.assertEqual(check['score_summary']['normalized_score'],75.0)

    def test_missing_requires_global_search_scope(self):
        idx,aud=mock_objects()
        d=next(x for x in aud.dimensions if x.name=='验证与稳健性')
        d.status='missing'; d.score=0; d.evidence_ids=['E001']
        check=check_audit_consistency(idx,aud)
        self.assertFalse(check['passed'])
        self.assertTrue(any('global_search' in e for e in check['errors']))

    def test_under_80pct_coverage_suppresses_score(self):
        idx,aud=mock_objects()
        for name in ['模型选择与适配','验证与稳健性']:
            d=next(x for x in aud.dimensions if x.name==name)
            d.status='unverifiable'; d.score=None
        s=compute_score(aud)
        self.assertLess(s.coverage_ratio,0.8)
        self.assertFalse(s.score_allowed)
        self.assertIsNone(s.normalized_score)

    def test_runner_writes_fixed_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            idx,aud,check=EvidenceAuditRunner(MockBackend(),'mock').run(paper='paper',problem='problem',out_dir=d)
            self.assertTrue(check['passed'])
            for name in ['problem_index.json','audit.json','consistency.json','audit_report.md']:
                self.assertTrue((Path(d)/name).exists(),name)

if __name__=='__main__': unittest.main()
