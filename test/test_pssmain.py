#-------------------------------------------------------------------------------
# pss: test/test_pssmain.py
#
# Test the main() function of pss
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import unittest

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from psslib.pss import main
from test.utils import (
        path_to_testdir, MockOutputFormatter, filter_out_path)


class TestPssMain(unittest.TestCase):
    testdir1 = path_to_testdir('testdir1')
    testdir2 = path_to_testdir('testdir2')
    of = None

    def setUp(self):
        self.of = MockOutputFormatter('testdir1')

    def test_basic(self):
        self._run_main(['abc', '--cc'])
        self.assertEqual(sorted(self.of.output),
                sorted(self._gen_outputs_in_file(
                    'testdir1/filea.c', [('MATCH', (2, [(4, 7)]))]) +
                self._gen_outputs_in_file(
                    'testdir1/filea.h', [('MATCH', (1, [(8, 11)]))])))

    def test_two_matches(self):
        self._run_main(['abc', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('MATCH', (4, [(18, 21)])),
                        ('MATCH', (14, [(15, 18)]))]))

    def test_whole_words(self):
        # without whole word matching
        of = MockOutputFormatter('testdir1')
        self._run_main(['xaxo', '--ada'], output_formatter=of)
        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/wholewords.adb',
                    [   ('MATCH', (1, [(5, 9)])),
                        ('MATCH', (2, [(4, 8)]))]))

        # now with whole word matching
        of = MockOutputFormatter('testdir1')
        self._run_main(['xaxo', '--ada', '-w'], output_formatter=of)
        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/wholewords.adb',
                    [('MATCH', (1, [(5, 9)]))]))

    def test_no_break(self):
        # same test as above but with --nobreak
        self._run_main(['abc', '--ada', '--nobreak'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('MATCH', (4, [(18, 21)])),
                        ('MATCH', (14, [(15, 18)]))],
                    add_end=False))

    def test_context_separate(self):
        # context set to +/-3, so it's not "merged" between the two matches
        # and stays separate, with a context separator
        self._run_main(['abc', '-C', '3', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('CONTEXT', 1), ('CONTEXT', 2), ('CONTEXT', 3),
                        ('MATCH', (4, [(18, 21)])),
                        ('CONTEXT', 5), ('CONTEXT', 6), ('CONTEXT', 7),
                        ('CONTEXT_SEP', None),
                        ('CONTEXT', 11), ('CONTEXT', 12), ('CONTEXT', 13),
                        ('MATCH', (14, [(15, 18)])),
                        ('CONTEXT', 15), ('CONTEXT', 16), ('CONTEXT', 17),
                        ]))

    def test_context_merged(self):
        # context set to +/-6, so it's merged between matches
        self._run_main(['abc', '-C', '6', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('CONTEXT', 1), ('CONTEXT', 2), ('CONTEXT', 3),
                        ('MATCH', (4, [(18, 21)])),
                        ('CONTEXT', 5), ('CONTEXT', 6), ('CONTEXT', 7),
                        ('CONTEXT', 8), ('CONTEXT', 9), ('CONTEXT', 10),
                        ('CONTEXT', 11), ('CONTEXT', 12), ('CONTEXT', 13),
                        ('MATCH', (14, [(15, 18)])),
                        ('CONTEXT', 15), ('CONTEXT', 16), ('CONTEXT', 17),
                        ('CONTEXT', 18), ('CONTEXT', 19), ('CONTEXT', 20),
                        ]))

    def test_ignored_dirs(self):
        rootdir = path_to_testdir('ignored_dirs')

        # no dirs ignored
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(['def', '--xml'], dir=rootdir, output_formatter=of)

        # Comparing as sorted because on different systems the files
        # returned in a different order
        #
        self.assertEqual(sorted(of.output),
                sorted(self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir1/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir2/file.xml', [('MATCH', (1, [(3, 6)]))])))

        # both dir1 and dir2 ignored
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(
            ['def', '--xml', '--ignore-dir=dir1', '--ignore-dir=dir2'],
            dir=rootdir,
            output_formatter=of)

        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]))

        # dir1 ignored (dir2 also appears in remove_ignored_dirs)
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(
            ['def', '--xml', '--ignore-dir=dir1', '--ignore-dir=dir2',
                '--noignore-dir=dir2'],
            dir=rootdir,
            output_formatter=of)

        self.assertEqual(sorted(of.output),
                sorted(self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir2/file.xml', [('MATCH', (1, [(3, 6)]))])))

    def test_only_find_files_f(self):
        self._run_main(['--cc', '-f'])
        self.assertFoundFiles(self.of,
                ['testdir1/filea.c', 'testdir1/filea.h',
                'testdir1/subdir1/filey.c', 'testdir1/subdir1/filez.c'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['--make', '-f'])
        self.assertFoundFiles(self.of,
                ['testdir1/Makefile', 'testdir1/subdir1/Makefile', 'testdir1/zappos.mk'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['--cmake', '-f'])
        self.assertFoundFiles(self.of,
                [   'testdir1/CMakeLists.txt',
                    'testdir1/subdir1/CMakeFuncs.txt',
                    'testdir1/subdir1/joe.cmake',
                    'testdir1/subdir1/joe2.cmake'])

        self.of = MockOutputFormatter('testdir2')
        self._run_main(['--txt', '-f'], dir=self.testdir2)
        self.assertFoundFiles(self.of,
                ['testdir2/sometext.txt', 'testdir2/othertext.txt'])

        self.of = MockOutputFormatter('testdir2')
        self._run_main(['--withoutext', '-f'], dir=self.testdir2)
        self.assertFoundFiles(self.of,
                ['testdir2/somescript'])

    def test_only_find_files_g(self):
        self._run_main(['--cc', '-g', r'.*y\.'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/filey.c'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['-g', r'\.qqq'])
        self.assertFoundFiles(self.of, [])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['-a', '-g', r'\.qqq'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/ppp.qqq'])

    def test_only_find_files_l(self):
        self._run_main(['--cc', 'abc', '-l'])
        self.assertFoundFiles(self.of,
                ['testdir1/filea.c', 'testdir1/filea.h'])

    def test_only_find_files_L(self):
        self._run_main(['--cc', 'abc', '-L'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/filey.c', 'testdir1/subdir1/filez.c'])

    def test_binary_matches(self):
        self._run_main(['-G', 'zb', 'cde'])

        binary_match = self.of.output[-1]
        self.assertEqual(binary_match[0], 'BINARY_MATCH')
        self.assertTrue(binary_match[1].find('zb.erl') > 0)

    def test_weird_chars(self):
        # .rb files have some weird characters in them - this is a sanity
        # test that shows that pss won't crash while decoding these files
        #
        self._run_main(['ttt', '--ruby'])

    def test_include_types(self):
        rootdir = path_to_testdir('test_types')
        def outputs(filename):
            return self._gen_outputs_in_file(
                        filename,
                        [('MATCH', (1, [(0, 3)]))])

        # include only js and java
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc', '--js', '--java'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.java') +
                outputs('test_types/a.js')))

        # empty include_types - so include all known types
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.java') +
                outputs('test_types/a.js') +
                outputs('test_types/a.lua') +
                outputs('test_types/a.cmd') +
                outputs('test_types/a.bat')))

        # empty include_types, but some are excluded
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc', '--nojs', '--nojava', '--nobatch'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.lua')))

    def _run_main(self, args, dir=None, output_formatter=None):
        main(
            argv=[''] + args + [dir or self.testdir1],
            output_formatter=output_formatter or self.of)

    def _gen_outputs_in_file(self, filename, outputs, add_end=True):
        """ Helper method for constructing a list of output pairs in the format
            of MockOutputFormatter, delimited from both ends with START_MATCHES
            and END_MATCHES for the given filename.
        """
        seq = []
        seq.append(('START_MATCHES', os.path.normpath(filename)))
        seq.extend(outputs)
        if add_end:
            seq.append(('END_MATCHES', os.path.normpath(filename)))
        return seq

    def _build_found_list(self, filenames):
        """ Helper for only_find_files methods
        """
        return sorted(
            ('FOUND_FILENAME', os.path.normpath(f)) for f in filenames)

    def assertFoundFiles(self, output_formatter, expected_list):
        self.assertEqual(sorted(e for e in output_formatter.output
                                  if not filter_out_path(e[1])),
            self._build_found_list(expected_list))


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

