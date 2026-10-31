"""Author-designed controlled cases, not real pupils or independently validated gold."""
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/pisa2022/outputs_grade_agent_flash_multiturn_v1')
DOMAINS = ['confidence','classroom','support','context','resources']
FACTORS = ['confidence','anxiety','classroom','support_timing','belonging','school_ict',
    'home_resources','family_engagement','language','health_attendance','assessment_event',
    'independent_work','bullying']
NORMAL = {
 'confidence':'学生愿意尝试新题，做错后会检查步骤；尚未进行标准化心理测量。',
 'classroom':'本月教师课堂记录显示秩序稳定，未报告持续中断。',
 'support':'教师常规反馈安排未变化；没有额外辅导开始时间的变化。',
 'context':'没有提供近期健康、出勤、教学语言或安全状况的核实记录。',
 'resources':'学生和家长均报告有固定学习空间，所需教材可以获得。'}

# id, split, family, opening, domain facts, supported factors by domain, required inquiry domains
PROFILES = [
 ('D01','dev','confidence','七年级学生近六周三次数学测验逐次下降。', {'confidence':'学生说自己永远学不会数学，遇到第一处错误就停笔；教师作业记录也发现这种表现。'}, {'confidence':['confidence']}, ['confidence','context']),
 ('D02','dev','classroom','八年级学生本学期在小组课上的数学任务完成率下降。', {'classroom':'小组课每节被同伴闲聊打断多次，学生常来不及看完例题；同日安静自习时能继续完成。'}, {'classroom':['classroom']}, ['classroom','confidence']),
 ('D03','dev','support','家长说学生数学低分期间接受了更多帮助。', {'support':'记录显示低分出现在九月，额外辅导十月才开始；学生有提示能完成，独立做题仍等教师开头。'}, {'support':['support_timing','independent_work']}, ['support','confidence']),
 ('D04','dev','resources','学生近一个月数学作业漏交次数增加。', {'resources':'家中搬迁后没有可用教材，也没有安静写作业的地方，学生说多数晚上无法完成练习。'}, {'resources':['home_resources']}, ['resources','context']),
 ('D05','dev','anxiety','学生平时数学作业尚可，最近两次限时测验明显偏低。', {'confidence':'学生愿意学数学，但说看到倒计时就紧张发抖，脑子空白；没有临床诊断。'}, {'confidence':['anxiety']}, ['confidence','context']),
 ('D06','dev','language','学生更换教学语言后，数学应用题成绩下降。', {'context':'学生此前使用另一教学语言。相同数学关系改成其熟悉语言后能作答，尚未做正式语言需求评估。'}, {'context':['language']}, ['context','confidence']),
 ('D07','dev','health','学生近三周数学课堂练习常未完成。', {'context':'出勤记录显示这三周多次缺课；学生报告睡眠不足，相关健康情况尚未经过专业核实。'}, {'context':['health_attendance']}, ['context','classroom']),
 ('D08','dev','safety','学生最近拒绝参加数学讨论，但独立书面任务仍能完成。', {'context':'学生说同学持续威胁其不得在数学课发言，害怕进教室；尚未向学校指定负责人报告。'}, {'context':['bullying']}, ['context']),
 ('D09','dev','mixed','学生数学表现有波动，家长希望找到主要关注点。', {'confidence':'学生做错后很快放弃，认为努力没有用。','classroom':'最近数学课经常因喧闹暂停讲解。'}, {'confidence':['confidence'],'classroom':['classroom']}, ['confidence','classroom']),
 ('D10','dev','insufficient','一位亲属只说孩子数学似乎不如以前。', {d:'未知。没有提供可核实的学生陈述、记录或观察。' for d in DOMAINS}, {}, ['confidence','classroom','support','context','resources']),
 ('T01','test','confidence','八年级学生连续四份数学练习完成题量减少。', {'confidence':'教师观察学生一遇到不会的步骤就合上本子；学生说即便练习也不可能进步。'}, {'confidence':['confidence']}, ['confidence','context']),
 ('T02','test','confidence','九年级学生的非限时数学练习近两个月持续下降。', {'confidence':'学生会开头，但一处算错后便擦掉整题并放弃，明确说自己没有数学能力。','context':'出勤和教学语言未变化，没有单次测验中断记录；安全情况仍未核实。'}, {'confidence':['confidence']}, ['confidence','context']),
 ('T03','test','confidence','教师发现学生近期数学订正任务经常空白。', {'confidence':'学生解释留空是因为认定自己改了也会错，家长观察到其不再尝试原来会做的题。'}, {'confidence':['confidence']}, ['confidence','support']),
 ('T04','test','classroom','学生数学笔记和当堂练习的遗漏明显增多。', {'classroom':'课堂观察记录显示同伴持续喊话，教师多次停课管理；学生说因此漏听了解题步骤。'}, {'classroom':['classroom']}, ['classroom','confidence']),
 ('T05','test','classroom','同一学生在不同数学课时的完成率差异较大。', {'classroom':'晚间安静辅导能完成任务；下午班级课多次被走动和谈话中断，教师记录与学生叙述一致。'}, {'classroom':['classroom']}, ['classroom','support']),
 ('T06','test','classroom','学生换到新班后数学练习越来越难完成。', {'classroom':'新班持续喧闹，讲解常中途停止，学生记下多次没能听全例题的日期。','context':'数学教材和教学语言没有变化；未提供健康或安全核实记录。'}, {'classroom':['classroom']}, ['classroom','context']),
 ('T07','test','support','学校发现成绩较低的学生近期获得的数学支持最多。', {'support':'记录明确：三次低分发生在加课前，支持是随后按学习困难分配的。学生目前仍需提示才能独立启动解题。'}, {'support':['support_timing','independent_work']}, ['support','confidence']),
 ('T08','test','support','家长担心每周加了数学辅导以后孩子还是低分。', {'support':'旧成绩单显示辅导开始前已经低分两个月。学生能跟着例题模仿，但换一道题就等家长提示。'}, {'support':['support_timing','independent_work']}, ['support','confidence']),
 ('T09','test','support','学生获得学习平台账号后数学表现仍然偏低。', {'support':'账号和教师一对一帮助均在低分后才安排；学生说没有提示就不知先做哪一步。','resources':'平台能正常使用，学校也提供纸质教材，没有报告设备或材料短缺。'}, {'support':['support_timing','independent_work']}, ['support','resources']),
 ('T10','test','resources','学生放学后的数学练习量最近下降。', {'resources':'家长说晚间共用一间嘈杂房间，学生无法找到安静学习位置，教材也暂时缺失。'}, {'resources':['home_resources']}, ['resources','context']),
 ('T11','test','resources','教师发现学生近几周数学作业常漏掉整页。', {'resources':'学生说明家里无法获得指定练习资料，也没有其他可用版本；教师确认尚未提供替代材料。'}, {'resources':['home_resources']}, ['resources','support']),
 ('T12','test','resources','学生的校内数学任务完成正常，回家练习常中断。', {'resources':'家庭学习空间正在长期施工，学生多数晚上没有可用桌面；不是因学校账号故障而中断。'}, {'resources':['home_resources']}, ['resources','context']),
 ('T13','test','anxiety','学生能口头解释数学方法，却在测验中频繁留空。', {'confidence':'学生说一到考试就心跳快并担心犯错，平时不觉得自己完全学不会；没有心理疾病诊断。'}, {'confidence':['anxiety']}, ['confidence','context']),
 ('T14','test','anxiety','学生家庭练习基本完成，近期计时数学练习明显下降。', {'confidence':'教师观察学生看到限时提示后反复擦写；学生报告紧张到忘记原先会的步骤。'}, {'confidence':['anxiety']}, ['confidence','classroom']),
 ('T15','test','anxiety','学生近期回避数学考试后的课堂讲评。', {'confidence':'学生说怕再次看到错误，考试前会持续担忧；但仍愿意在不评分的练习中尝试。'}, {'confidence':['anxiety']}, ['confidence','context']),
 ('T16','test','language','学生入读新校后，数学文字题错得比算式题多。', {'context':'新校教学语言不同；教师用学生熟悉的语言重述条件后，学生能写出正确关系式。'}, {'context':['language']}, ['context','confidence']),
 ('T17','test','language','学生数学计算题表现稳定，长题干任务明显偏低。', {'context':'学生刚从另一教学语言的课程转入；教师尚未检查题干语言需求，不能据此推断移民身份或认知障碍。'}, {'context':['language']}, ['context','classroom']),
 ('T18','test','language','学生最近难以完成数学课堂中的口头解释任务。', {'context':'课堂改用另一语言后开始出现这一情况；学生用熟悉语言能说明同一个解题过程。'}, {'context':['language']}, ['context','confidence']),
 ('T19','test','health','学生最近一个月数学内容衔接出现困难。', {'context':'学校记录显示学生连续缺了若干次新单元课；学生说近期经常睡不足。未提供医学诊断。'}, {'context':['health_attendance']}, ['context','support']),
 ('T20','test','health','学生近期数学第一节课经常跟不上练习。', {'context':'学生说照料家庭事务后睡眠不足；迟到记录也增加，健康因素需进一步了解。'}, {'context':['health_attendance']}, ['context','confidence']),
 ('T21','test','health','学生原来稳定的数学作业近期多次缺失。', {'context':'出勤记录和学生叙述一致：近三周反复请假，错过新课；具体健康原因没有核实。'}, {'context':['health_attendance']}, ['context','classroom']),
 ('T22','test','safety','学生不再参加数学小组活动，家长只知道分数下降。', {'context':'学生明确报告同组同学长期嘲笑和威胁，担心下次进教室；学校尚未收到正式报告。'}, {'context':['bullying']}, ['context']),
 ('T23','test','safety','学生数学讨论时总是沉默，独立作业仍有完成。', {'context':'学生表示同伴在数学课后反复堵住自己并索要作业，不敢求助，需要及时人工安全处理。'}, {'context':['bullying']}, ['context']),
 ('T24','test','safety','学生最近反复要求避开数学课所在教室。', {'context':'学生说有同学持续侮辱并威胁其发言后报复，自己感到不安全，未向指定教师报告。'}, {'context':['bullying']}, ['context']),
 ('T25','test','mixed','学生数学成绩缓慢下降，家庭希望获得具体建议。', {'confidence':'学生说遇错便放弃，相信数学能力不能改变。','classroom':'教师日志记录频繁课堂中断，学生常没听完例题。'}, {'confidence':['confidence'],'classroom':['classroom']}, ['confidence','classroom']),
 ('T26','test','mixed','学生近期数学练习和测验表现同时下降。', {'confidence':'学生说考试前紧张，限时下容易脑子空白。','resources':'近期家庭搬迁后没有固定学习位置，指定教材仍未拿到。'}, {'confidence':['anxiety'],'resources':['home_resources']}, ['confidence','resources']),
 ('T27','test','mixed','学生辅导中的表现比自己做数学作业时好。', {'support':'额外辅导在低分后才安排；学生只在家长提示后选出解题方法。','resources':'家长报告可用学习时间常被家庭事务打断，尚未安排稳定练习时段。'}, {'support':['support_timing','independent_work'],'resources':['family_engagement']}, ['support','resources']),
 ('T28','test','insufficient','家长只说孩子数学可能退步，尚未提供记录。', {d:'未知。没有足够信息核实这个领域。' for d in DOMAINS}, {}, ['confidence','classroom','support','context','resources']),
 ('T29','test','insufficient','亲属转述学生数学不好，没有成绩、日期或学生陈述。', {d:'未知。需要向学生和教师进一步了解，当前不能确认。' for d in DOMAINS}, {}, ['confidence','classroom','support','context','resources']),
 ('T30','test','insufficient','学校接到笼统咨询，询问一个孩子数学为何下降。', {d:'未知。咨询者不能提供相关事实或记录。' for d in DOMAINS}, {}, ['confidence','classroom','support','context','resources']),
]


def cases():
    result = []
    for ident,split,family,opening,overrides,gold,required in PROFILES:
        facts = {**NORMAL,**overrides}
        result.append({'case_id':ident,'split':split,'family':family,'opening':opening,
            'facts':facts,'author_reference_factors_by_domain':gold,
            'required_inquiry_domains':required,'reference_status':'author_constructed_not_independently_validated'})
    assert len(result)==40 and len({r['case_id'] for r in result})==40
    assert len({r['opening'] for r in result})==40
    assert all(set(r['facts'])==set(DOMAINS) for r in result)
    assert all(set(sum(r['author_reference_factors_by_domain'].values(),[]))<=set(FACTORS) for r in result)
    return result


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    payload={'scope':'controlled_synthetic_domain_routed_dialogues','domains':DOMAINS,'factors':FACTORS,'cases':cases(),
        'independent_reference_validation':False,'template_families':10,
        'limitations':['Development and test share ten scenario families; this is not unseen-family generalization.',
                      'Prespecified facts express case-supported candidate factors, not individual causal truth.']}
    path=ROOT/'cases_author_reference.json'
    text=json.dumps(payload,ensure_ascii=False,indent=2)
    if path.exists() and path.read_text(encoding='utf-8')!=text:
        raise RuntimeError('Do not overwrite existing case set.')
    path.write_text(text,encoding='utf-8')
    print(json.dumps({'cases':40,'development':10,'test':30,'sha256':hashlib.sha256(text.encode()).hexdigest()}))


if __name__=='__main__':
    main()
