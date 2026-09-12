import unittest
from paper_lab.rebattle.schemas import Review, Issue
from paper_lab.rebattle.ledger import build_issue_ledger
class T(unittest.TestCase):
  def test_dedupe(self):
    a=Review(judge_type='a',issues=[Issue(summary='未来数据泄露',detail='x',severity='serious',category='methods')])
    b=Review(judge_type='b',issues=[Issue(summary='未来数据泄露问题',detail='y',severity='fatal',category='methods')])
    xs=build_issue_ledger([a,b],.6)
    self.assertEqual(len(xs),1); self.assertEqual(xs[0].id,'ISS-001'); self.assertEqual(xs[0].severity,'fatal'); self.assertEqual(set(xs[0].raised_by),{'a','b'})
if __name__=='__main__': unittest.main()
