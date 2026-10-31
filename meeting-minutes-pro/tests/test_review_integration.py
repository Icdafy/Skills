"""Cross-stage review contracts; no actual model inference is claimed."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import refine_transcript as refine


class BoundaryReviewTests(unittest.TestCase):
    def test_agreement_on_a_dense_loop_still_requires_review(self):
        repeated = '继续读取' * 6
        flags = refine.compare_texts(repeated, repeated, [])
        self.assertIn('重复输出待核', [item['category'] for item in flags])

    def window(self, start=8, end=14):
        return {'start': start, 'end': end, 'time_basis': 'processed_audio'}

    def test_boundary_is_reviewed_even_without_primary_words(self):
        clips = refine.add_boundary_reviews([], [self.window()], [], 30)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].reasons, ('chunk_boundary',))
        self.assertEqual(clips[0].funasr_text, '')
        self.assertEqual((clips[0].start, clips[0].end), (8, 14))

    def test_existing_full_coverage_is_not_duplicated(self):
        existing = [refine.Clip(1, 0, 10, ('all',), ''),
                    refine.Clip(2, 10, 30, ('all',), '')]
        self.assertEqual(len(refine.add_boundary_reviews(existing, [self.window()], [], 30)), 2)

    def test_partial_coverage_expands_to_sentence_boundaries(self):
        existing = [refine.Clip(1, 0, 5, ('number',), '3个')]
        stamps = [{'start': 7, 'end': 16, 'text': '这里仍在继续讲话。'}]
        clips = refine.add_boundary_reviews(existing, [self.window()], stamps, 30)
        self.assertEqual((clips[-1].start, clips[-1].end), (7, 16))
        self.assertIn('继续讲话', clips[-1].funasr_text)

    def test_invalid_windows_are_not_silently_accepted(self):
        for bad in [self.window(-1, 3), self.window(2, 40), self.window(float('nan'), 3),
                    {'start': 2, 'end': 4}]:
            with self.assertRaises(ValueError):
                refine.add_boundary_reviews([], [bad], [], 30)

    def test_expansion_includes_new_overlapping_sentence_in_audio_and_text(self):
        stamps = [{'start': 7, 'end': 16, 'text': '甲继续介绍产品。'},
                  {'start': 15, 'end': 20, 'text': '乙补充客户情况。'}]
        clip = refine.add_boundary_reviews([], [self.window()], stamps, 30)[0]
        self.assertEqual((clip.start, clip.end), (7, 20))
        self.assertEqual(clip.funasr_text, '甲继续介绍产品。乙补充客户情况。')
        self.assertEqual(clip.reasons, ('chunk_boundary',))

    def test_overlapping_chain_expands_until_membership_is_stable(self):
        stamps = [{'start': 7, 'end': 16, 'text': '甲介绍。'},
                  {'start': 15, 'end': 20, 'text': '乙补充。'},
                  {'start': 19, 'end': 23, 'text': '丙说明。'},
                  {'start': 23, 'end': 25, 'text': '后续独立句。'}]
        clip = refine.add_boundary_reviews([], [self.window()], stamps, 30)[0]
        self.assertEqual((clip.start, clip.end), (7, 23))
        self.assertEqual(clip.funasr_text, '甲介绍。乙补充。丙说明。')

    def test_overlong_sentence_keeps_bounded_audio_and_explicit_review_cue(self):
        stamps = [{'start': 7, 'end': 16, 'text': '甲介绍。'},
                  {'start': 15, 'end': 150, 'text': '乙的长句不能完整装入片段。'}]
        clip = refine.add_boundary_reviews([], [self.window()], stamps, 180)[0]
        self.assertEqual((clip.start, clip.end), (7, 16))
        self.assertLessEqual(clip.end - clip.start, refine.DEFAULT_MAX_CLIP_SECONDS)
        self.assertIn('partial_sentence_boundary', clip.reasons)
        self.assertIn('乙的长句', clip.funasr_text)


if __name__ == '__main__':
    unittest.main()
