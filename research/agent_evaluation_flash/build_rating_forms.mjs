import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const out='C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs/grade_agent_flash_20261025';
const plan=JSON.parse(await fs.readFile('D:/pisa2022/outputs_grade_agent_flash_multiturn_v2/restricted_human_sample_plan.json','utf8'));
let packetIndex=[];
try {packetIndex=JSON.parse(await fs.readFile(`${out}/packet_index.json`,'utf8'));} catch(e) {if(e.code!=='ENOENT')throw e;}
const packetMap=new Map(packetIndex.map(p=>[p.report_id,p.status]));
await fs.mkdir(out,{recursive:true});

for (const rater of [1,2]) {
  const wb=Workbook.create();
  const scores=wb.worksheets.add('填写评分');
  const guide=wb.worksheets.add('评分说明');
  for (const s of [scores,guide]) {
    s.showGridLines=false;
    s.getRange('A1:J45').format.font={name:'Microsoft YaHei',size:10,color:'#253246'};
    s.getRange('A1:J45').format.verticalAlignment='center';
    s.getRange('A1:A45').format.columnWidth=3;
  }
  scores.getRange('B2').values=[[`智能体报告简化评分｜评分者${rater}`]];
  scores.getRange('B2').format.font={name:'Microsoft YaHei',size:15,bold:true};
  scores.getRange('B3').values=[['每份报告只填三项0、1或2分；有明显问题时再写一句说明。']];
  scores.getRange('B4').values=[[packetIndex.length?'请对照匿名报告材料独立评分；空白不是0分，生成失败的报告不评分。':'配套报告尚未生成；请保留空白，不用0代替未评分。请独立评分。']];
  scores.getRange('B5').values=[['已完成份数']];
  scores.getRange('C5').formulas=[['=COUNTIFS(G9:G38,"已完成")']];
  scores.getRange('E5:F5').values=[['计划份数',30]];
  scores.getRange('E6').values=[['可评分份数']];
  scores.getRange('F6').formulas=[['=COUNTIFS(C9:C38,"已配套")']];
  scores.getRange('B8:H8').values=[['报告编号','配套材料','因素合理性','建议适用性','不确定处理','填写状态','问题说明（选填）']];
  const values=plan.slots.map(r=>[r.report_id,packetMap.has(r.report_id)?(packetMap.get(r.report_id)==='completed'?'已配套':'生成失败'):'待生成',null,null,null,null,null]);
  scores.getRange('B9:H38').values=values;
  const formulas=[];
  for(let r=9;r<=38;r++) {
    formulas.push([`=IF(C${r}="生成失败","无报告，不评分",IF(COUNT(D${r}:F${r})=3,IF(AND(MIN(D${r}:F${r})>=0,MAX(D${r}:F${r})<=2,D${r}=INT(D${r}),E${r}=INT(E${r}),F${r}=INT(F${r})),"已完成","请填0、1或2"),"待评分"))`]);
  }
  scores.getRange('G9:G38').formulas=formulas;
  scores.getRange('D9:F38').format.fill='#FFF3D5';
  scores.getRange('D9:F38').format.numberFormat='0';
  scores.dataValidations.add({range:'D9:F38',rule:{type:'whole',operator:'between',formula1:0,formula2:2}});
  scores.getRange('B8:H8').format={fill:'#253E5C',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center',wrapText:true};
  scores.getRange('B9:H38').format.rowHeight=27;
  scores.getRange('B8:B38').format.columnWidth=13;
  scores.getRange('C8:C38').format.columnWidth=12;
  scores.getRange('D8:F38').format.columnWidth=15;
  scores.getRange('G8:G38').format.columnWidth=18;
  scores.getRange('H8:H38').format.columnWidth=34;
  scores.getRange('D9:F38').format.horizontalAlignment='center';
  scores.getRange('H9:H38').format.wrapText=true;
  scores.freezePanes.freezeRows(8);

  guide.getRange('B2').values=[['三个维度，每项0—2分']];
  guide.getRange('B2').format.font={name:'Microsoft YaHei',size:15,bold:true};
  guide.getRange('B4:E7').values=[
    ['维度','0分','1分','2分'],
    ['因素合理性','明显误判，或编造重要因素。','部分合理，但有遗漏或依据不足。','主要判断有案例依据，未明显遗漏关键因素。'],
    ['建议适用性','不相关、不适当或无法执行。','基本相关，但比较笼统。','针对案例，下一步清楚、可行。'],
    ['不确定处理','信息不足仍断言，或声称已经确定原因。','注意到不确定性，但处理不充分。','指出缺失信息，合理追问或保留判断。']];
  guide.getRange('B4:E4').format={fill:'#253E5C',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:28};
  guide.getRange('B5:E7').format.wrapText=true;
  guide.getRange('B5:E7').format.rowHeight=65;
  guide.getRange('B4:B12').format.columnWidth=22;
  guide.getRange('C4:E12').format.columnWidth=35;
  guide.getRange('B9').values=[['空白代表未评分；0分代表明确判为最低档。各维度分别分析，不设置任意加权总分。']];
  guide.getRange('B10').values=[['依据']];
  guide.getRange('C10').values=[['https://aclanthology.org/2025.naacl-long.57/']];
  guide.getRange('B11').values=[['文献中的指导与可执行性维度，以及本研究任务适配；不是已经验证的标准量表。']];
  guide.getRange('B12').values=[['材料只提供匿名报告编号，不提供系统名称。请勿与另一评分者讨论后再填写。']];

  // Verify blank, partial, zero and invalid scores without retaining test ratings.
  wb.recalculate();
  if(scores.getRange('C5').values[0][0]!==0) throw Error('Blank forms count as completed');
  scores.getRange('D9').values=[[0]]; wb.recalculate();
  if(scores.getRange('C5').values[0][0]!==0) throw Error('Partial row count incorrect');
  scores.getRange('D9:F9').values=[[0,0,0]]; wb.recalculate();
  if(scores.getRange('C5').values[0][0]!==1) throw Error('Valid zero scores lost');
  scores.getRange('D9:F9').values=[[3,1,1]]; wb.recalculate();
  if(scores.getRange('C5').values[0][0]!==0) throw Error('Invalid scores counted');
  scores.getRange('D9:F9').clear({applyTo:'contents'}); wb.recalculate();
  const inspect=await wb.inspect({kind:'table',range:'填写评分!B8:H12',include:'values,formulas',tableMaxRows:5,tableMaxCols:7});
  console.log(inspect.ndjson);
  const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},summary:'formula errors'});
  console.log(errors.ndjson);
  for(const [name,range] of [['填写评分','B2:H16'],['评分说明','B2:E12']]) {
    if(name==='评分说明' && packetIndex.length)continue;
    const preview=await wb.render({sheetName:name,range,scale:1.5,format:'png'});
    await fs.writeFile(`${out}/rater_${rater}_${name}.png`,new Uint8Array(await preview.arrayBuffer()));
  }
  const file=await SpreadsheetFile.exportXlsx(wb);
  await file.save(`${out}/简化评分表_评分者${rater}.xlsx`);
}
console.log(`Two independent blank rating workbooks exported. Packet rows: ${packetIndex.length}.`);
