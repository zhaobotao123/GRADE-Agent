from pathlib import Path

DATA = Path('D:/Users/84130/Desktop/论文/STU_QQQ_SPSS/CY08MSP_STU_QQQ.SAV')
SCHOOL_DATA = Path('D:/Users/84130/Desktop/论文/SCH_QQQ_SPSS/CY08MSP_SCH_QQQ.SAV')
OUT = Path('D:/pisa2022/outputs_grade_agent_multicountry/development_v1')
DEPS = Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/work/pisa_audit_deps')
FACTORS = ['ESCS','ANXMAT','MATHEF21','MATHEFF','TEACHSUP','BELONG','DISCLIM','HOMEPOS','ICTQUAL','ICTSCH','ICTENQ','BULLIED']
BASE = ['AGE','ST004D01T','LANGN']
PVS = [f'PV{i}MATH' for i in range(1,11)]
SEED = 20261022
# Development eligibility only; these are declared design choices, not OECD rules.
MIN_RAW_N = 1000
MIN_SCHOOLS = 30
MIN_FACTOR_COVERAGE = .70
MIN_COMMON_N = 500
MIN_COMMON_FRACTION = .50
FOLDS = 5
TREES = 150
THREADS = 4

def controls(factor, specification):
    x = BASE + ['CNT']
    # Avoid composite-component conditioning as the default specification.
    if factor == 'HOMEPOS':
        x += ['HISEI','PAREDINT']
    elif factor != 'ESCS':
        x += ['ESCS']
    if specification == 'mutual':
        excluded = {factor}
        if factor != 'HOMEPOS':
            excluded.add('HOMEPOS')
        if factor == 'HOMEPOS':
            excluded.add('ESCS')
        x += [v for v in FACTORS if v not in excluded]
    return list(dict.fromkeys(x))
