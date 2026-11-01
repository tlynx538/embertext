import unittest

from editing import find_next, replace_all, syntax_spans


class EditingTests(unittest.TestCase):
    def test_find_wraps_and_is_case_insensitive(self):
        self.assertEqual(find_next('Alpha beta ALPHA', 'alpha', 6), (11, 16))
        self.assertEqual(find_next('Alpha beta ALPHA', 'alpha', 16), (0, 5))
        self.assertIsNone(find_next('abc', 'missing', 0))
        self.assertIsNone(find_next('abc', '', 0))

    def test_replace_all_literal_case_insensitive_and_empty_guard(self):
        self.assertEqual(replace_all('Foo food FOO', 'foo', 'x'), ('x xd x', 3))
        self.assertEqual(replace_all('one', '', 'x'), ('one', 0))

    def test_highlighting_known_suffix_only_and_size_limit(self):
        self.assertIn(('keyword', 0, 3), syntax_spans('def f():\n  return 1', '.py'))
        self.assertEqual(syntax_spans('def f()', '.madeup'), [])
        self.assertEqual(syntax_spans('def ' * 60000, '.py'), [])

    def test_python_highlights_standard_keywords_but_not_names_inside_strings(self):
        self.assertIn(('keyword', 0, 5), syntax_spans('break = "break"', '.py'))
        self.assertNotIn(('keyword', 9, 14), syntax_spans('break = "break"', '.py'))

    def test_suffix_specific_syntax_does_not_mislabel_markup_or_json(self):
        self.assertEqual(syntax_spans('# Heading\n<script>// hi</script>', '.md'), [])
        self.assertEqual(syntax_spans('<tag>#literal</tag>', '.html'), [])
        self.assertEqual(syntax_spans('<tag>#literal</tag>', '.xml'), [])
        self.assertEqual(syntax_spans('{"url":"https://example.com/#fragment"}', '.json'),
                         [('string', 1, 6), ('string', 7, 38)])
        self.assertEqual(syntax_spans('const x = 1; // note', '.js'),
                         [('keyword', 0, 5), ('comment', 13, 20)])


if __name__ == '__main__':
    unittest.main()
