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

        # ref (lowercased, no punctuation): this is a   simple first frame
        # hyp (lowercased, no punctuation): this is *   simple frame  extra
        #                                          D            S     S
        # -> 3 hits, 2 substitutions, 1 deletion, 0 insertions.
        self.assertEqual(statistics["hits"], 3)
        self.assertEqual(statistics["substitutions"], 2)
        self.assertEqual(statistics["deletions"], 1)
        self.assertEqual(statistics["insertions"], 0)


if __name__ == '__main__':
    unittest.main()
