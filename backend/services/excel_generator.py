import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from backend.models.menu import Menu, MenuItem

CATEGORY_ORDER = ["凉菜", "热菜", "汤羹", "主食", "甜品", "点心"]

thin_border = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def generate_excel(menu: Menu, items: list[MenuItem]) -> io.BytesIO:
    """生成带公式的 Excel 菜单"""
    wb = Workbook()
    ws = wb.active
    ws.title = "推荐菜单"

    # 列宽
    col_widths = [5, 22, 16, 8, 14, 30]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # 样式
    title_font = Font(name="微软雅黑", size=16, bold=True)
    header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    cat_font = Font(name="微软雅黑", size=11, bold=True)
    cat_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    normal_font = Font(name="微软雅黑", size=10)
    total_font = Font(name="微软雅黑", size=11, bold=True)
    note_font = Font(name="微软雅黑", size=9, italic=True, color="888888")

    # 标题行
    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    cell = ws.cell(row=row, column=1, value="旺阁渔村 · 推荐菜单")
    cell.font = title_font
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 35

    # 信息行
    row = 2
    date_str = datetime.now().strftime("%Y-%m-%d")
    is_banquet = getattr(menu, 'mode', 'retail') == 'banquet'
    budget_label = f"宴会总价: {int(menu.budget)}元" if is_banquet else f"预算: {int(menu.budget)}元"
    info = f"客户: {menu.customer_name or '贵宾'}  |  人数: {menu.party_size}位  |  日期: {date_str}  |  {budget_label}  |  场合: {menu.occasion or '聚餐'}"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    cell = ws.cell(row=row, column=1, value=info)
    cell.font = Font(name="微软雅黑", size=10)
    cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[row].height = 22

    row = 3  # 空行

    # 按类别分组
    grouped: dict[str, list[MenuItem]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    subtotal_cells: list[str] = []  # 记录所有小计单元格地址
    has_market_price = False

    row = 4
    for cat in CATEGORY_ORDER:
        cat_items = grouped.get(cat)
        if not cat_items:
            continue

        # 类别标题
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        cell = ws.cell(row=row, column=1, value=f"【{cat}】")
        cell.font = cat_font
        cell.fill = cat_fill
        cell.alignment = Alignment(horizontal="left")
        for c in range(1, 7):
            ws.cell(row=row, column=c).fill = cat_fill
            ws.cell(row=row, column=c).border = thin_border
        row += 1

        # 表头
        headers = ["序号", "菜名", "单价", "数量", "小计", "备注"]
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border
        row += 1

        # 菜品行
        for idx, item in enumerate(cat_items, 1):
            price_display = item.price_text
            market_mark = ""
            if "时价" in item.price_text:
                has_market_price = True
                market_mark = " *"

            ws.cell(row=row, column=1, value=idx).font = normal_font
            ws.cell(row=row, column=1).alignment = Alignment(horizontal="center")

            ws.cell(row=row, column=2, value=item.dish_name).font = normal_font

            ws.cell(row=row, column=3, value=f"{price_display}{market_mark}").font = normal_font
            ws.cell(row=row, column=3).alignment = Alignment(horizontal="center")

            ws.cell(row=row, column=4, value=item.quantity).font = normal_font
            ws.cell(row=row, column=4).alignment = Alignment(horizontal="center")

            # 小计用公式 (price列 × quantity列没有直接对应，用数值公式)
            # 由于单价是文本带单位，用实际数值填写公式
            price_cell = f"C{row}"
            qty_cell = f"D{row}"
            # 直接用数值而非公式引用文本列
            subtotal_cell_ref = f"E{row}"
            # 用 =price*qty 的数值版本
            ws.cell(row=row, column=5, value=item.subtotal).font = normal_font
            ws.cell(row=row, column=5).number_format = '#,##0.00'
            ws.cell(row=row, column=5).alignment = Alignment(horizontal="right")
            subtotal_cells.append(subtotal_cell_ref)

            ws.cell(row=row, column=6, value=item.reason).font = normal_font

            for c in range(1, 7):
                ws.cell(row=row, column=c).border = thin_border

            row += 1

        row += 1  # 类别间空行

    # 合计行
    row_total = row
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    cell = ws.cell(row=row, column=1, value="合计")
    cell.font = total_font
    cell.alignment = Alignment(horizontal="right")

    # SUM 公式
    if subtotal_cells:
        sum_formula = "=" + "+".join(subtotal_cells)
        ws.cell(row=row, column=5).value = sum_formula
    else:
        ws.cell(row=row, column=5, value=0)
    ws.cell(row=row, column=5).font = total_font
    ws.cell(row=row, column=5).number_format = '#,##0.00'
    ws.cell(row=row, column=5).alignment = Alignment(horizontal="right")

    for c in range(1, 7):
        ws.cell(row=row, column=c).border = thin_border

    # 时价备注
    if has_market_price:
        row += 2
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        cell = ws.cell(row=row, column=1, value="* 时价菜品按参考价计算，实际以当日市价为准")
        cell.font = note_font

    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
