#
#    Metrix++, Copyright 2009-2013, Metrix++ Project
#    Link: http://metrixplusplus.sourceforge.net
#    
#    This file is a part of Metrix++ Tool.
#    
#    Metrix++ is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#    
#    Metrix++ is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with Metrix++.  If not, see <http://www.gnu.org/licenses/>.
#


import unittest

import tests.common

class TestBasic(tests.common.TestCase):

    def test_workflow(self):
        
        # first collection
        runner = tests.common.ToolRunner('collect',
                                         ['--std.code.complexity.on',
                                          '--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         save_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('export',
                                         ['--general.log-level=INFO'],
                                         check_stderr=[(0, -1)])
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0'],
                                         check_stderr=[(0, -1)],
                                         exit_code=4)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('info',
                                         ['--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         exit_code=0)
        self.assertExec(runner.run())

        # second collection
        runner = tests.common.ToolRunner('collect',
                                         ['--std.code.complexity.on',
                                          '--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         prefix='second',
                                         cwd="sources_changed",
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('export',
                                         ['--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         prefix='second',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('export',
                                         ['--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         prefix='second_per_file',
                                         dirs_list=['./simple.cpp'],
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0'],
                                         check_stderr=[(0, -1)],
                                         exit_code=6,
                                         prefix='second',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0',
                                          '--general.warn=all'],
                                         check_stderr=[(0, -1)],
                                         exit_code=6,
                                         prefix='second_warn_all',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0',
                                          '--general.warn=touched'],
                                         check_stderr=[(0, -1)],
                                         exit_code=4,
                                         prefix='second_warn_touched',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0',
                                          '--general.warn=trend'],
                                         check_stderr=[(0, -1)],
                                         exit_code=3,
                                         prefix='second_warn_trend',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit',
                                         ['--general.log-level=INFO',
                                          '--general.max-limit=std.code.complexity:cyclomatic:0',
                                          '--general.warn=new'],
                                         check_stderr=[(0, -1)],
                                         exit_code=2,
                                         prefix='second_warn_new',
                                         use_prev=True)
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('info',
                                         ['--general.log-level=INFO'],
                                         check_stderr=[(0, -1)],
                                         prefix='second',
                                         use_prev=True)
        self.assertExec(runner.run())

    def test_help(self):
        
        runner = tests.common.ToolRunner('collect', ['--help'])
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('export', ['--help'])
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('limit', ['--help'])
        self.assertExec(runner.run())

        runner = tests.common.ToolRunner('info', ['--help'])
        self.assertExec(runner.run())
		

if __name__ == '__main__':
    unittest.main()