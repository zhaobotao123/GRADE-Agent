import unittest
from evaluator_v2 import evaluate,sections

class EvaluationTests(unittest.TestCase):
    def score(self,text,facts=None,expected=None):return evaluate(text,facts or {},expected or {'isolated_event'})
    def test_never_crosses_priority_section(self):
        r=self.score('PRIORITY SIGNALS\nAcute migraine during a single test.\nBOUNDARY-REVIEW SIGNALS\nNo conflicting sources identified.\nMISSING INFORMATION\nNo safeguarding concern reported.')
        self.assertEqual(r['primary_signal'],'isolated_event');self.assertEqual(r['priority_alignment'],1)
    def test_negation_not_a_priority(self):
        r=self.score('PRIORITY SIGNALS\nNo bullying or conflicting sources were identified.\nLanguage transition barriers.\nMISSING INFORMATION\nFurther information needed.',expected={'language_context'})
        self.assertEqual(r['primary_signal'],'language_context')
    def test_language_synonym(self):
        r=self.score('PRIORITY SIGNALS\nLanguage transition context.\nBOUNDARY-REVIEW SIGNALS\nMathematics self-efficacy needs assessment.',expected={'language_context'})
        self.assertEqual(r['primary_signal'],'language_context')
    def test_confidence_not_read_from_case_summary(self):
        r=self.score('CASE SUMMARY\nStudent has high confidence.\nPRIORITY SIGNALS\nAcute illness interrupted one test.\nMISSING INFORMATION\nUnknown.')
        self.assertEqual(r['primary_signal'],'isolated_event')
    def test_no_heading_does_not_force_zero(self):
        r=self.score('The student has difficulties. We should investigate further.')
        self.assertIsNone(r['primary_signal']);self.assertIsNone(r['priority_alignment']);self.assertTrue(r['manual_review_required'])
    def test_markdown_baseline_supported(self):
        r=self.score('## Likely Factors\n- Language barriers in word problems.\n## Recommendations\nProvide a glossary next week and review outcomes.',expected={'language_context'})
        self.assertEqual(r['primary_signal'],'language_context');self.assertEqual(r['action_structure_completeness'],1)
    def test_multiple_categories_require_review(self):
        r=self.score('PRIORITY SIGNALS\nLow confidence together with classroom disruption.\nMISSING INFORMATION\nUnknown.',expected={'learning_confidence'})
        self.assertIsNone(r['primary_signal']);self.assertIsNone(r['priority_alignment'])
    def test_boundary_heading_alone_does_not_pass(self):
        r=self.score('INTERPRETATION BOUNDARY\nProceed with the plan.')
        self.assertEqual(r['explicit_boundary_statement_present'],0)
    def test_boundary_can_be_written_without_heading(self):
        r=self.score('An association cannot establish an individual cause.')
        self.assertEqual(r['explicit_boundary_statement_present'],1)
    def test_factual_cause_not_automatic_failure(self):
        r=self.score('The migraine caused an early departure from the test.',{'event':'The student left the assessment early because of an acute migraine.'})
        self.assertTrue(r['causal_claim_review_required']);self.assertIsNone(r['overall_boundary_compliance_score'])
        self.assertTrue(r['causal_claim_candidates'][0]['potentially_relevant_case_facts'])
    def test_negated_cause_not_violation(self):
        r=self.score('The report does not establish that tutoring caused low performance.')
        self.assertFalse(r['causal_claim_review_required'])
    def test_hedged_claim_not_automatic_failure(self):
        r=self.score('Tutoring might have caused dependence; this remains uncertain.')
        self.assertFalse(r['causal_claim_review_required'])
    def test_action_terms_outside_action_section_not_counted(self):
        r=self.score('MISSING INFORMATION\nReview records next week.\nCOORDINATED SUPPORT PLAN\nProvide support.')
        self.assertEqual(r['action_structure_completeness'],1/3)
    def test_action_no_heading_left_unscored(self):
        self.assertIsNone(self.score('Provide support next week and monitor outcomes.')['action_structure_completeness'])
    def test_primary_statement_in_plain_text(self):
        r=self.score('The main issue is a language barrier in the new instructional language.',expected={'language_context'})
        self.assertEqual(r['primary_signal'],'language_context')
    def test_test_interruption_not_classroom_disruption(self):
        r=self.score('PRIORITY SIGNALS\nAcute migraine event causing assessment interruption.\nMISSING INFORMATION\nUnknown.')
        self.assertEqual(r['primary_signal'],'isolated_event')
    def test_classroom_interruption_has_relevant_context(self):
        r=self.score('PRIORITY SIGNALS\nFrequent classroom interruptions.\nMISSING INFORMATION\nUnknown.',expected={'classroom_conditions'})
        self.assertEqual(r['primary_signal'],'classroom_conditions')
    def test_no_use_of_expected_label_to_extract(self):
        text='PRIORITY SIGNALS\nBullying and feeling unsafe.\nMISSING INFORMATION\nUnknown.'
        a=self.score(text,expected={'language_context'});b=self.score(text,expected={'safeguarding'})
        self.assertEqual(a['primary_signal'],b['primary_signal']);self.assertEqual(a['priority_alignment'],0);self.assertEqual(b['priority_alignment'],1)

if __name__=='__main__':unittest.main()
