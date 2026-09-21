"""The supported editing CLI stays usable without a native editor backend."""
from contextlib import redirect_stderr
import io
import unittest
from digital_human.cli import parser


class DirectEditCommands(unittest.TestCase):
    def test_direct_commands_remain_and_retired_commands_are_rejected(self):
        for name in ['edit-compose', 'edit-render', 'edit-verify', 'edit-seal']:
            args = parser().parse_args([name, 'fixture-job', 'revision'])
            self.assertEqual(args.job, 'fixture-job')
            self.assertEqual(args.revision, 'revision')
        for args in [['edit-export', 'fixture-job', 'revision'],
                     ['relink-draft', '--source', 'old', '--out', 'new']]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                parser().parse_args(args)
            self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
