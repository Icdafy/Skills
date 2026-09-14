"""Attachment rules are checked before DOCX generation preserves the final text."""
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from quality_check import validate


class AttachmentFormatTests(unittest.TestCase):
    def problems(self, attachments):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'minutes.txt'
            path.write_text('专题会议纪要\n　　会议听取项目进展情况。\n' +
                            '\n'.join('　　' + line for line in attachments), encoding='utf-8')
            return [error for error in validate(path, 'minutes') if '附件' in error]

    def test_single_has_no_number(self):
        self.assertEqual(self.problems(['附件：工作方案（试行）']), [])
        self.assertTrue(self.problems(['附件1.工作方案（试行）']))

    def test_multiple_arabic_numbers_and_clean_names(self):
        self.assertEqual(self.problems(['附件1.工作方案', '附件2.测算表']), [])
        self.assertTrue(self.problems(['附件一：《工作方案》；', '附件二：测算表。']))


if __name__ == '__main__':
    unittest.main()
