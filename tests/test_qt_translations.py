import tempfile
import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.scanner import _is_xml_ts, scan_repository
from scripts.canonical_json import canonical_json_bytes


class QtTranslationTests(unittest.TestCase):
    def test_bounded_positive_headers_and_typescript_negatives(self):
        for content in [
            b'<?xml version="1.0"?><!DOCTYPE TS><TS version="2.1">',
            b'\xef\xbb\xbf  <!-- translation -->\n<?xml version="1.0"?>',
            b'<!DOCTYPE TS><TS version="2.1">',
            b'<TS version="2.1" language="ko">',
            b"<TS version = '2.1' language='en'>",
            b'<!DOCTYPE TS SYSTEM "https://invalid.example/no-fetch">',
        ]:
            with self.subTest(content=content):
                self.assertTrue(_is_xml_ts(content))
        for content in [
            b'const xml = `<?xml version="1.0"?><TS version="2.1">`;',
            b'// <?xml version="1.0"?>\nexport const n = 1;',
            b'/* <TS version="2.1"> */\nexport const n = 1;',
            b'<TS>value;', b'<T>(value: T) => value;',
            b'<!-- incomplete', b'<?xml', b'<TS version="', b'<!DOCTYPE TSX>',
        ]:
            with self.subTest(content=content):
                self.assertFalse(_is_xml_ts(content))

    def test_xml_is_structural_not_jsts_even_with_import_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'translations.ts').write_text(
                '<?xml version="1.0"?><!DOCTYPE TS><TS version="2.1">'
                '<context><message><source>import "./target";</source></message></context></TS>',
                encoding='utf-8')
            (root/'target.ts').write_text('export const n = 1;', encoding='utf-8')
            (root/'main.ts').write_text('import "./target";', encoding='utf-8')
            scan = scan_repository(root)
            self.assertEqual({f.path:f.language for f in scan.files},
                {'main.ts':'typescript', 'target.ts':'typescript', 'translations.ts':'xml'})
            first = analyze_repository(root, 'fixture/qt')
            second = analyze_repository(root, 'fixture/qt')
            self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
            imports = [e for e in first['edges'] if e['type'] == 'IMPORTS']
            self.assertEqual(len(imports), 1)
            self.assertIn('main.ts', imports[0]['from'])
            coverage = next(d for d in first['diagnostics'] if d['code'] == 'ANALYZER_COVERAGE')
            self.assertIn('2 JavaScript/TypeScript', coverage['message'])
            self.assertIn('1 file(s) remain structural-only', coverage['message'])
            scene = generate_city(first)
            self.assertEqual(len(scene['buildings']), 3)
            self.assertTrue(all(b['archetype'] == 'GENERIC_BUILDING' for b in scene['buildings']))

    def test_xml_discriminator_does_not_change_tsx_and_never_reads_doctype(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            declaration = '<!DOCTYPE TS SYSTEM "file:///nonexistent/never-read"><TS/>'
            (root/'qt.ts').write_text(declaration, encoding='utf-8')
            (root/'component.tsx').write_text('const node = <TS version="2.1"/>;', encoding='utf-8')
            self.assertEqual({f.path:f.language for f in scan_repository(root).files},
                             {'component.tsx':'typescript', 'qt.ts':'xml'})


if __name__ == '__main__':
    unittest.main()
