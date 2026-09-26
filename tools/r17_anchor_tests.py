import unittest
from fix_faq_anchor_r17 import Markup, repair


class FAQAnchorRegressionTests(unittest.TestCase):
    def test_duplicate_consult_keeps_first_and_preserves_text_and_links(self):
        # Mirrors the source structure: table-of-contents anchor, FAQ section, CTA.
        raw = '<main><a href="#consult">無料受験戦略診断について</a><section id="consult"><h2>無料受験戦略診断について</h2><p>相談できます。</p></section><div class="cta-box" id="consult"><h2>ご相談ください。</h2><a href="/contact/">無料相談</a></div></main>'
        updated, report = repair(raw)
        self.assertTrue(report['changed'])
        self.assertIn('<section id="consult">', updated)
        self.assertIn('class="cta-box" id="consult-secondary"', updated)
        self.assertEqual(Markup(raw).text, Markup(updated).text)
        self.assertEqual(Markup(raw).links, Markup(updated).links)
        self.assertEqual(repair(updated)[0], updated)
        self.assertFalse(repair(updated)[1]['changed'])

    def test_single_anchor_is_not_modified(self):
        raw = '<section id="consult"><p>本文</p></section>'
        self.assertEqual(repair(raw)[0], raw)

    def test_new_name_collision_stops(self):
        with self.assertRaises(ValueError):
            repair('<p id="consult"></p><p id="consult"></p><p id="consult-secondary"></p>')

    def test_unexpected_count_stops(self):
        for raw in ('<p>none</p>', '<p id="consult"></p>' * 3):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                repair(raw)

    def test_other_duplicate_is_not_suppressed(self):
        with self.assertRaisesRegex(ValueError, 'Other duplicate'):
            repair('<p id="consult"></p><p id="consult"></p><p id="other"></p><p id="other"></p>')

    def test_quote_variants_and_japanese_offsets(self):
        for attribute in ('id="consult"', "id='consult'", 'id=consult', "ID = 'consult'"):
            with self.subTest(attribute=attribute):
                raw = '日本語\n<header id="consult">前半</header>\n<section class="x" ' + attribute + '>後半</section>'
                updated, _ = repair(raw)
                self.assertEqual(updated.replace('consult-secondary', 'consult'), raw)
                self.assertEqual([x[0] for x in Markup(updated).elements], ['consult', 'consult-secondary'])

    def test_script_and_comment_text_not_treated_as_elements(self):
        raw = '<script>const x = \'<p id="consult">\';</script><!-- id="consult" --><p id="consult">先</p><p id="consult">後</p>'
        updated, _ = repair(raw)
        self.assertIn('<script>const x = \'<p id="consult">\';</script>', updated)
        self.assertEqual(Markup(updated).text, Markup(raw).text)

    def test_existing_fragment_links_unchanged(self):
        raw = '<a href="/faq/#consult">相談</a><p id="consult"></p><a href="#consult">目次</a><p id="consult"></p>'
        updated, _ = repair(raw)
        self.assertEqual(Markup(updated).links, ['/faq/#consult', '#consult'])


if __name__ == '__main__':
    unittest.main()
