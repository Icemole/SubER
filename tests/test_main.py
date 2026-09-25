import unittest
import tempfile
import subprocess
import json

from typing import List
from contextlib import ExitStack

from suber.__main__ import check_metrics, _concatenate_into_single_segment
from suber.data_types import Word, Segment


class MainFunctionTests(unittest.TestCase):

    def _run_main(self, hypothesis_files_contents: List[str], reference_files_contents: List[str],
                 metrics: str = "SubER WER CER BLEU TER chrF TER-br WER-seg BLEU-seg AS-BLEU t-BLEU"):
        """
        Creates temporary hypothesis and reference files, runs the SubER tool and returns the metric scores.
        """

        with ExitStack() as stack:
            def write_files(files_contents):
                files = [stack.enter_context(tempfile.NamedTemporaryFile(mode="w", suffix=".srt"))
                         for _ in files_contents]

                for i, file_content in enumerate(files_contents):
                    files[i].write(file_content)
                    files[i].flush()

                file_names = " ".join(file.name for file in files)
                return file_names

            hypothesis_file_names = write_files(hypothesis_files_contents)
            reference_file_names = write_files(reference_files_contents)

            # Check all metrics, including hyp-to-ref-alignment.
            completed_process = subprocess.run(
                f"python3 -m suber "
                f"--hypothesis {hypothesis_file_names} --reference {reference_file_names} "
                f"--metrics {metrics}".split(),
                check=True, stdout=subprocess.PIPE)

            metric_scores = json.loads(completed_process.stdout.decode("utf-8"))

        return metric_scores

    def test_main_function(self):
        file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame.

            2
            00:00:01,000 --> 00:00:02,000
            This is another frame
            having two lines."""

        metric_scores = self._run_main(
            hypothesis_files_contents=[file_content], reference_files_contents=[file_content])

        # Just check that it runs through.
        self.assertTrue(metric_scores)

    def test_multiple_files(self):
        """
        We support multiple input files, see 'suber.concat_input_files'.
        """
        hypothesis_file1_content = """
            1
            00:00:00,000 --> 00:00:00,800
            This is a first frame."""

        hypothesis_file2_content = """
            2
            00:00:00,400 --> 00:00:01,200
            This is another frame which should have two lines."""

        reference_file1_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame."""

        reference_file2_content = """
            2
            00:00:00,000 --> 00:00:01,000
            This is another frame
            having two lines."""

        metric_scores_split_files = self._run_main(
            hypothesis_files_contents=[hypothesis_file1_content, hypothesis_file2_content],
            reference_files_contents=[reference_file1_content, reference_file2_content])

        # Note: also concatenated in time, second subtitle is shifted by duration of first.
        concatenated_hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:00,800
            This is a first frame.

            2
            00:00:01,400 --> 00:00:02,200
            This is another frame which should have two lines."""

        concatenated_reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame.

            2
            00:00:01,000 --> 00:00:02,000
            This is another frame
            having two lines."""

        metric_scores_concatenated_files = self._run_main(
            hypothesis_files_contents=[concatenated_hypothesis_file_content],
            reference_files_contents=[concatenated_reference_file_content])

        # We expect manual concatenation and giving multiple files to be equivalent.
        self.assertEqual(metric_scores_split_files, metric_scores_concatenated_files)

    def test_ffwer_allows_mismatched_segment_count(self):
        reference_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple first frame.

            2
            00:00:01,000 --> 00:00:02,000
            This is another frame
            having two lines."""

        # Same words as the reference, but split into three subtitle boxes instead of two.
        hypothesis_file_content = """
            1
            00:00:00,000 --> 00:00:01,000
            This is a simple

            2
            00:00:01,000 --> 00:00:01,500
            first frame.

            3
            00:00:01,500 --> 00:00:02,000
            This is another frame
            having two lines."""

        # Plain WER assumes a matching number of segments in hypothesis and reference, so it must fail outright.
        with self.assertRaises(subprocess.CalledProcessError):
            self._run_main(
                hypothesis_files_contents=[hypothesis_file_content],
                reference_files_contents=[reference_file_content],
                metrics="WER")

        # FFWER concatenates everything into a single segment first, so a differing number of segments doesn't
        # matter; since the concatenated text is identical, the score should be a perfect 0.
        metric_scores = self._run_main(
            hypothesis_files_contents=[hypothesis_file_content],
            reference_files_contents=[reference_file_content],
            metrics="FFWER")

        self.assertAlmostEqual(metric_scores["FFWER"], 0.0)


class ConcatenateIntoSingleSegmentTests(unittest.TestCase):

    def test_concatenates_words_in_order(self):
        segments = [
            Segment(word_list=[Word(string="a"), Word(string="b")]),
            Segment(word_list=[Word(string="c")]),
            Segment(word_list=[]),
        ]

        result = _concatenate_into_single_segment(segments)

        self.assertEqual(len(result), 1)
        self.assertEqual([word.string for word in result[0].word_list], ["a", "b", "c"])

    def test_empty_input(self):
        result = _concatenate_into_single_segment([])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].word_list, [])


class CheckMetricsTests(unittest.TestCase):

    def test_ffwer_allowed(self):
        check_metrics(["FFWER"])  # must not raise

    def test_ffwer_cased_and_seg_variants_not_supported(self):
        # Deliberately not implemented: FFWER only exists as its plain, uncased, non-segmentation-aware form.
        with self.assertRaises(ValueError):
            check_metrics(["FFWER-cased"])
        with self.assertRaises(ValueError):
            check_metrics(["FFWER-seg"])


if __name__ == '__main__':
    unittest.main()
