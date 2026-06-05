from __future__ import annotations

import unittest

from tools.release_e2e_check import APP_FAIL, OS_POLICY_BLOCK, PASS, classify_release_result


class ReleaseE2EClassificationTest(unittest.TestCase):
    def test_classifies_application_control_block(self) -> None:
        output = "Application Control policy has blocked this file"

        self.assertEqual(classify_release_result(output, 1), OS_POLICY_BLOCK)

    def test_classifies_code_integrity_signing_block(self) -> None:
        output = "Code Integrity determined that a file did not meet the Enterprise signing level requirements."

        self.assertEqual(classify_release_result(output, 1), OS_POLICY_BLOCK)

    def test_classifies_embedded_python_startup_failure(self) -> None:
        output = "Failed to start embedded python interpreter: Failed to import encodings module"

        self.assertEqual(classify_release_result(output, 1), APP_FAIL)

    def test_classifies_successful_smoke_output(self) -> None:
        self.assertEqual(classify_release_result("EXE_SMOKE_OK", 0), PASS)
        self.assertEqual(classify_release_result("E2E_OK", 0), PASS)

    def test_classifies_generic_nonzero_failure_as_app_fail(self) -> None:
        self.assertEqual(classify_release_result("process exited too early: exit_code=1", 1), APP_FAIL)


if __name__ == "__main__":
    unittest.main()
