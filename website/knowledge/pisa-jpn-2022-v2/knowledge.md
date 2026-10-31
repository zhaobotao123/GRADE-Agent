# GRADE-Agent 本地研究证据知识库



版本 pisa-jpn-2022-v2｜本地草稿｜已接入网站对话接口（全量证据上下文注入，非RAG；教育草稿不注入）｜教育解释待作者审核



统计数值来自 sources_manifest.json 对应的CSV快照；问题和支持示例为AI辅助编辑草稿，不是原始统计结果。未整理的名称或建议保留为空。



## 使用边界



- Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect.

- Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance.

- Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds.

- BRR is available for five factors only and remains conditional on frozen student-level folds.

- Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index.

- Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## MATHEFF 数学自我效能感



记录ID：PISA2022-JPN-MATHEFF

证据类别：positive_association_PV_direction_consistent

SHAP mean_abs_shap=29.529455195853778; rank=1（仅预测贡献，无正负方向）。

主DML：coef=28.89819444063561; SE=1.5418609790079032; p=0.0; 推导95%CI=[25.87614692178012, 31.9202419594911]。来源：sources/dml.csv。

敏感性 extra_trees：coef=32.08280073103966; p=0.0; 95%CI=[28.892427899713297, 35.273173562366026]。

敏感性 random_forest：coef=31.65968121249822; p=5.081448805168377e-81; 95%CI=[28.404664631058406, 34.91469779393803]。

敏感性 brr：coef=28.898194440631197; p=2.184686649062458e-62; 95%CI=[25.500403789600476, 32.29598509166192]。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：学生对数学任务能力的自我判断

追问草稿：遇到不会的题时，学生通常如何判断自己能否完成？

支持示例草稿：可与教师一起选择适当难度的任务，观察尝试过程和反馈。



## FAMCON (名称待整理)



记录ID：PISA2022-JPN-FAMCON

证据类别：prediction_only

SHAP mean_abs_shap=9.513808891278734; rank=2（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTWKDY (名称待整理)



记录ID：PISA2022-JPN-ICTWKDY

证据类别：prediction_only

SHAP mean_abs_shap=9.152137845309378; rank=3（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ESCS 经济社会文化地位



记录ID：PISA2022-JPN-ESCS

证据类别：weak_or_context_sensitive

SHAP mean_abs_shap=7.604972885494415; rank=4（仅预测贡献，无正负方向）。

主DML：coef=16.414302943543785; SE=11.812702568595418; p=0.16466654297325967; 推导95%CI=[-6.738594090903234, 39.5671999779908]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：家庭经济社会文化背景指数

追问草稿：当前学习机会或资源是否存在具体障碍？

支持示例草稿：可关注能够提供的支持机会，避免按背景给学生贴标签。



## HOMEPOS 家庭物质资源



记录ID：PISA2022-JPN-HOMEPOS

证据类别：weak_or_context_sensitive

SHAP mean_abs_shap=7.025876761762406; rank=5（仅预测贡献，无正负方向）。

主DML：coef=7.5238931249628225; SE=5.105580061350108; p=0.1405729461216918; 推导95%CI=[-2.483043795283389, 17.530830045209033]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：家庭拥有的相关资源指数

追问草稿：家庭中哪些实际资源有助于或限制当前任务？

支持示例草稿：可根据已确认的资源障碍寻找可行支持，避免推断家庭能力或意愿。



## DISCLIM 课堂纪律氛围



记录ID：PISA2022-JPN-DISCLIM

证据类别：positive_association_PV_direction_consistent

SHAP mean_abs_shap=5.716057201762529; rank=6（仅预测贡献，无正负方向）。

主DML：coef=13.7354205431832; SE=1.8988409510177036; p=4.705125178361413e-13; 推导95%CI=[10.0136922791885, 17.457148807177898]。来源：sources/dml.csv。

敏感性 extra_trees：coef=14.852764388130055; p=1.5121237595394632e-13; 95%CI=[10.911436348422184, 18.794092427837924]。

敏感性 random_forest：coef=14.091527990984872; p=1.5945414692092898e-12; 95%CI=[10.182830594159668, 18.000225387810076]。

敏感性 brr：coef=13.735420543179155; p=8.280395593503787e-14; 95%CI=[10.129513501200266, 17.34132758515804]。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：学生报告的课堂秩序与学习环境

追问草稿：学生描述的课堂秩序或干扰具体是什么？

支持示例草稿：可先记录具体课堂干扰，再与教师商量适合该课堂的调整。



## COGACMCO (名称待整理)



记录ID：PISA2022-JPN-COGACMCO

证据类别：prediction_only

SHAP mean_abs_shap=5.269627259075511; rank=7（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTWKEND (名称待整理)



记录ID：PISA2022-JPN-ICTWKEND

证据类别：prediction_only

SHAP mean_abs_shap=5.2569607283118085; rank=8（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## FAMSUP (名称待整理)



记录ID：PISA2022-JPN-FAMSUP

证据类别：prediction_only

SHAP mean_abs_shap=4.911937988273848; rank=9（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTFEED (名称待整理)



记录ID：PISA2022-JPN-ICTFEED

证据类别：prediction_only

SHAP mean_abs_shap=4.543149221128817; rank=10（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## COGACRCO (名称待整理)



记录ID：PISA2022-JPN-COGACRCO

证据类别：prediction_only

SHAP mean_abs_shap=4.293993776818995; rank=11（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTOUT (名称待整理)



记录ID：PISA2022-JPN-ICTOUT

证据类别：prediction_only

SHAP mean_abs_shap=4.021648843070302; rank=12（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## HISEI (名称待整理)



记录ID：PISA2022-JPN-HISEI

证据类别：prediction_only

SHAP mean_abs_shap=3.6823210781186497; rank=13（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## TEACHSUP 教师支持



记录ID：PISA2022-JPN-TEACHSUP

证据类别：negative_association_requires_contextual_review

SHAP mean_abs_shap=3.620323677375083; rank=14（仅预测贡献，无正负方向）。

主DML：coef=-3.2407347221795346; SE=1.2006973986387763; p=0.006953904910007136; 推导95%CI=[-5.594101623511536, -0.8873678208475329]。来源：sources/dml.csv。

敏感性 extra_trees：coef=-2.3119492435809166; p=0.07670043272603033; 95%CI=[-4.871794885048446, 0.24789639788661244]。

敏感性 random_forest：coef=-2.786596713072606; p=0.029146660009029386; 95%CI=[-5.290211731317315, -0.28298169482789737]。

敏感性 brr：coef=-3.2407347221800054; p=0.01898157925441585; 95%CI=[-5.948328200284835, -0.5331412440751757]。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions. ExtraTrees pooled interval includes zero (p approximately .0767); retain learner sensitivity despite significant RF and BRR results. Negative estimate does not show that teacher support harms achievement.

编辑草稿，待审核：学生报告获得的教师支持

追问草稿：额外帮助是在困难出现之前还是之后开始的？

支持示例草稿：可了解当前支持的内容和时机，与教师共同讨论需要调整的地方。



## ICTENQ ICT探究与使用



记录ID：PISA2022-JPN-ICTENQ

证据类别：weak_or_context_sensitive

SHAP mean_abs_shap=3.4587002484275153; rank=15（仅预测贡献，无正负方向）。

主DML：coef=-1.2457549501449043; SE=1.3329954110518734; p=0.3500186754832195; 推导95%CI=[-3.858425955806576, 1.3669160555167674]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：与ICT探究使用相关的问卷指标

追问草稿：学生在什么任务中怎样使用数字工具？

支持示例草稿：可围绕具体任务讨论工具使用方式，不按统计方向增加或减少使用。



## ICTEFFIC (名称待整理)



记录ID：PISA2022-JPN-ICTEFFIC

证据类别：prediction_only

SHAP mean_abs_shap=3.433904020112442; rank=16（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## BELONG 学校归属感



记录ID：PISA2022-JPN-BELONG

证据类别：negative_association_requires_contextual_review

SHAP mean_abs_shap=3.4148910494525255; rank=17（仅预测贡献，无正负方向）。

主DML：coef=-5.957036508798989; SE=1.223924210140164; p=1.1321264485886218e-06; 推导95%CI=[-8.35592796067371, -3.558145056924268]。来源：sources/dml.csv。

敏感性 extra_trees：coef=-5.776356963759732; p=1.9207506607443747e-06; 95%CI=[-8.15401973229233, -3.3986941952271343]。

敏感性 random_forest：coef=-6.0503587091912445; p=9.725928207363427e-07; 95%CI=[-8.471888808074333, -3.6288286103081573]。

敏感性 brr：coef=-5.957036508795866; p=5.75472293946555e-05; 95%CI=[-8.859496320247551, -3.0545766973441806]。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions. Negative association is not evidence to reduce belonging or resource provision; possible contextual explanations are hypotheses, not established mechanisms.

编辑草稿，待审核：学生对学校成员身份和被接纳感的报告

追问草稿：学生最近在学校的人际体验和归属感有何变化？

支持示例草稿：可先听取学生具体经历，再与可信赖的学校人员讨论支持。



## ICTINFO (名称待整理)



记录ID：PISA2022-JPN-ICTINFO

证据类别：prediction_only

SHAP mean_abs_shap=3.329541995060464; rank=18（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## MATHEF21 21世纪数学自我效能感



记录ID：PISA2022-JPN-MATHEF21

证据类别：directionally_unstable_across_PVs

SHAP mean_abs_shap=3.2829205486175845; rank=19（仅预测贡献，无正负方向）。

主DML：coef=-0.001370558591925608; SE=1.6266361314450244; p=0.9993277246277497; 推导95%CI=[-3.1895773762241735, 3.186836259040322]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：与21世纪数学任务相关的自我效能问卷构念

追问草稿：哪些类型的数学任务让学生缺乏把握？

支持示例草稿：可与教师核实具体任务表现和支持需求，避免从该估计推断个体原因。



## ICTSUBJ (名称待整理)



记录ID：PISA2022-JPN-ICTSUBJ

证据类别：prediction_only

SHAP mean_abs_shap=3.054312000747094; rank=20（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ST004D01T (名称待整理)



记录ID：PISA2022-JPN-ST004D01T

证据类别：prediction_only

SHAP mean_abs_shap=3.0464734172353647; rank=21（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## AGE (名称待整理)



记录ID：PISA2022-JPN-AGE

证据类别：prediction_only

SHAP mean_abs_shap=2.7933098113822616; rank=22（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## PAREDINT (名称待整理)



记录ID：PISA2022-JPN-PAREDINT

证据类别：prediction_only

SHAP mean_abs_shap=2.7275672534585285; rank=23（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTSCH 学校ICT资源



记录ID：PISA2022-JPN-ICTSCH

证据类别：negative_association_requires_contextual_review

SHAP mean_abs_shap=2.6083212393491855; rank=24（仅预测贡献，无正负方向）。

主DML：coef=-4.521848336224393; SE=1.2214229907321492; p=0.00021380968693929248; 推导95%CI=[-6.915837398059406, -2.12785927438938]。来源：sources/dml.csv。

敏感性 extra_trees：coef=-5.485663459409084; p=2.24760991105466e-05; 95%CI=[-8.02218615801127, -2.949140760806899]。

敏感性 random_forest：coef=-5.48570980399804; p=1.9208191406401426e-05; 95%CI=[-8.001395678834959, -2.9700239291611212]。

敏感性 brr：coef=-4.521848336225235; p=0.004423356807756827; 95%CI=[-7.6356201001288415, -1.4080765723216273]。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions. Negative association is not evidence to reduce belonging or resource provision; possible contextual explanations are hypotheses, not established mechanisms.

编辑草稿，待审核：学校相关的信息通信技术资源

追问草稿：学生实际能使用哪些资源，如何使用，有什么困难？

支持示例草稿：可核实实际可用性和用途；负向估计不能作为减少资源的理由。



## ICTREG (名称待整理)



记录ID：PISA2022-JPN-ICTREG

证据类别：prediction_only

SHAP mean_abs_shap=2.188023142446073; rank=25（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## FAMSUPSL (名称待整理)



记录ID：PISA2022-JPN-FAMSUPSL

证据类别：prediction_only

SHAP mean_abs_shap=2.1346862425435043; rank=26（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## PROBSELF (名称待整理)



记录ID：PISA2022-JPN-PROBSELF

证据类别：prediction_only

SHAP mean_abs_shap=1.9329877976826186; rank=27（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## SDLEFF (名称待整理)



记录ID：PISA2022-JPN-SDLEFF

证据类别：prediction_only

SHAP mean_abs_shap=1.8264379700084796; rank=28（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ICTQUAL 数字资源质量



记录ID：PISA2022-JPN-ICTQUAL

证据类别：weak_or_context_sensitive

SHAP mean_abs_shap=1.7320537540860237; rank=29（仅预测贡献，无正负方向）。

主DML：coef=2.3731361975189182; SE=1.2745377792500543; p=0.06260896820491757; 推导95%CI=[-0.12495784981118829, 4.871230244849025]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：学生报告的数字资源质量

追问草稿：数字资源是否满足当前任务，需要改进的具体方面是什么？

支持示例草稿：可先核实资源使用障碍，再考虑适合学习任务的支持。



## FEELLAH (名称待整理)



记录ID：PISA2022-JPN-FEELLAH

证据类别：prediction_only

SHAP mean_abs_shap=1.573934930347676; rank=30（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## EXPOFA (名称待整理)



记录ID：PISA2022-JPN-EXPOFA

证据类别：prediction_only

SHAP mean_abs_shap=1.406022158814964; rank=31（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## RELATST (名称待整理)



记录ID：PISA2022-JPN-RELATST

证据类别：prediction_only

SHAP mean_abs_shap=1.3159618238671524; rank=32（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## LEARRES (名称待整理)



记录ID：PISA2022-JPN-LEARRES

证据类别：prediction_only

SHAP mean_abs_shap=1.315938297505779; rank=33（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## MATHPERS (名称待整理)



记录ID：PISA2022-JPN-MATHPERS

证据类别：prediction_only

SHAP mean_abs_shap=1.1274105437740733; rank=34（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## EXPO21ST (名称待整理)



记录ID：PISA2022-JPN-EXPO21ST

证据类别：prediction_only

SHAP mean_abs_shap=1.1232849832160263; rank=35（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## SCHSUST (名称待整理)



记录ID：PISA2022-JPN-SCHSUST

证据类别：prediction_only

SHAP mean_abs_shap=1.0076465415640607; rank=36（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## HISCED (名称待整理)



记录ID：PISA2022-JPN-HISCED

证据类别：prediction_only

SHAP mean_abs_shap=0.8577931422653317; rank=37（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## BULLIED 遭受欺凌



记录ID：PISA2022-JPN-BULLIED

证据类别：weak_or_context_sensitive

SHAP mean_abs_shap=0.7103790337677243; rank=38（仅预测贡献，无正负方向）。

主DML：coef=1.3838404997345481; SE=1.5081139223421671; p=0.3588299971020519; 推导95%CI=[-1.5720627880560993, 4.339743787525196]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions. Safeguarding takes precedence over pooled significance; weak academic association never means bullying is safe.

编辑草稿，待审核：学生报告的欺凌经历

追问草稿：如果学生愿意说明，具体发生了什么，目前是否安全？

支持示例草稿：若已报告欺凌或不安全，应优先联系可信赖成人及学校学生保护人员；不能因统计不显著而忽视。



## LANGN (名称待整理)



记录ID：PISA2022-JPN-LANGN

证据类别：prediction_only

SHAP mean_abs_shap=0.6223938047722323; rank=39（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## ANXMAT 数学焦虑



记录ID：PISA2022-JPN-ANXMAT

证据类别：directionally_unstable_across_PVs

SHAP mean_abs_shap=0.5698244073967893; rank=40（仅预测贡献，无正负方向）。

主DML：coef=-0.15543171909974607; SE=1.1954408312665936; p=0.8965502709155049; 推导95%CI=[-2.4984957483822696, 2.1876323101827775]。来源：sources/dml.csv。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.

编辑草稿，待审核：数学相关焦虑的学生自我报告

追问草稿：哪些数学情境让学生感到紧张，何时开始？

支持示例草稿：可先了解具体情境和可获得的支持，不据此诊断心理障碍。



## ICTHOME (名称待整理)



记录ID：PISA2022-JPN-ICTHOME

证据类别：prediction_only

SHAP mean_abs_shap=0.2898665251509741; rank=41（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.



## GRADE (名称待整理)



记录ID：PISA2022-JPN-GRADE

证据类别：prediction_only

SHAP mean_abs_shap=0.0; rank=42（仅预测贡献，无正负方向）。

未进行对应主DML估计；不可补造系数或调整关联。

解释边界：Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect. Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance. Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds. BRR is available for five factors only and remains conditional on frozen student-level folds. Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index. Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.