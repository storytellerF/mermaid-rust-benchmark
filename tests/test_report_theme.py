"""Browser theme checks: install Playwright and Chrome, then run this file."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_report import BENCHMARKS, generate_html, load_crate_meta

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'optional Playwright browser checks')
class ReportThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.report = Path(cls.directory.name) / 'report.html'
        results = [dict(group=group, bench=bench, median_ns=1000 * (i + 1),
                        ci_lower_ns=900 * (i + 1), ci_upper_ns=1100 * (i + 1))
                   for i, group in enumerate(load_crate_meta()) for bench in BENCHMARKS]
        generate_html(results, str(cls.report))
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='chrome', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.directory.cleanup()

    def setUp(self):
        self.page = self.browser.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.page.close()

    def assert_theme(self, theme):
        expected = 'rgb(15, 23, 42)' if theme == 'dark' else 'rgb(241, 245, 249)'
        self.page.wait_for_function('(color) => getComputedStyle(document.body).backgroundColor === color', arg=expected)
        self.assertEqual(self.page.locator('.fastest').count(), 3)
        self.assertEqual(self.page.locator('tbody tr').count(), 4)
        self.assertEqual(self.errors, [])
        # Check actual rendered text, including highlighted CI text, against its background.
        failures = self.page.evaluate('''() => {
            const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
            const luminance = value => rgb(value).map(v => {
                v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
            }).reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
            return [...document.querySelectorAll('td, th, a, .version, .ci, footer, h2, code, pre, .chart-error')].flatMap(el => {
                let parent = el;
                while (getComputedStyle(parent).backgroundColor === 'rgba(0, 0, 0, 0)') parent = parent.parentElement;
                const a = luminance(getComputedStyle(el).color);
                const b = luminance(getComputedStyle(parent).backgroundColor);
                const ratio = (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                return ratio < 4.5 ? [{text: el.textContent, ratio}] : [];
            });
        }''')
        self.assertEqual(failures, [])

    def test_initial_system_theme_and_reload(self):
        for theme in ('light', 'dark'):
            with self.subTest(theme=theme):
                self.page.emulate_media(color_scheme=theme)
                self.page.goto(self.report.as_uri())
                self.page.wait_for_function("typeof Chart !== 'undefined' && Chart.instances[0]")
                self.assert_theme(theme)
                self.page.reload()
                self.page.wait_for_function("typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 3")
                self.assert_theme(theme)

    def test_live_theme_updates_chart_and_page(self):
        self.page.goto(self.report.as_uri())
        self.page.wait_for_function("typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 3")
        for theme in ('dark', 'light', 'dark'):
            self.page.emulate_media(color_scheme=theme)
            self.assert_theme(theme)
            expected = '#f1f5f9' if theme == 'dark' else '#1e293b'
            self.page.wait_for_function('(color) => Object.values(Chart.instances).every(c => c.options.plugins.title.color === color)', arg=expected)
            self.assertEqual(self.page.evaluate('Object.values(Chart.instances).map(c => c.options.scales.x.ticks.color)'),
                             ['#cbd5e1' if theme == 'dark' else '#475569'] * 3)
            self.page.evaluate('''() => {
                const c = Object.values(Chart.instances)[0];
                c.tooltip.setActiveElements([{datasetIndex: 0, index: 0}], {x: 100, y: 100});
                c.update('none');

            }''')
            self.page.wait_for_function('Object.values(Chart.instances)[0].tooltip.opacity === 1')
            self.assertEqual(self.page.evaluate('Object.values(Chart.instances)[0].options.plugins.tooltip.bodyColor'),
                             '#0f172a' if theme == 'dark' else '#ffffff')

    def test_return_to_report_uses_current_preference(self):
        self.page.emulate_media(color_scheme='light')
        self.page.goto(self.report.as_uri())
        self.page.wait_for_function("typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 3")
        self.page.goto('about:blank')
        self.page.emulate_media(color_scheme='dark')
        self.page.go_back()
        self.assert_theme('dark')
        self.page.wait_for_function("Object.values(Chart.instances).every(c => c.options.plugins.title.color === '#f1f5f9')")

    def test_interaction_states_and_code_contrast(self):
        self.page.goto(self.report.as_uri())
        self.page.evaluate("document.querySelector('footer').insertAdjacentHTML('beforeend', '<pre><code>sample code</code></pre>')")
        for theme in ('light', 'dark'):
            self.page.emulate_media(color_scheme=theme)
            link = self.page.locator('.lib-name a').first
            link.hover()
            self.assert_theme(theme)
            link.focus()
            self.assertNotEqual(link.evaluate('(el) => getComputedStyle(el).outlineStyle'), 'none')

    def test_chart_download_failure_keeps_table_readable(self):
        self.page.route('**/chart.js@4', lambda route: route.abort())
        self.page.emulate_media(color_scheme='dark')
        self.page.goto(self.report.as_uri())
        self.assertEqual(self.page.locator('[role=status]').count(), 3)
        self.assert_theme('dark')


if __name__ == '__main__':
    unittest.main()
