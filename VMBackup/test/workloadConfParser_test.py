import unittest
from mock import patch, MagicMock
import sys
import os
sys.path.insert(1, os.path.join(os.path.dirname(os.getcwd()),'main'))
sys.path.insert(1, os.path.join(os.path.dirname(os.getcwd()),'main/workloadPatch'))

from backuplogger import Backuplogger
from workloadPatch import WorkloadPatch

class SimpleTest(unittest.TestCase):

    def setUp(self):
        with patch.object(Backuplogger, 'log', return_value=1):
            mock_log = Backuplogger('asd')
            self.workload_patch= WorkloadPatch.WorkloadPatch(mock_log)
            
    def testWorkloadName(self):
        workloadList = self.workload_patch.supported_workload
        workloadName = self.workload_patch.name
        if (workloadName != None):
            self.assertIn(workloadName, workloadList, "workload found in conf but not contained in supported list")
        self.assertTrue(True)

    def testMySQLIPC(self):
        workloadName = self.workload_patch.name
        ipcFolder = self.workload_patch.ipc_folder
        if (workloadName.upper() == "mysql".upper()):
            self.assertIsNotNone(ipcFolder, "MySQL database provided but no ipc folder directory provided")
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()