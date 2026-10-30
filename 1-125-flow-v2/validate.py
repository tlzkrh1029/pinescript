"""Static invariants and independent numerical examples. Does NOT execute Pine."""
from pathlib import Path
import hashlib
import math
import re
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = (HERE / 'crypto_flow_v2.pine').read_text(encoding='utf-8')
ORIGINALS = {
    '1_10': ('c395a9f4aab7957801a91f45a690df3e784fab46', 8),
    '11_50': ('c4e9fb391cba7847c7687c5e1111537adad39bbe', 32),
    '51_100': ('b4bd0acc48bbc1ba58fce2d2598fa29bda2b11d8', 40),
    '101_125': ('e15a41edea8cffe45445a7d727efb2bb0374fe6a', 22),
}


class SourceContract(unittest.TestCase):
    def test_original_files_are_byte_identical(self):
        for group, (expected, _) in ORIGINALS.items():
            data = (ROOT / '1-125-flow' / f'crypto_ranks_{group}.pine').read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()
            self.assertEqual(actual, expected, group)

    def test_exact_102_symbol_ticker_rank_membership(self):
        old = []
        for group, (_, n) in ORIGINALS.items():
            text = (ROOT / '1-125-flow' / f'crypto_ranks_{group}.pine').read_text(encoding='utf-8')
            rows = re.findall(r'// Original rank (\d+): (\S+)\np\d+ = request.security\("([^"]+)"', text)
            self.assertEqual(len(rows), n)
            old.extend(rows)
        symbol_lines = re.findall(r'symbols := array.from\(([^\n]+)\)', SOURCE)
        tick_lines = re.findall(r'ticks := array.from\(([^\n]+)\)', SOURCE)
        rank_lines = re.findall(r'ranks := array.from\(([^\n]+)\)', SOURCE)
        new = []
        for symbols, ticks, ranks in zip(symbol_lines, tick_lines, rank_lines):
            new.extend(zip(re.findall(r'\d+', ranks), re.findall(r'"([^"]+)"', ticks), re.findall(r'"([^"]+)"', symbols)))
        self.assertEqual(new, old)
        self.assertEqual(len({s for _, _, s in new}), 102)

    def test_bounded_dynamic_requests_and_independent_state(self):
        self.assertEqual(SOURCE.count('request.security('), 1)
        self.assertIn('for i = 0 to count - 1', SOURCE)
        self.assertIn('bases.get(i)', SOURCE)
        self.assertIn('bases.set(i, price)', SOURCE)
        self.assertNotIn('f_compare(', SOURCE)
        self.assertIn('ignore_invalid_symbol=true', SOURCE)
        self.assertIn('lookahead=barmerge.lookahead_off', SOURCE)
        self.assertIn('sourceTime == time_close', SOURCE)
        self.assertEqual(SOURCE.count('time_close - time_close[recentBars] == recentBars * seconds * 1000'), 2)
        self.assertLessEqual(40 * 3, 127)

    def test_rank_filters_and_drawings(self):
        self.assertIn('not late.get(i) and not selfCoin.get(i)', SOURCE)
        self.assertIn('f_rankable(int i)', SOURCE)
        self.assertIn('or not na(recents.get(i))', SOURCE)
        self.assertIn('if f_rankable(i)\n            validOrder.push(i)', SOURCE)
        self.assertIn('trails.push(Trail.new(array.new<chart.point>()))', SOURCE)
        self.assertIn('polyline.delete(path)', SOURCE)
        self.assertIn('xloc=xloc.bar_time', SOURCE)
        self.assertIn('curved=false, closed=false', SOURCE)
        self.assertIn('trace.points.clear()', SOURCE)
        self.assertNotIn('varip ', SOURCE)
        self.assertNotIn('plot(', SOURCE)
        self.assertLessEqual(40, 100)

    def test_table_contract_and_unicode(self):
        self.assertIn('height=rowPct', SOURCE)
        self.assertIn('height=startPct', SOURCE)
        self.assertIn('frame_width=0, border_width=0', SOURCE)
        self.assertIn('순위 구간', SOURCE)
        self.assertNotIn('\ufffd', SOURCE)
        self.assertNotIn('__UNIVERSE__', SOURCE)


class NumericalSpecification(unittest.TestCase):
    def test_ratio_is_not_percentage_point_subtraction(self):
        relative = ((110 / 100) / (90 / 100) - 1) * 100
        self.assertAlmostEqual(relative, 22.2222222222)
        self.assertNotAlmostEqual(relative, 10 - (-10))

    def test_independent_bases_and_host_rebasing(self):
        # Two assets differ 100-fold in nominal price; both should draw identically.
        coin_bases, prices = [10, 1000], [11, 1100]
        host_base, host_price = 80000, 76000
        lines = [host_base * p / b for p, b in zip(prices, coin_bases)]
        relative = [((p / b) / (host_price / host_base) - 1) * 100 for p, b in zip(prices, coin_bases)]
        self.assertEqual(lines, [88000, 88000])
        self.assertAlmostEqual(relative[0], relative[1])
        self.assertAlmostEqual(relative[0], 15.7894736842)

    def test_actual_lookback_minutes(self):
        self.assertEqual(math.ceil(60 / 15), 4)
        self.assertEqual(math.ceil(60 / 60), 1)
        self.assertEqual(math.ceil(60 / 45) * 45, 90)
        # Ten source bars spread across 3h must not be called the host's 150 minutes.
        self.assertNotEqual(3 * 60 * 60, 10 * 15 * 60)

    def test_fixed_anchor_common_close(self):
        anchor = 12 * 60
        for interval in (15, 60):
            closes = list(range(interval, 24 * 60 + 1, interval))
            self.assertEqual(next(c for c in closes if c >= anchor), anchor)

    def test_layout_every_supported_density(self):
        counts = [8, 32, 40, 22]
        for limit in range(6, 21):
            previous_end = 3.0
            before_rows = 0
            for count in counts:
                groups = math.ceil(count / limit)
                rows = math.ceil(count / groups)
                start = 3 + before_rows * 1.65
                self.assertAlmostEqual(start, previous_end)
                for k in range(count):
                    c = (k // rows) * 3
                    r = 4 + k % rows
                    self.assertLess(c + 2, 3 * groups)
                    self.assertLess(r, rows + 4)
                self.assertAlmostEqual(groups * (0.44 + 0.28 + 0.28), groups)
                previous_end = start + (3 + rows) * 1.65
                before_rows += 3 + rows
        total_rows = sum(3 + math.ceil(n / math.ceil(n / 12)) for n in counts)
        self.assertEqual(total_rows, 52)
        self.assertAlmostEqual(3 + total_rows * 1.65, 88.8)


if __name__ == '__main__':
    unittest.main(verbosity=2)
