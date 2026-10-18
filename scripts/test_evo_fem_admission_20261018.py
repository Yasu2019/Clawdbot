import unittest
from evo_fem_admission_20261018 import decide
class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.policy={'solver_thread_cap':28,'guest_configured_gib':48,'guest_reserve_gib':4,'windows_reserve_gib':6}
        self.jobs=[{'pid':1,'threads':12,'reserved_peak_gib':8,'rss_gib':5.5,'budget_identified':True},
                   {'pid':2,'threads':6,'reserved_peak_gib':8,'rss_gib':5.2,'budget_identified':True}]
    def test_additional_cpu_and_memory_budget(self):
        r=decide(self.policy,self.jobs,35,30,10,20)
        self.assertTrue(r['resource_budget_fits']);self.assertEqual(r['remaining_solver_threads'],10)
    def test_cpu_oversubscription_rejected(self):
        self.assertFalse(decide(self.policy,self.jobs,35,30,11,1)['resource_budget_fits'])
    def test_unknown_host_is_not_zero_or_eligible(self):
        self.assertFalse(decide(self.policy,self.jobs,35,None,2,1)['resource_budget_fits'])
    def test_host_and_guest_available_are_not_added(self):
        self.assertFalse(decide(self.policy,self.jobs,35,10,2,8)['resource_budget_fits'])
    def test_unknown_older_work_is_preserved_and_blocks_new_admission(self):
        self.jobs[0]['budget_identified']=False
        self.assertFalse(decide(self.policy,self.jobs,35,30,2,1)['resource_budget_fits'])
    def test_large_rss_is_not_a_global_nine_gib_kill_threshold(self):
        self.jobs[0].update(rss_gib=14,reserved_peak_gib=18)
        self.assertTrue(decide(self.policy,self.jobs,25,30,2,4)['resource_budget_fits'])
if __name__=='__main__':unittest.main()
