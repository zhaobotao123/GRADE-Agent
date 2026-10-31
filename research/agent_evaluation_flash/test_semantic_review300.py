import unittest
from semantic_review300 import validate,quote_span,make_payload,METRICS

class SemanticValidationTests(unittest.TestCase):
    def setUp(self):
        self.item={'item_id':'R0001','system':'SHOULD_NOT_BE_SENT','caseId':'H02_standardized_case','repeat':1,
            'case_record':{'records':'Accounts conflict.'},'reference_constraints':{'prioritize':['reconcile sources']},
            'report':'Accounts conflict.\nCollect dated records before drawing conclusions.'}
    def result(self):return {'item_id':'R0001','ratings':{m:{'applicable':True,'score':2,'reason':'Case-specific reasoning.',
        'report_evidence':['Accounts conflict.'],'case_evidence_keys':['records']} for m in METRICS},
        'primary_signal_set':['conflicting_sources'],'primary_signal_reason':'Main issue.',
        'needs_human_review':False,'human_review_reason':''}
    def test_exact_quote_offsets(self):
        x=quote_span(self.item['report'],'Accounts conflict.');self.assertEqual(self.item['report'][x['start']:x['end']],x['quote'])
    def test_whitespace_only_quote_canonicalization(self):
        x=quote_span('Hello\nworld.','Hello world.');self.assertEqual(x['quote'],'Hello\nworld.')
    def test_paraphrased_evidence_rejected(self):
        with self.assertRaises(ValueError):quote_span(self.item['report'],'Sources disagree.')
    def test_valid_schema(self):self.assertFalse(validate(self.result(),self.item)['needs_human_review'])
    def test_wrong_case_applicability_rejected(self):
        item={**self.item,'caseId':'H04_standardized_case'}
        with self.assertRaises(AssertionError):validate(self.result(),item)
    def test_other_category_requires_review(self):
        r=self.result();r['primary_signal_set']=['other'];self.assertTrue(validate(r,self.item)['needs_human_review'])
    def test_noninteger_score_rejected(self):
        r=self.result();r['ratings']['priority_alignment']['score']=1.5
        with self.assertRaises(AssertionError):validate(r,self.item)
    def test_no_configuration_or_old_score_in_payload(self):
        payload=make_payload(self.item);self.assertNotIn('system',payload);self.assertNotIn('SHOULD_NOT_BE_SENT',str(payload));self.assertNotIn('old_score',payload)

if __name__=='__main__':unittest.main()
