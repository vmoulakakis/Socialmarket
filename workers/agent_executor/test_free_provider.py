import os
import unittest
from unittest.mock import patch
import run


class FreeExecutorProviderTests(unittest.TestCase):
    def test_missing_provider_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(run.verified_free_provider())

    def test_groq_needs_explicit_free_plan_confirmation(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake"}, clear=True):
            self.assertIsNone(run.verified_free_provider())
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake", "GROQ_FREE_TIER_CONFIRMED": "true"}, clear=True):
            cfg = run.verified_free_provider()
            self.assertEqual(cfg["name"], "groq")
            self.assertEqual(cfg["model"], "openai/gpt-oss-20b")

    def test_openrouter_cannot_be_overridden_to_paid_model(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake", "GITHUB_MODELS_MODEL": "paid/test"}, clear=True):
            cfg = run.verified_free_provider()
            self.assertEqual(cfg["model"], "openrouter/free")
            self.assertTrue(cfg["url"].startswith("https://openrouter.ai/"))


if __name__ == "__main__":
    unittest.main()
