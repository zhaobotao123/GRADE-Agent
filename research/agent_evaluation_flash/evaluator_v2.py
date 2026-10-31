"""Post-hoc measurement audit, not a validated educational-quality instrument.

Group identity and old scores are deliberately absent from evaluate() inputs.
Primary labels use bounded sections and negative assertions are excluded.
Potential causal claims are quoted for review, never treated as proved errors.
"""
import re

VERSION='2.0.0-posthoc-audit'
SIGNALS={
 'safeguarding':r'\bsafeguard\w*|\bbully\w*|\bbullying\b|\bharass\w*|\bpeer ridicule\b|\bunsafe\b|\bmock\w*',
 'conflicting_sources':r'\bconflict\w*|\breconcil\w*|\bdiscrepan\w*|\bcontradict\w*|\baccounts? differ\b|\bmismatch between .{0,40}(?:reports?|accounts?|perception)',
 'insufficient_information':r'\binsufficient (?:information|case evidence)|\bnot enough information|\binformation (?:gap|insufficiency)|\bmissing (?:information|context|case)|\bcannot (?:assess|determine)|\bunexplained decline|\bcollect more (?:information|evidence)',
 'isolated_event':r'\bisolated\b|\bone[- ]time\b|\bsingle low\b|\btemporary (?:event|health|illness|fluctuation)|\btransient\b|\bmigraine\b|\bfire alarm\b|\bacute illness\b',
 'language_context':r'\blanguage[- ]of[- ]instruction\b|\blanguage (?:context|support|transition|barrier|demand|proficiency)|\bacademic[- ]language\b|\binstructional language\b|\bhome language\b',
 'support_timing':r'\bcompensatory\b|\bsupport[- ]timing\b|\b(?:support|tutoring|assistance) .{0,50}(?:after|followed|response to|pre[- ]existing)|\b(?:introduced|increased|intensified) after\b|\breactive support\b|\blow (?:scores?|performance) .{0,30}(?:preceded|before) .{0,30}(?:support|tutoring)',
 'learning_confidence':r'\bself[- ]efficacy\b|\bconfidence\b|\bconfident\b|\bfixed ability\b|\bfixed[- ]mindset\b|\bgiv(?:e|es|ing) up\b|\blow persistence\b|\bstops? after .{0,20}error',
 'classroom_conditions':r'\bdisciplinary climate\b|\bclassroom conditions?\b|\binterruptions?\b|\bdisruption\w*|\boff[- ]task noise\b',
 'health_or_context':r'\bsleep\b|\bhealth\b|\battendance\b|\bcurriculum transition\b|\btimetable changes?\b',
}
SIGNALS={k:re.compile(v,re.I) for k,v in SIGNALS.items()}
HEADINGS={
 'case summary':'summary','priority signals':'priority','priority issues':'priority','primary signals':'priority',
 'primary concerns':'priority','main issue':'priority','main issues':'priority',
 'boundary-review signals':'boundary_review','boundary review signals':'boundary_review',
 'missing information':'missing','information still needed':'missing',
 'coordinated support plan':'actions','learning-support plan':'actions','learning support plan':'actions',
 'recommendations':'actions','practical recommendations':'actions','support plan':'actions','action plan':'actions',
 'interpretation boundary':'limits','interpretation limits':'limits','limitations':'limits',
 'assessment':'assessment','assessment of likely factors':'assessment','likely factors':'assessment',
 'key factors':'assessment','main concerns':'assessment',
}
ANCHOR=re.compile(r'\b(?:primary signal|primary concern|first priority|main issue|most important issue|most actionable insight)\b',re.I)
NEG_BEFORE=re.compile(r'\b(?:no|without|absence of|not|neither)\b(?:[\w\s\-\'’]{0,55})$',re.I)
NEG_AFTER=re.compile(r'^\s*(?:is|are|was|were|has been|have been)?\s*(?:not\b|absent\b|unchanged\b|stable\b|adequate\b)',re.I)
POSITIVE_CONFIDENCE=re.compile(r'\b(?:high|strong|adequate|stable|positive|maintained|intact|remains? confident)\s*(?:mathematics\s*)?$',re.I)
CAUSAL=re.compile(r'\b(?:caused by|caused|causes|cause|leads? to|led to|results? in|resulted in|drives|responsible for)\b',re.I)
HEDGE_OR_NEGATION=re.compile(r'\b(?:no|not|cannot|can\x27t|does not|do not|must not|should not|may|might|could|possible|possibly|whether|uncertain|avoid)\b',re.I)
BOUNDARY_CONTENT=re.compile(r'\b(?:cannot|can\x27t|does not|do not|not sufficient to)\b.{0,90}\b(?:establish|prove|determine|infer|demonstrate)\b.{0,65}\bcaus|'
    r'\b(?:association|prediction)\b.{0,70}\b(?:not|cannot|does not)\b.{0,40}\bcaus|'
    r'\b(?:no|not making|avoid)\s+(?:individual\s+)?causal claims?\b|'
    r'\bpopulation[- ]level\b.{0,80}\b(?:not|cannot|individual|uncertain|limits?)\b|'
    r'\b(?:provisional|uncertain)\s+(?:interpretation|explanation|assessment|conclusion)',re.I)

def clean_heading(line):
    text=line.strip().replace('**','').replace('__','')
    text=re.sub(r'^\s*#{1,6}\s*','',text)
    text=re.sub(r'^\s*\d+[.)]\s*','',text)
    return text.strip().rstrip(':').strip().lower()

def sections(report):
    starts=[];offset=0
    for line in report.splitlines(keepends=True):
        heading=clean_heading(line)
        kind=HEADINGS.get(heading)
        if kind is not None or re.match(r'^\s*#{1,6}\s+',line):
            starts.append({'heading_start':offset,'start':offset+len(line),'kind':kind or 'other','heading':heading})
        offset+=len(line)
    for i,block in enumerate(starts):
        block['end']=starts[i+1]['heading_start'] if i+1<len(starts) else len(report)
        block['text']=report[block['start']:block['end']]
    return starts

def units(text,offset=0):
    # Preserve source offsets. Stop a priority excerpt at sentences/bullets,
    # not at an arbitrary 420-character window extending into another section.
    for m in re.finditer(r'[^\n.!?]+[.!?]?',text):
        left=len(m.group())-len(m.group().lstrip());right=len(m.group().rstrip())
        if right<=left:continue
        yield {'quote':m.group()[left:right],'start':offset+m.start()+left,'end':offset+m.start()+right}

def is_negative(unit,match,label):
    before=unit[:match.start()];after=unit[match.end():]
    # Confine scope to the latest contrast or punctuation-delimited clause.
    before=re.split(r'[,;:]|\bbut\b|\bhowever\b',before,flags=re.I)[-1]
    if NEG_BEFORE.search(before) or NEG_AFTER.search(after):return True
    if label=='classroom_conditions' and re.fullmatch(r'interruptions?',match.group(),re.I):
        if not re.search(r'\b(?:classroom|lesson|class group|disciplinary|off[- ]task)\b',unit,re.I):return True
    if label=='learning_confidence' and POSITIVE_CONFIDENCE.search(before):return True
    return False

def candidates(unit):
    hits=[]
    for label,pattern in SIGNALS.items():
        for m in pattern.finditer(unit['quote']):
            if not is_negative(unit['quote'],m,label):
                hits.append({'label':label,'match_start':unit['start']+m.start(),'matched_text':m.group(),**unit});break
    return sorted(hits,key=lambda h:(h['match_start'],h['label']))

def priority(report,blocks):
    explicit=[b for b in blocks if b['kind']=='priority']
    if explicit:
        regions=explicit;source='bounded_priority_section'
    else:
        # A declared primary issue is stronger evidence than a general mention.
        anchored=[]
        for u in units(report):
            if ANCHOR.search(u['quote']):anchored.append({'text':u['quote'],'start':u['start']})
        if anchored:regions=anchored;source='explicit_primary_issue_sentence'
        else:regions=[b for b in blocks if b['kind']=='assessment'];source='assessment_section_first_issue'
    if not regions:
        return {'signal':None,'candidates':[],'source':'unresolved','review_reason':'No reliably bounded priority or assessment statement; do not guess from the earliest keyword.'}
    for region in regions:
        # A single priority bullet may contain a genuine multi-signal statement.
        for u in units(region['text'],region['start']):
            hits=candidates(u)
            labels=list(dict.fromkeys(h['label'] for h in hits))
            if not labels:continue
            # More than one category in the first issue is not silently resolved
            # by taxonomy order or by whichever category improves agreement.
            if len(labels)>1:
                return {'signal':None,'candidates':hits,'source':source,'review_reason':'Multiple affirmative categories in the first identifiable issue; primary ranking requires review.'}
            return {'signal':labels[0],'candidates':hits,'source':source,'review_reason':None}
    return {'signal':None,'candidates':[],'source':source,'review_reason':'Priority text has no recognized unnegated category; possible wording or taxonomy limitation.'}

def evaluate(report,case_facts,expected_signals):
    assert isinstance(report,str) and isinstance(case_facts,dict)
    blocks=sections(report);p=priority(report,blocks)
    boundary=[];causal=[];hedged=[]
    for u in units(report):
        if BOUNDARY_CONTENT.search(u['quote']):boundary.append(u)
        for m in CAUSAL.finditer(u['quote']):
            before=u['quote'][:m.start()]
            if HEDGE_OR_NEGATION.search(before[-130:]):
                hedged.append({**u,'matched_text':m.group(),'assessment':'negated_or_hedged_expression_not_automatic_error'});continue
            facts=[{'field':k,'quote':v} for k,v in case_facts.items() if isinstance(v,str) and
                any(token in u['quote'].lower() and token in v.lower() for token in ['migraine','fire alarm','illness','left','support','tutoring'])]
            causal.append({**u,'matched_text':m.group(),'assessment':'requires_context_review_not_automatic_causal_error',
                'potentially_relevant_case_facts':facts})
    action_blocks=[b for b in blocks if b['kind']=='actions']
    action_text='\n'.join(b['text'] for b in action_blocks)
    structure=None;structure_evidence={}
    if action_blocks:
        patterns={'action':r'\b(?:provide|conduct|allow|collect|record|monitor|review|arrange|refer|contact|offer|implement|assess|discuss|develop|create|establish|administer|identify|check|share|use)\b',
            'time_window':r'\b(?:week|weeks|day|days|month|months|immediately|daily|weekly|next lesson|next session|next assessment|before|within)\b',
            'review_indicator':r'\b(?:review indicator|review|monitor|record|track|check|reassess|evaluate|log|revisit|observe|indicator|follow[- ]up|compare|comparison)\b'}
        for name,pattern in patterns.items():
            evidence=[]
            for b in action_blocks:
                evidence.extend(u for u in units(b['text'],b['start']) if re.search(pattern,u['quote'],re.I))
            structure_evidence[name]=evidence
        structure=sum(bool(v) for v in structure_evidence.values())/3
    reasons=[]
    if p['review_reason']:reasons.append(p['review_reason'])
    if causal:reasons.append('Unhedged causal wording needs comparison with the supplied case facts; wording alone is not a violation.')
    if not action_blocks:reasons.append('No reliably bounded action/recommendation section; action completeness left unscored.')
    result={'version':VERSION,'primary_signal':p['signal'],'priority_alignment':None if p['signal'] is None else int(p['signal'] in expected_signals),
        'priority_extraction_source':p['source'],'priority_evidence':p['candidates'],
        'explicit_boundary_statement_present':int(bool(boundary)),'boundary_statement_evidence':boundary,
        'causal_claim_review_required':bool(causal),'causal_claim_candidates':causal,'hedged_or_negated_causal_expressions':hedged,
        'action_structure_completeness':structure,'action_structure_evidence':structure_evidence,
        'manual_review_required':bool(reasons),'manual_review_reasons':reasons,
        'overall_educational_quality_score':None,'overall_boundary_compliance_score':None}
    # Every reported quotation must be an exact source substring.
    for collection in [p['candidates'],boundary,causal,hedged]+list(structure_evidence.values()):
        for item in collection:assert report[item['start']:item['end']]==item['quote']
    return result
