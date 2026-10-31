"""Weighted descriptive diagnostics. Not causal or replacement DML estimates."""
import json
import numpy as np
import pandas as pd
import config as c

OUT=c.OUT.parent/'reversal_diagnostics_v1'
TARGETS=['MATHEF21','TEACHSUP','BELONG']

def correlation(mean,cross):
    cov=cross-np.outer(mean,mean)
    sd=np.sqrt(np.maximum(np.diag(cov),0))
    return cov/np.outer(sd,sd)

def main():
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((c.OUT/'sample_manifest.json').read_text(encoding='utf-8'))
    cols=c.FACTORS+['PV1MATH']
    records=[]; means=[]; moments=[]; within_cov=[]
    for cnt in manifest['countries']:
        d=pd.read_pickle(c.OUT/f'country_{cnt}.pkl')
        d=d.loc[d.common_sample]
        x=d[cols].to_numpy(float); w=d.W_FSTUWT.to_numpy(float)
        w=w/w.sum()
        mean=w@x; cross=(x*w[:,None]).T@x
        corr=correlation(mean,cross)
        means.append(mean); moments.append(cross)
        within_cov.append(cross-np.outer(mean,mean))
        for target in TARGETS:
            for j,other in enumerate(cols):
                if other==target: continue
                records.append({'CNT':cnt,'target':target,'other':other,'weighted_correlation':corr[cols.index(target),j],'n':len(d),'scope':'descriptive_within_system_PV1_only'})
    pd.DataFrame(records).to_csv(OUT/'within_system_correlations.csv',index=False,encoding='utf-8-sig')
    pooled=correlation(np.mean(means,axis=0),np.mean(moments,axis=0))
    covariance=np.mean(within_cov,axis=0)
    sd=np.sqrt(np.diag(covariance)); within=covariance/np.outer(sd,sd)
    pd.DataFrame(pooled,index=cols,columns=cols).to_csv(OUT/'equal_system_pooled_correlations.csv',encoding='utf-8-sig')
    pd.DataFrame(within,index=cols,columns=cols).to_csv(OUT/'equal_system_within_centered_correlations.csv',encoding='utf-8-sig')
    summary=[]
    a=pd.DataFrame(records)
    for target in TARGETS:
        g=a[(a.target==target)&(a.other=='PV1MATH')]
        peers=[(cols[j],float(within[cols.index(target),j])) for j in range(len(c.FACTORS)) if cols[j]!=target]
        summary.append({'target':target,'positive_raw_within_systems':int((g.weighted_correlation>0).sum()),'negative_raw_within_systems':int((g.weighted_correlation<0).sum()),'pooled_raw_correlation_with_PV1':float(pooled[cols.index(target),-1]),'within_centered_correlation_with_PV1':float(within[cols.index(target),-1]),'strongest_absolute_within_centered_factor_correlations':sorted(peers,key=lambda p:abs(p[1]),reverse=True)[:3]})
    report={'scope':'descriptive_only_not_adjusted_not_causal','systems':len(means),'outcome':'PV1MATH_only_for_diagnostics','results':summary,'remaining':'Need targeted DML control-set sensitivity and country-specific estimates; these correlations cannot establish the cause of coefficient reversals.'}
    (OUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
