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
        self.assertIn('frame_width=0, border_width=1, border_color=lineInk', SOURCE)
        self.assertIn('순위 구간', SOURCE)
        self.assertNotIn('\ufffd', SOURCE)
        self.assertNotIn('__UNIVERSE__', SOURCE)

    def test_ticker_text_is_bold_pure_black(self):
        self.assertIn('color tickerInk = #000000', SOURCE)
        self.assertIn('text_formatting=bold ? text.format_bold : text.format_none', SOURCE)
        self.assertIn('textcolor=tickerInk, size=size.small, tooltip=f_tip(i), text_formatting=text.format_bold)', SOURCE)
        palette = re.findall(r'#[0-9A-Fa-f]{6}', re.search(r'palette = array.from\(([^)]*)\)', SOURCE).group(1))
        self.assertEqual(len(palette), 40)

        def linear(value):
            s = value / 255
            return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

        for colour in palette:
            r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
            luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
            # WCAG contrast of pure black text on the slot colour.
            self.assertGreaterEqual((luminance + 0.05) / 0.05, 4.5, colour)
    def test_title_row_counts_use_host_wording(self):
        self.assertIn('"호스트 상회 " + str.tostring(beat) + "/" + str.tostring(peers)', SOURCE)
        self.assertIn('" · 최근 호스트 상회 " + str.tostring(recentBeat) + "/" + str.tostring(recentPeers)', SOURCE)
        self.assertIn('"상회 " + str.tostring(beat) + "/" + str.tostring(peers) + (bars ? "  " + f_bar(beat, peers) : "")', SOURCE)
        self.assertIn('"최근 " + str.tostring(recentBeat) + "/" + str.tostring(recentPeers) + (bars ? "  " + f_bar(recentBeat, recentPeers) : "")', SOURCE)
        self.assertNotIn('"강함', SOURCE)
        self.assertIn('str.format_time(anchorRead, "HH:mm", "Asia/Seoul") + " 이후"', SOURCE)
        self.assertIn('string recentLabel = "최근 "', SOURCE)
        self.assertIn('sinceLabel + " %"', SOURCE)
        self.assertIn('recentLabel + " %"', SOURCE)

    def test_merged_cells_are_built_once_and_never_cleared(self):
        build = SOURCE[SOURCE.index('if barstate.isfirst and showBoard'):SOURCE.index('if barstate.islast and showBoard')]
        self.assertIn('board.merge_cells(0, 0, cols - 1, 0)', build)
        self.assertIn('board.merge_cells(0, 1, 1, 1)', build)
        self.assertIn('board.merge_cells(countA, 1, countB - 1, 1)', build)
        self.assertIn('board.merge_cells(countB, 1, cols - 1, 1)', build)
        self.assertEqual(SOURCE.count('merge_cells('), 4)
        self.assertNotIn('board.clear(', SOURCE)
        update = SOURCE[SOURCE.index('if barstate.islast and showBoard'):]
        # Rows 0 and 1 hold the merged cells; the update only uses setters there.
        self.assertNotRegex(update, r'(f_cell|board\.cell)\([^,]+, [01],')
        for setter in ('cell_set_text(countA, 1', 'cell_set_text(countB, 1', 'cell_set_tooltip(0, 1'):
            self.assertIn(setter, update)

    def test_board_design(self):
        # Swatch column in the slot colour, light bold ticker, monospace heat-mapped numbers, header band, centred text.
        self.assertIn('f_cell(c, r, "", fg, ok ? palette.get(i) : color.new(fg, 80), tip)', SOURCE)
        self.assertIn('f_cell(c + 1, r, tick, ok ? fg : muted, bg, tip, true)', SOURCE)
        self.assertIn('f_heat(rel, heatRel) : bg, tip, false, true)', SOURCE)
        self.assertIn('f_heat(recent, heatRecent) : bg, tip, false, true)', SOURCE)
        self.assertIn('text_font_family=mono ? font.family_monospace : font.family_default', SOURCE)
        self.assertIn('text_halign=text.align_center', SOURCE)
        self.assertIn('color headBg = f_mix(chart.bg_color, fg, 0.12, 8)', SOURCE)
        self.assertIn('f_cell(c + 1, 2, "코인", fg, headBg', SOURCE)
        self.assertIn('str.repeat("█", fill) + str.repeat("░", 10 - fill)', SOURCE)
        self.assertIn('2 * k > m ? good : 2 * k < m ? bad : fg', SOURCE)
        self.assertIn('float groupPct = widthPct / 4', SOURCE)

    def test_bar_and_mood_examples(self):
        bar = lambda k, m: round(10 * k / m) if m else 0
        self.assertEqual(bar(27, 40), 7)
        self.assertEqual(bar(2, 8), 2)
        self.assertEqual(bar(0, 0), 0)
        mood = lambda k, m: 'good' if 2 * k > m else 'bad' if 2 * k < m else 'fg'
        self.assertEqual([mood(27, 40), mood(2, 8), mood(11, 22)], ['good', 'bad', 'fg'])

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
        row, line = 1.65, 0.1
        for limit in range(6, 21):
            previous_end = 3.0
            before_rows = before_lines = 0
            for group_index, count in enumerate(counts):
                groups = math.ceil(count / limit)
                rows = math.ceil(count / groups)
                start = 3 + before_rows * row + before_lines * line
                self.assertAlmostEqual(start - previous_end, 0 if group_index == 0 else row)
                for k in range(count):
                    c = (k // rows) * 4
                    r = 3 + k % rows
                    self.assertLess(c + 3, 4 * groups)
                    self.assertLess(r, rows + 3)
                # Counts split at a group boundary and never overlap the two-column title cell.
                count_b = 3 if groups == 1 else 4 * math.ceil(groups / 2)
                self.assertGreater(count_b, 2)
                self.assertLess(count_b, 4 * groups)
                h = 2 + rows
                previous_end = start + h * row + h * line
                before_rows += h + 1
                before_lines += h
        # Every group is a quarter of the width, swatch included.
        width, swatch = 46, 0.4
        group = swatch + (width / 4 - swatch) * (36 + 28 + 28) / 92
        self.assertAlmostEqual(group, width / 4)
        heights = [2 + math.ceil(n / math.ceil(n / 12)) for n in counts]
        total_rows = sum(heights) + len(counts) - 1
        self.assertEqual(total_rows, 51)
        self.assertEqual(sum(heights), 48)
        self.assertAlmostEqual(3 + total_rows * row + sum(heights) * line, 91.95)

if __name__ == '__main__':
    unittest.main(verbosity=2)
