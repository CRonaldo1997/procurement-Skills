# -*- coding: utf-8 -*-
"""
替换采购文件模板中的占位符
支持被HTML标签、空白、HTML实体分割的【此处填充xxx】格式占位符

核心机制：
1. 将占位符文本的每个字符之间插入分隔符模式，允许HTML标签/空白/HTML实体
2. 使用非贪婪匹配避免回溯问题
3. 替换前后双重验证，确保无遗漏

用法:
    python scripts/generate_procurement_doc.py [--output <输出路径>]

    占位符替换规则通过 REPLACEMENTS 字典配置。
    模板文件路径相对于 Skill 根目录自动解析。
"""

import re
import sys
from pathlib import Path

# ==================== 路径配置 ====================
# 脚本所在目录的父目录即为 Skill 根目录
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# 模板文件路径（相对于 Skill 根目录）
TEMPLATE_FILE = SKILL_DIR / 'assets' / '20w以下项目采购文件模板.html'
# ==================== 路径配置结束 ====================

# ==================== 占位符替换规则 ====================
# 键必须是模板中【】内的完整文本（去除HTML标签后的纯文本）
# 注意：占位符必须包含完整的【】括号
REPLACEMENTS = {
    '【此处填充项目名称】': '中再寿险体检报告智能解析系统',
    '【此处填充当前年月，例如：2026年5月】': '2026年5月',
    '【此处填充报价时间deadline，需年月日和具体几点，例如：2026年5月9日17时】': '2026年5月25日17时',
    '【此处填充联系人名，需询问用户】': '江东',
    '【此处填充项目人座机号，需询问用户】': '010-83361234',
    '【此处填充联系人手机号，需询问用户】': '18524967815',
    '【此处填充项目背景交待，可分为2~3个小段落】': (
        '随着公司业务的不断发展和员工规模的持续扩大，员工健康管理已成为企业人力资源管理的重要组成部分。'
        '目前公司每年组织全体员工进行健康体检，但体检报告的分析和管理仍主要依赖人工方式，存在效率低、成本高、'
        '难以进行长期健康趋势跟踪等问题。大量体检数据未能得到有效挖掘和利用，无法为公司制定健康管理政策提供数据支撑。\n\n'
        '为提升员工健康管理水平，降低人工分析成本，实现体检数据的智能化管理，大数据服务部拟建设体检报告智能分析系统。'
        '该系统将利用OCR识别、自然语言处理和AI分析等技术，实现体检报告的自动识别、结构化解析、智能分析和可视化管理，'
        '为公司员工提供更加精准、高效的健康服务。'
    ),
    '【此处填充需求1标题】': '体检报告OCR识别与结构化解析',
    '【此处填充需求1展开说明】': (
        '系统需支持多种格式体检报告的自动识别与结构化解析。具体要求包括：'
        '（1）支持纸质体检报告扫描件（PDF、JPG、PNG等格式）的OCR文字识别，识别准确率不低于95%；'
        '（2）支持电子版体检报告（PDF、Excel等格式）的数据提取；'
        '（3）能够自动识别并提取体检报告中的各项指标数据，包括但不限于血常规、尿常规、生化指标、影像学检查结果等；'
        '（4）支持多家主流体检机构（如美年大健康、爱康国宾、慈铭体检等）的报告模板适配；'
        '（5）具备自学习能力，能够通过样本训练不断提升识别准确率。'
    ),
    '【此处填充需求2标题】': '健康指标智能分析与风险评估',
    '【此处填充需求2展开说明】': (
        '系统需基于AI模型对体检数据进行深度分析和健康风险评估。具体要求包括：'
        '（1）建立健康指标参考值数据库，支持按性别、年龄段等维度进行差异化对比分析；'
        '（2）自动识别异常指标并进行分级预警（轻度异常、中度异常、重度异常），生成相应的健康建议；'
        '（3）支持历史体检数据对比分析，生成个人健康趋势报告，直观展示各项指标的变化趋势；'
        '（4）基于大数据分析模型，对员工群体进行健康风险画像，为公司制定健康管理政策提供数据支撑；'
        '（5）支持自定义分析规则和预警阈值，满足不同部门的个性化管理需求。'
    ),
}
# ==================== 占位符替换规则结束 ====================

# 默认输出文件名（可通过命令行参数覆盖）
DEFAULT_OUTPUT_NAME = '中再寿险体检报告智能解析系统-采购文件.html'


# HTML分隔符模式：匹配HTML标签、空白字符、HTML实体
# 使用非贪婪 *? 避免长文本回溯
_HTML_SEP = r'(?:<[^>]*?>|\s|&[^;]+;)*?'


def build_placeholder_pattern(placeholder_text: str) -> str:
    """
    构建匹配被HTML分割的占位符的正则表达式。

    原理：将占位符文本的每个字符之间插入分隔符模式，
    允许HTML标签（如<font>）、空白（空格/换行）、HTML实体（如&nbsp;）插入其中。

    示例::

        输入: "【此处填充项目名称】"
        输出: "【(?:<[^>]*?>|\\s|&[^;]+;)*?此(?:<[^>]*?>|\\s|&[^;]+;)*?处..."

    Args:
        placeholder_text: 占位符的纯文本（包含【】括号）

    Returns:
        正则表达式字符串
    """
    # 对每个字符转义后，用分隔符连接
    escaped_chars = [re.escape(ch) for ch in placeholder_text]
    return _HTML_SEP.join(escaped_chars)


def strip_html_tags(text: str) -> str:
    """去除HTML标签、HTML实体和空白，提取纯文本"""
    return re.sub(r'<[^>]*?>|&[^;]+;|\s', '', text)


def replace_all_placeholders(content: str, replacements: dict) -> tuple[str, list[str]]:
    """
    替换所有占位符。

    Args:
        content: HTML内容
        replacements: 占位符->替换内容的映射

    Returns:
        (替换后的内容, 未匹配的占位符列表)
    """
    unmatched = []

    for placeholder, replacement in replacements.items():
        pattern = build_placeholder_pattern(placeholder)
        new_content, count = re.subn(pattern, replacement, content)

        if count == 0:
            unmatched.append(placeholder)
            print(f'  [WARN] 未找到占位符: {placeholder}')
        else:
            content = new_content
            print(f'  [OK] 已替换: {placeholder} (共{count}处)')

    return content, unmatched


def find_all_fill_placeholders(content: str) -> list[str]:
    """
    扫描内容中所有【此处填充...】模式的占位符。
    只匹配以"此处填充"开头的占位符，排除模板固定文本（如【供应商】）。

    Returns:
        去重后的纯文本占位符列表（已排序）
    """
    # 构建匹配【此处填充...】的模式
    pattern = (
        r'【' + _HTML_SEP +
        r'此' + _HTML_SEP + r'处' + _HTML_SEP +
        r'填' + _HTML_SEP + r'充' + _HTML_SEP +
        r'[^】]+' + _HTML_SEP +
        r'】'
    )

    found = set()
    for match in re.finditer(pattern, content):
        text = strip_html_tags(match.group())
        found.add(text)

    return sorted(found)


def verify_replacements(content: str, replacements: dict) -> tuple[list[str], list[str]]:
    """
    验证替换结果。

    Returns:
        (已知占位符残留列表, 未知占位符列表)
    """
    # 1. 检查已知占位符是否还有残留
    known_remaining = []
    for placeholder in replacements.keys():
        pattern = build_placeholder_pattern(placeholder)
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                text = strip_html_tags(match)
                known_remaining.append(text)

    # 2. 检查是否有未知的【此处填充...】占位符
    all_fill_placeholders = find_all_fill_placeholders(content)
    known_keys = set(replacements.keys())
    unknown_remaining = [p for p in all_fill_placeholders if p not in known_keys]

    return known_remaining, unknown_remaining


def main():
    # 解析命令行参数
    output_name = DEFAULT_OUTPUT_NAME
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--output' and i < len(sys.argv) - 1:
            output_name = sys.argv[i + 1]

    output_file = Path(output_name)

    print('=' * 60)
    print('采购文件占位符替换工具')
    print('=' * 60)
    print()

    # 1. 检查模板文件
    if not TEMPLATE_FILE.exists():
        print(f'[ERROR] 模板文件不存在: {TEMPLATE_FILE}')
        print(f'Skill 目录: {SKILL_DIR}')
        print('请检查模板文件是否存在。')
        sys.exit(1)

    # 2. 读取模板
    try:
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f'[ERROR] 读取模板文件失败: {e}')
        sys.exit(1)

    if not content.strip():
        print('[ERROR] 模板文件为空')
        sys.exit(1)

    print(f'模板文件: {TEMPLATE_FILE}')
    print(f'文件大小: {len(content):,} 字符')
    print(f'已配置 {len(REPLACEMENTS)} 个占位符替换规则')
    print()

    # 3. 替换前：扫描模板中的所有占位符
    print('--- 替换前 ---')
    before_placeholders = find_all_fill_placeholders(content)
    print(f'发现 {len(before_placeholders)} 种【此处填充...】占位符:')
    for p in before_placeholders:
        print(f'  - {p}')
    print()

    # 4. 执行替换
    print('--- 执行替换 ---')
    content, unmatched = replace_all_placeholders(content, REPLACEMENTS)
    print()

    # 5. 验证
    print('--- 验证结果 ---')
    known_remaining, unknown_remaining = verify_replacements(content, REPLACEMENTS)

    has_errors = False

    if known_remaining:
        has_errors = True
        print(f'[WARN] 以下已知占位符仍有残留 ({len(known_remaining)} 处):')
        for r in known_remaining:
            print(f'  - {r}')

    if unknown_remaining:
        has_errors = True
        print(f'[WARN] 发现 {len(unknown_remaining)} 个未知占位符（未在REPLACEMENTS中配置）:')
        for r in unknown_remaining:
            print(f'  - {r}')

    if not known_remaining and not unknown_remaining:
        print('[OK] 所有【此处填充...】占位符均已替换，无残留')

    # 6. 输出文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'\n[OK] 采购文件已生成: {output_file.resolve()}')
        print(f'输出文件大小: {len(content):,} 字符')
    except Exception as e:
        print(f'[ERROR] 写入输出文件失败: {e}')
        sys.exit(1)

    # 7. 退出状态
    if has_errors or unmatched:
        print('\n[WARN] 替换过程存在警告，请检查上述信息')
        sys.exit(1)
    else:
        print('\n[OK] 替换完成，无错误')
        sys.exit(0)


if __name__ == '__main__':
    main()
