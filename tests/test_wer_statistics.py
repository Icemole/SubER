import unittest

from suber.metrics.jiwer_interface import calculate_word_error_rate
from suber.metrics.wer_statistics import WERStatisticsCollector
from .utilities import create_temporary_file_and_read_it


class WERStatisticsTests(unittest.TestCase):

    def test_wer_statistics(self):
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame."""

        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is simple frame extra."""

        reference_subtitles = create_temporary_file_and_read_it(reference_file_content)
        hypothesis_subtitles = create_temporary_file_and_read_it(hypothesis_file_content)

        statistics_collector = WERStatisticsCollector()

        wer_score = calculate_word_error_rate(
            hypothesis=hypothesis_subtitles, reference=reference_subtitles, metric="WER",
            statistics_collector=statistics_collector)

        # Passing a statistics collector must not change the returned score.
        self.assertAlmostEqual(wer_score, 50.0)

        statistics = statistics_collector.get_statistics()

        # ref (lowercased, no punctuation): this is a   simple first  frame
        # hyp (lowercased, no punctuation): this is *   simple frame extra
        #                                          D            S     S
        # -> 3 hits, 2 substitutions, 1 deletion, 0 insertions, reported as two separate single-word
        # substitutions ("first"->"frame" and "frame"->"extra"), not joined into one multi-word phrase.
        self.assertEqual(statistics["hits"], 3)
        self.assertEqual(statistics["substitutions"], 2)
        self.assertEqual(statistics["deletions"], 1)
        self.assertEqual(statistics["insertions"], 0)

        self.assertEqual(
            statistics["most_common_substitutions"],
            [{"reference": "first", "hypothesis": "frame", "count": 1},
             {"reference": "frame", "hypothesis": "extra", "count": 1}])
        self.assertEqual(statistics["most_common_insertions"], [])
        self.assertEqual(statistics["most_common_deletions"], [{"word": "a", "count": 1}])

        alignment_visualization = statistics_collector.get_alignment_visualization()
        self.assertIn("REF:", alignment_visualization)
        self.assertIn("HYP:", alignment_visualization)

    def test_multi_word_insertion_split_by_word(self):
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a e"""

        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a c d e"""

        reference_subtitles = create_temporary_file_and_read_it(reference_file_content)
        hypothesis_subtitles = create_temporary_file_and_read_it(hypothesis_file_content)

        statistics_collector = WERStatisticsCollector()

        calculate_word_error_rate(
            hypothesis=hypothesis_subtitles, reference=reference_subtitles, metric="WER",
            statistics_collector=statistics_collector)

        statistics = statistics_collector.get_statistics()

        # ref: a * * e
        # hyp: a c d e
        #        I I
        # jiwer's alignment reports this as one 2-word insertion chunk ("c d"); it must be split into two
        # separate single-word entries rather than reported as one "c d" phrase.
        self.assertEqual(
            statistics["most_common_insertions"],
            [{"word": "c", "count": 1}, {"word": "d", "count": 1}])

    def test_multi_word_deletion_split_by_word(self):
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a b c e"""

        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a e"""

        reference_subtitles = create_temporary_file_and_read_it(reference_file_content)
        hypothesis_subtitles = create_temporary_file_and_read_it(hypothesis_file_content)

        statistics_collector = WERStatisticsCollector()

        calculate_word_error_rate(
            hypothesis=hypothesis_subtitles, reference=reference_subtitles, metric="WER",
            statistics_collector=statistics_collector)

        statistics = statistics_collector.get_statistics()

        # ref: a b c e
        # hyp: a * * e
        #        D D
        # jiwer's alignment reports this as one 2-word deletion chunk ("b c"); it must be split into two
        # separate single-word entries rather than reported as one "b c" phrase.
        self.assertEqual(
            statistics["most_common_deletions"],
            [{"word": "b", "count": 1}, {"word": "c", "count": 1}])

    def test_error_grouping_phrase(self):
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame."""

        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is simple frame extra."""

        reference_subtitles = create_temporary_file_and_read_it(reference_file_content)
        hypothesis_subtitles = create_temporary_file_and_read_it(hypothesis_file_content)

        statistics_collector = WERStatisticsCollector(error_grouping="phrase")

        calculate_word_error_rate(
            hypothesis=hypothesis_subtitles, reference=reference_subtitles, metric="WER",
            statistics_collector=statistics_collector)

        statistics = statistics_collector.get_statistics()

        # Same fixture as test_wer_statistics, but with error_grouping="phrase" the two adjacent substituted
        # words are joined into a single "first frame" -> "frame extra" entry, as jiwer.collect_error_counts()
        # does natively.
        self.assertEqual(
            statistics["most_common_substitutions"],
            [{"reference": "first frame", "hypothesis": "frame extra", "count": 1}])

    def test_invalid_error_grouping(self):
        with self.assertRaises(AssertionError):
            WERStatisticsCollector(error_grouping="bogus")

    def test_top_n(self):
        # Substitutions are separated by matching words so jiwer counts them as 4 separate single-word
        # substitutions instead of joining adjacent ones into multi-word phrases.
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a one b two c three d four"""

        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            a six b seven c eight d nine"""

        reference_subtitles = create_temporary_file_and_read_it(reference_file_content)
        hypothesis_subtitles = create_temporary_file_and_read_it(hypothesis_file_content)

        statistics_collector = WERStatisticsCollector(top_n=2)

        calculate_word_error_rate(
            hypothesis=hypothesis_subtitles, reference=reference_subtitles, metric="WER",
            statistics_collector=statistics_collector)

        statistics = statistics_collector.get_statistics()

        # 4 substitutions total (one<->six, two<->seven, three<->eight, four<->nine), only top 2 should be reported.
        self.assertEqual(statistics["substitutions"], 4)
        self.assertEqual(len(statistics["most_common_substitutions"]), 2)


if __name__ == '__main__':
    unittest.main()
