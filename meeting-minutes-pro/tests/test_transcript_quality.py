"""Synthetic repetitions only; no private transcript or real-audio score."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from transcript_quality import repetition_flags


class RepetitionTests(unittest.TestCase):
    def test_empty_and_nonrepeated_text_are_unflagged(self):
        for text in ('', '，。\n', '项目正在检查设备连接情况，随后安排新的实验。'):
            self.assertEqual(repetition_flags(text), [])

    def test_two_or_three_repetitions_remain_unflagged(self):
        for count in (2, 3):
            self.assertEqual(repetition_flags('状态切换，' * count), [])

    def test_consecutive_phrase_loop_is_a_review_cue(self):
        flags = repetition_flags('先说明流程。' + '状态切换，' * 5 + '然后继续。')
        self.assertTrue(flags)
        self.assertEqual(flags[0]['code'], 'suspected_repetition')
        self.assertEqual(flags[0]['severity'], 'warning')
        self.assertGreaterEqual(flags[0]['occurrences'], 4)
        self.assertIn('可能是真实重复', flags[0]['message'])

    def test_interspersed_short_word_loop_is_flagged(self):
        text = ('模块甲、模块乙、模块甲、模块乙、入口、出口、'
                '写入、写入、继续写入、写入、继续写入、写入')
        flags = repetition_flags(text)
        self.assertTrue(any(flag['repeated_text'] == '写入' and flag['occurrences'] >= 6
                            for flag in flags))

    def test_dispersed_technical_name_is_not_a_local_loop(self):
        paragraph = ('星际控制器支持自动校准并将采样数据发送至地面终端，'
                     '工作人员逐项检查电源线路和通信连接，完成确认后进入后续试验阶段。')
        self.assertEqual(repetition_flags(paragraph * 8), [])

    def test_offsets_locate_evidence_in_original_text(self):
        text = '开始：\n  ' + '状态切换，\n' * 5 + '结束。'
        flags = repetition_flags(text)
        self.assertTrue(flags)
        for flag in flags:
            window = flag['window']
            self.assertGreaterEqual(window['start_character'], 0)
            self.assertLessEqual(window['end_character'], len(text))
            evidence = text[window['start_character']:window['end_character']]
            normalized = ''.join(char for char in evidence if char.isalnum())
            self.assertGreaterEqual(normalized.count(flag['repeated_text']), flag['occurrences'])
            self.assertNotIn('replacement', flag)


if __name__ == '__main__':
    unittest.main()
