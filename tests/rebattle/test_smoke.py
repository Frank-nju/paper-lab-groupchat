import unittest, tempfile
from pathlib import Path
from paper_lab.rebattle.engine import ReBattleEngine
from paper_lab.rebattle.backends import MockBackend
class T(unittest.TestCase):
  def test_full_flow(self):
    m={'judges':{k:'mock' for k in ['national_modeling_judge','math_rigor_judge','evidence_repro_judge','writing_clarity_judge','devil_advocate_judge']},'rebuttal_model':'mock','chair_model':'mock'}
    with tempfile.TemporaryDirectory() as d:
      c=ReBattleEngine(MockBackend(),m).run('paper','problem',d)
      self.assertEqual(c.decision,'major_revise')
      for f in ['evidence_audit/problem_index.json','evidence_audit/audit.json','evidence_audit/consistency.json','evidence_audit/audit_report.md','issues.json','rebuttal.json','chair_decision.json','report.md']:
        self.assertTrue((Path(d)/f).exists())
if __name__=='__main__': unittest.main()
