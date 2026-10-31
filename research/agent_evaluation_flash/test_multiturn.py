import unittest
from prepare_cases import cases,DOMAINS
from run_multiturn_v2 import score,prompts,DOMAIN_ALIASES


class ControlledEvaluationTests(unittest.TestCase):
    def test_split_and_ids(self):
        records=cases()
        self.assertEqual(sum(c['split']=='dev' for c in records),10)
        self.assertEqual(sum(c['split']=='test' for c in records),30)
        self.assertEqual(len({c['case_id'] for c in records}),40)

    def test_reference_factors_have_domain(self):
        self.assertTrue(all(set(c['author_reference_factors_by_domain'])<=set(DOMAINS) for c in cases()))

    def test_alias_only_routes_not_scores(self):
        self.assertEqual(DOMAIN_ALIASES['support_timing'],'support')
        self.assertEqual(DOMAIN_ALIASES['q3'],'context')
        self.assertNotIn('new_psychological_disorder',DOMAIN_ALIASES)

    def test_perfect_and_false_positive(self):
        case=cases()[0]
        row={'assessment':{'factors':[{'id':'confidence','domain':'confidence','case_quote':case['facts']['confidence']}]},
             'revealed_domains':['confidence','context'],'turns':[],'case_id':'D01','family':'confidence','system':'test','repeat':1}
        metrics=score(row,case)
        self.assertEqual(metrics['f1'],1)
        self.assertEqual(metrics['exact_case_quote_rate'],1)
        row['assessment']['factors'].append({'id':'anxiety'})
        self.assertEqual(score(row,case)['fp'],1)

    def test_unknown_reference_not_full_marks(self):
        case=cases()[9]
        row={'assessment':{'decision':'insufficient_information','factors':[]},'revealed_domains':[],
             'turns':[],'case_id':'D10','family':'insufficient','system':'test','repeat':1}
        metric=score(row,case)
        self.assertIsNone(metric['f1'])
        self.assertTrue(metric['reference_empty_correct_abstention'])

    def test_no_reference_labels_in_prompts(self):
        for text in prompts().values():
            self.assertNotIn('author_reference_factors',text)
            self.assertNotIn('required_inquiry_domains',text)
            self.assertNotIn('T01',text)


if __name__=='__main__': unittest.main()
