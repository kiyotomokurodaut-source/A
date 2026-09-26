import unittest
from pathlib import Path
import re
import random
from netlify_prepare_r17 import make_headers
from refresh_hub_r17 import entries,refresh
from fingerprint_assets_r17 import refresh as refresh_assets
ROOT=Path(__file__).resolve().parents[1]
class R17Tests(unittest.TestCase):
 def test_math_cases(self):
  random.seed(17)
  for a in [-1,0,2,3]+[random.uniform(-10,10) for _ in range(500)]:
   m=1+2*a if a < -1 else -a*a if a<=2 else 4-4*a
   xs=[-1,2]+([a] if -1<=a<=2 else [])
   self.assertAlmostEqual(m,min(x*x-2*a*x for x in xs))
   n=2 if a<0 else 2-a*a if a<=3 else 11-6*a
   xs=[0,3]+([a] if 0<=a<=3 else [])
   self.assertAlmostEqual(n,min(x*x-2*a*x+2 for x in xs))
 def test_weekly_totals(self):
  self.assertEqual(sum([20*6,90*3,60*4,60*3,45*6,60]),1140)
  self.assertEqual(24*60-1140,300)
 def test_english_model(self):
  html=(ROOT/'public/study-guides/todai-english-writing/index.html').read_text()
  m=re.search(r'<p[^>]*id="r17-writing-model"[^>]*>(.*?)</p>',html,re.S)
  self.assertIsNotNone(m);self.assertEqual(len(m.group(1).split()),72)
 def test_headers(self):
  self.assertNotIn('X-Robots-Tag: noindex',make_headers(ROOT,'production'))
  for ctx in ['deploy-preview','branch-deploy','dev']:
   self.assertIn('X-Robots-Tag: noindex, nofollow',make_headers(ROOT,ctx))
  self.assertNotIn('/assets/*',make_headers(ROOT,'production'))
 def test_catalogue_repeatable(self):
  path=ROOT/'public/study-guides/index.html';before=path.read_bytes()
  items=entries(ROOT);self.assertTrue(len(items)>0)
  self.assertEqual(refresh(ROOT),len(items));self.assertEqual(before,path.read_bytes())
 def test_asset_fingerprints_repeatable(self):
  self.assertEqual(refresh_assets(ROOT),0)
if __name__=='__main__':unittest.main()
