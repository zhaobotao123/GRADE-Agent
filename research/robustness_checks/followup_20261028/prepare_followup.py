from common import *
from datetime import datetime,timezone
paths=[ROOT/x for x in ['common.py','prepare_followup.py','random_forest_check.py','full_refit_brr.py']]
paths += [AUDIT/'japan_analysis_data.pkl',Path('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv'),Path('D:/pisa2022/outputs_grade_agent_formal/dml_results_by_pv.csv'),SOURCE/'config.py',SOURCE/'utils_pisa.py',SOURCE/'run_formal_pisa_experiment.py']
design=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),posthoc=True,preregistered=False,reason='Complete missing full-refit replicate-weight computation; add exactly one frozen RF specification, not a search for significance.',factors=['TEACHSUP','MATHEFF','DISCLIM','BELONG','ICTSCH'],PVs=c.PV_MATH_VARS,replicates=80,replicate_fields=[f'W_FSTURWT{i}'for i in range(1,81)],Fay=.5,variance_multiplier=.05,PV_pooling='mean(within_BRR_variance)+1.1*sample_var(PV_full_weight_estimates)',folds=3,fold_type='student_KFold',fold_seed=42,model_seed=42,RF_parameters=dict(c.RF_PARAMS,n_jobs=2),LGBM_parameters=dict(c.LGBM_PARAMS,n_jobs=2),preserve_original_main_results=True,stop_on_significance=False,drop_unfavourable_results=False,D_nuisance_reuse='Within each factor and replicate only, across ten PVs after identical sample/fold/X/weight assertions; never across replicate weights.',preprocessing='Refit training-only, unweighted preprocessing for every replicate/fold; share identical X transformation between nuisance targets.',inference_scope='Fay-BRR refitting sensitivity conditional on frozen student folds, model and hyperparameters; not a proof of all DML complex-design asymptotics or a causal effect.',hashes={str(p):sha(p)for p in paths})
out=ROOT/'frozen_design.json'
assert not out.exists(),'Existing frozen design retained; do not overwrite or refreeze after seeing results.'
save(out,design)
# Algebraic unit checks independent of the learner.
y=np.array([1.,3.,5.,8.]);d=np.array([1.,2.,1.,3.]);w=np.array([1.,2.,3.,4.]);groups=np.array(['A','A','B','B'])
a=residual_estimate(y,np.zeros(4),d,np.zeros(4),w,groups)
b=residual_estimate(y,np.zeros(4),d,np.zeros(4),w*7,groups)
np.testing.assert_allclose(a['coef'],np.sum(w*d*y)/np.sum(w*d*d),atol=1e-14)
np.testing.assert_allclose([a['coef'],a['std_error']],[b['coef'],b['std_error']],atol=1e-14)
assert .05*np.sum((np.ones(80)*2-2)**2)==0
assert np.isclose(.05*np.sum((np.ones(80)*3-2)**2),4)
save(ROOT/'unit_tests.json',dict(weighted_residual_ratio=True,constant_weight_scale_invariance=True,BRR_zero_perturbation=True,BRR_known_perturbation=True))
print('Frozen design and four algebraic tests saved before fitting.',flush=True)

