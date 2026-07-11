# 公文排版规范（.docx 输出专用）

来源：集团《关于规范行文格式的通知》（2020年4月22日）所附《行文规范性格式模板》，加上用户补充的表格规则。用户要求输出 Word 文档时，本文件优先于 docx 通用技能中的一般性建议（目标环境是 Microsoft Word 公文场景）。

## 一、输出前置步骤：字体保障

生成 .docx 之前先运行字体检测安装脚本：

```
powershell -ExecutionPolicy Bypass -File <技能目录>/scripts/ensure-fonts.ps1
```

- 逻辑：逐个检测 仿宋_GB2312、楷体_GB2312、方正小标宋简体 是否已安装（查 HKLM/HKCU 字体注册表，中英文族名都查）；已安装直接用；未安装从技能 `assets/fonts/` 复制做用户级安装（无需管理员权限）；assets 缺失时通过 `gh api` 从 GitHub 仓库下载后安装；
- 字体文件与族名对照：

| 文件（assets/fonts/） | 中文族名 | 英文族名 | 用途 |
| --- | --- | --- | --- |
| simfang.ttf | 仿宋_GB2312 | FangSong_GB2312 | 正文、三级标题、表格 |
| KaiTi_GB2312.ttf | 楷体_GB2312 | KaiTi_GB2312 | 二级标题、副标题 |
| FZXiaoBiaoSongJT.ttf | 方正小标宋简体 | FZXiaoBiaoSong-B05S | 主标题 |

- 黑体（一级标题）与宋体（页码）用 Windows 自带的 SimHei/SimSun，无需安装；
- 安装后新字体对已打开的 Word 进程不可见，提示用户重启 Word。

## 二、页面设置

| 项目 | 规范值 | OOXML/docx-js 取值 |
| --- | --- | --- |
| 纸张 | A4 | width 11906 / height 16838 (DXA) |
| 页边距 | 上3.7cm 下3.5cm 左2.8cm 右2.6cm | top 2098 / bottom 1985 / left 1588 / right 1474 |
| 页码 | 外侧、奇偶页不同，四号宋体，格式 -1- | evenAndOddHeaderAndFooters: true；奇数页页脚右对齐、偶数页左对齐；宋体 sz 28 |
| 正文对齐 | 两端对齐 | jc: both（docx-js: AlignmentType.JUSTIFIED） |

页边距和行间距可根据实际情况适当调整（规范原文允许），默认按上表执行。

## 三、字体层级（正文区）

字号换算：二号=22pt(sz44)、三号=16pt(sz32)、四号=14pt(sz28)、五号=10.5pt(sz21)。行距一律用固定值（lineRule: exact）：标题30磅(line 600)、正文28磅(line 560)。

| 元素 | 字体 | 字号 | 加粗 | 对齐/缩进 | 行距 |
| --- | --- | --- | --- | --- | --- |
| 主标题（章标题"三、主营业务分析"作报告章节时随主报告；独立成文时用此级） | 方正小标宋简体 | 二号 | 否 | 居中 | 固定值30磅 |
| 副标题/部门 | 楷体_GB2312 | 三号 | 否 | 居中 | 固定值28磅 |
| 一级标题（一、二、） | 黑体 | 三号 | **否**（规范明确不加粗） | 首行缩进2字符 | 固定值28磅 |
| 二级标题（（一）（二）） | 楷体_GB2312 | 三号 | **是** | 首行缩进2字符 | 固定值28磅 |
| 三级标题（1. 2.） | 仿宋_GB2312 | 三号 | **是** | 首行缩进2字符 | 固定值28磅 |
| 四级标题（（1）（2））及正文 | 仿宋_GB2312 | 三号 | 否 | 首行缩进2字符，两端对齐 | 固定值28磅 |
| 落款单位 | 仿宋_GB2312 | 三号 | 否 | 上空两行，右空4字 | 固定值28磅 |
| 落款日期 | 仿宋_GB2312 | 三号 | 否 | 与单位名居中对应 | 固定值28磅 |
| 页码 | 宋体 | 四号 | 否 | 外侧 | — |

本技能章节编号（三、→（一）→1.→（1））与上表标题层级一一对应：`三、`为章标题（并入立项报告时随主报告样式，通常黑体三号），`（一）`用二级标题样式（楷体_GB2312三号加粗），`1.`用三级标题样式（仿宋_GB2312三号加粗），`（1）`及正文用仿宋_GB2312三号。

## 四、表格规范（用户指定，硬性要求）

1. **表内文字一律 仿宋_GB2312、五号（sz21）**，含中文、数字、百分号；
2. **第一行（表头行）加粗**，其余行不加粗；表头行建议同时设置 `tblHeader`（跨页重复表头）；
3. **表格宽度根据窗口自动调整**：表格占满版心宽度并随页面缩放，OOXML 写法：

```xml
<w:tblPr>
  <w:tblW w:w="5000" w:type="pct"/>   <!-- 100% 版心宽度 -->
  <w:tblLayout w:type="autofit"/>      <!-- Word"根据窗口自动调整表格" -->
</w:tblPr>
```

docx-js 写法：

```javascript
new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  layout: TableLayoutType.AUTOFIT,
  rows: [...]
})
```

注：docx 通用技能建议表格用 DXA 定宽（兼容 Google Docs），公文场景以 Word 为目标，本条用户规则优先；

4. 表格框线：全框线单线；表头行可加浅灰底纹（`shd fill="D9D9D9" val="clear"`），无用户要求时默认不加底纹只加粗；
5. 单元格内容对齐：文字列左对齐或居中、数字列右对齐或居中，垂直居中（vAlign center）；
6. 表格上方保留一句引导语（正文样式），表格下方"单位：万元"及"注："用仿宋_GB2312五号，置于表格下一行；
7. 表内金额千分位、两位小数，与正文数据规则一致。

## 五、docx-js 实现要点

```javascript
// 字号(半磅)与行距(缇)常量
const HAO2 = 44, HAO3 = 32, HAO4 = 28, HAO5 = 21;
const LINE_TITLE = 600, LINE_BODY = 560;   // 固定值30磅/28磅

// 页面
sections: [{
  properties: {
    page: {
      size: { width: 11906, height: 16838 },                        // A4
      margin: { top: 2098, bottom: 1985, left: 1588, right: 1474 }  // 3.7/3.5/2.8/2.6cm
    },
    // 页码奇偶外侧需 evenAndOddHeaderAndFooters + 奇偶页脚分别右/左对齐
  },
  children: [ ... ]
}]

// 正文段
new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  indent: { firstLine: 640 },              // 三号字2字符 = 32pt = 640缇
  spacing: { line: LINE_BODY, lineRule: LineRuleType.EXACT },
  children: [new TextRun({ text: '……', font: { eastAsia: '仿宋_GB2312', ascii: 'Times New Roman' }, size: HAO3 })]
})

// 二级标题（一）
new Paragraph({
  indent: { firstLine: 640 },
  spacing: { line: LINE_BODY, lineRule: LineRuleType.EXACT },
  children: [new TextRun({ text: '（一）业务及产品概况', font: { eastAsia: '楷体_GB2312' }, size: HAO3, bold: true })]
})

// 表格单元格文字
new TextRun({ text: '……', font: { eastAsia: '仿宋_GB2312', ascii: '仿宋_GB2312' }, size: HAO5, bold: isHeaderRow })
```

- 中文字体必须写进 `eastAsia`；表内数字如需与中文同款，`ascii` 也设为仿宋_GB2312；
- 生成后用 docx 技能的 validate.py 校验。

## 六、标点与编号细则（规范原文）

1. 附件如有序号用阿拉伯数字（附件1.XXX），附件名称不加书名号，末尾不加标点；
2. 连续的书名号或引号中间不加标点符号（《A》《B》，"甲""乙"）；
3. 编号层级：一、→（一）→1.→（1）；"一、"后用顿号，"（一）"和"（1）"后不加标点，"1."用下脚点；
4. 成文日期用阿拉伯数字全写（2020年4月22日）。
