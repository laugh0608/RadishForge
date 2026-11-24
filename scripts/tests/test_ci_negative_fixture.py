import unittest


class CandidateQualityNegativeFixture(unittest.TestCase):
    def test_intentional_failure(self):
        self.fail("Intentional Candidate Quality acceptance fixture")
