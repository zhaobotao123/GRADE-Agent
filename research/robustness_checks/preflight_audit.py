"""Read-only preflight. No model fitting and no original output modification."""
from pathlib import Path
import os,sys,json,hashlib,ast,csv,platform
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='4'
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'))
sys.path.insert(0,str(BASE/'work/figure_python_deps'))
import numpy as np,pandas as pd,sklearn,pyreadstat,lightgbm,shap
SOURCE=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
scripts={p.name:{'path':str(p),'sha256':digest(p)} for p in SOURCE.glob('*.py')}
sources=[Path('D:/pisa2022')/s for s in ['outputs_five_models_tuned_42_features/tuned_five_model_metrics_by_pv.csv','outputs_five_models_tuned_42_features/training_cv_all_candidates.csv','outputs_five_models_tuned_42_features/training_cv_selected_models.csv','outputs_final_shap_42_features/shap_importance_by_pv.csv','outputs_grade_agent_formal/dml_results_by_pv.csv','outputs_grade_agent_formal/dml_results_pooled.csv','outputs_grade_agent_formal/selected_variables.csv']]
scores=BASE/'outputs/manuscript_teacher_evaluation_v21_20261027/teacher_scores_long.csv';sources.append(scores)
_,meta=pyreadstat.read_sav('D:/Users/84130/Desktop/论文/STU_QQQ_SPSS/CY08MSP_STU_QQQ.SAV',metadataonly=True)
rep=[f'W_FSTURWT{i}'for i in range(1,81)]
assert all(c in meta.column_names for c in rep)
report={'stage':'code_audit_before_any_new_model_fit','scripts':scripts,'original_result_hashes':{str(p):digest(p)for p in sources},'versions':{x.__name__:x.__version__ for x in [np,pd,sklearn,pyreadstat,lightgbm,shap]},'python':sys.version,'cpu_count':os.cpu_count(),'replicate_weights':rep,'models_saved':[],'prior_sample_audit':json.loads((BASE/'outputs/submission_audit_v33_20261028/raw_sample_audit.json').read_text(encoding='utf-8'))}
assert report['prior_sample_audit']['sample_n']==5760
(ROOT/'code_audit_before_fitting.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text='''# 主分析代码审查（补充拟合之前）

主分析代码位于 C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment/ 。本次审查了 config.py、预测调参/SHAP/预处理/DML/合并脚本，并对原始输出建立SHA256清单。主结果保持只读；所有新结果写入本目录。

## 预测

主分析使用五模型调参脚本tune_existing_five_models.py而非较早的未调参比较版本。它先按日本及正学生权重筛选；42预测变量在种子42训练集按缺失率筛选确定。主划分80/20、4608/1152，外层树模型CV三折，MATH_MEAN作调参目标；五种模型分别为RandomForest、ExtraTrees、RidgeCV、ElasticNetCV、LightGBM，最终在十个PV分别重拟合/评价。ElasticNetCV内部5折，RidgeCV默认内部选择。

**训练确实使用权重**：调参和最终拟合均直接传入sample_weight=w_train；CV验证和测试指标亦加权。缺失值填补、类别频数分组和标准化未作加权。R²=1−Σw(y−ŷ)²/Σw(y−加权均值)²；RMSE=√加权均方误差；MAE=加权绝对误差均值。当前五模型脚本没有导出持久化拟合模型，复现需要重新拟合，不将其他项目缓存当作本次主模型。

## SHAP

recompute_final_shap.py重新拟合选定的加权LightGBM，每个PV均使用种子42划分，固定最终参数。一个default_rng(42)在PV循环中顺序均匀无放回抽取最多3000训练行；抽样不是PPS。对绝对SHAP按所抽行的最终学生权重求均值，再将编码列汇总回原变量；最后平均十个PV。注意这是“先取各编码列绝对值再汇总”，不是将带符号SHAP先合并再取绝对值。

## DML

12保留因素来自初始14因素缺失率筛选；调整池共21列，每次焦点因素以外20列进入干扰模型。含常量CNT，但不含学生/学校ID；学校ID仅用于聚类。LightGBM500树/31叶/学习率.03，三折随机KFold种子42（不是按学校分折）。预处理在每折训练部分拟合；焦点因素、PV、正权重及学校ID须观测。权重用于两个干扰拟合和最终残差乘积比值。原工具有TypeError时无权重回退分支；本次执行会显式验证实际模型支持sample_weight并记录，不默认为加权。学校聚类score=Σ学校 w·D残差·最终残差，乘G/(G−1)修正。PV合并为平均系数、平均方差+(1+1/10)×PV系数样本方差。现有结果为模型式聚类SE，不是PISA复制权重方差。

## 冻结补充设计

原主分析不变。先检查种子42的LightGBM十PV预测/SHAP和关键五因素DML是否能逐行复现，再开展10个额外划分种子[0,1,7,13,21,73,101,202,365,999]。只改变划分/内层CV种子，模型和SHAP随机源保持42，减少同时改变多个随机过程。每次划分复用原LightGBM五组候选参数，在训练内三折CV重新选择；42变量名单事先固定。每PV拟合和SHAP方法同原流程。替代DML至少用ExtraTrees（原配置500树、min_samples_leaf3、max_features.8、seed42），不依结果调参；只有关键主DML复现通过后才开始替代模型。各输出全部保留。

复制权重方法另查OECD官方技术报告后决定可行性；不提前承诺全流程设计式DML方差已实现。
'''
(ROOT/'audit_report.md').write_text(text,encoding='utf-8')
print(json.dumps({'versions':report['versions'],'cpu_count':report['cpu_count'],'replicate_weight_count':len(rep),'original_sources_hashed':len(sources)},indent=2),flush=True)
