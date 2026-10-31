"""Recover only unambiguous metric-key typos from existing judge responses.

Does not regenerate reports or change scores, quotations, rubric, or protocol.
Waits for the locked worker to stop before changing any failed status file.
"""
import argparse,ctypes,json,os,re,subprocess,sys,time
from pathlib import Path
import semantic_review300 as review

ALIASES={'recommendation_actionbility':'recommendation_actionability'}

def markdown_quote(report,quote):
    """Map unchanged words across bold/code delimiters back to exact source."""
    try:return review.quote_span(report,quote)['quote']
    except ValueError:pass
    def normalized(text):
        excluded=set()
        for m in re.finditer(r'\*\*|__|`+',text):excluded.update(range(m.start(),m.end()))
        chars=[];positions=[]
        for i,c in enumerate(text):
            if i in excluded:continue
            if c.isspace():
                if chars and chars[-1]==' ':continue
                c=' '
            chars.append(c);positions.append(i)
        return ''.join(chars),positions
    source,offsets=normalized(report);target,_=normalized(quote)
    start=source.find(target)
    if start<0:raise ValueError('Not a delimiter-only quotation mismatch')
    return report[offsets[start]:offsets[start+len(target)-1]+1]

def alive(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        result=ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(result))) and result.value==259
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))

def recover():
    lock,mapping=review.prepare();items={m['item_id']:m for m in mapping};count=0;unresolved=[]
    for stage in ['first','repeat','adjudication']:
        for path in sorted((review.ROOT/stage).glob('*.json')):
            failed=json.loads(path.read_text(encoding='utf-8'))
            if failed['status']=='completed':continue
            candidates=sorted((review.ROOT/'calls'/stage/path.stem).glob('*.json'),reverse=True)
            fixed=None
            for candidate in candidates:
                call=json.loads(candidate.read_text(encoding='utf-8'));response=call.get('response',{})
                try:
                    choice=response['choices'][0]
                    assert choice['finish_reason']=='stop'
                    assessment=json.loads(choice['message']['content']);ratings=assessment['ratings'];changes={}
                    for bad,good in ALIASES.items():
                        if bad in ratings and good not in ratings:
                            ratings[good]=ratings.pop(bad);changes[bad]=good
                    quote_repairs=[];discarded_quotes=[]
                    for metric,rating in ratings.items():
                        verified=[];rejected=[]
                        for quote in rating.get('report_evidence',[]):
                            try:canonical=markdown_quote(items[path.stem]['report'],quote)
                            except ValueError:
                                rejected.append(quote);continue
                            if canonical!=quote:
                                quote_repairs.append({'metric':metric,'original_quote':quote,'source_quote':canonical})
                            verified.append(canonical)
                        # Never invent a replacement quotation or change a rating.
                        # An optional second quote can be discarded only if this
                        # same rating already has a directly verified source quote.
                        if rejected:
                            assert verified,'No source-grounded evidence remains for this rating'
                            discarded_quotes.extend({'metric':metric,'unsupported_quote':q} for q in rejected)
                        rating['report_evidence']=verified
                    assert changes or quote_repairs or discarded_quotes,'No approved mechanical correction'
                    assessment=review.validate(assessment,items[path.stem])
                    assert 'flash' in response.get('model','').lower()
                    fixed={'status':'completed','signature':lock['signature'],'item_id':path.stem,'stage':stage,
                        'assessment':assessment,'model_returned':response.get('model'),'response_id':response.get('id'),
                        'usage':response.get('usage'),'completed_utc':review.now(),
                        'mechanical_schema_recovery':{'source_call':str(candidate),'key_renames_only':changes,
                            'delimiter_only_quote_canonicalizations':quote_repairs,'no_rating_or_word_changes':True,
                            'discarded_unverifiable_extra_quotes':discarded_quotes,
                            'recovery_script_sha256':review.sha(Path(__file__))}}
                    break
                except (KeyError,ValueError,AssertionError,TypeError):continue
            if fixed:
                archive=review.ROOT/'schema_recovery'/stage/(path.stem+'_original_failure.json')
                assert not archive.exists()
                review.save(archive,failed);review.save(path,fixed);count+=1
            else:unresolved.append(stage+'/'+path.stem)
    review.save(review.ROOT/'schema_recovery'/'recovery_summary.json',{
        'time':review.now(),'recovered_count':count,'unresolved':unresolved,'approved_key_aliases':ALIASES,
        'method':'Revalidate existing raw response after metric-key spelling or delimiter-only quote canonicalization. Discard an unverifiable extra quotation only when the same rating retains a verified source quotation. Never alter scores or fabricate replacement evidence; all raw responses and discarded quotes retained.',
        'protocol_and_generated_reports_unchanged':True})
    return count,unresolved

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--wait-pid',type=int,required=True);args=parser.parse_args()
    key=sys.stdin.readline().strip();assert key
    while alive(args.wait_pid):time.sleep(15)
    # Each restart only follows a successful, purely mechanical recovery.
    for _ in range(30):
        count,unresolved=recover()
        if unresolved or not count:
            print('SCHEMA_RECOVERY_STOP recovered='+str(count)+' unresolved='+str(unresolved),flush=True);break
        command=[sys.executable,'-X','utf8',str(Path(review.__file__)),'--run']
        p=subprocess.Popen(command,stdin=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        p.stdin.write((key+'\n').encode());p.stdin.flush();p.stdin.close();p.wait()
        if (review.ROOT/'status.json').exists():
            state=json.loads((review.ROOT/'status.json').read_text(encoding='utf-8'))
            if state.get('status') in ['completed','needs_human_review']:break
    key=None

if __name__=='__main__':main()
