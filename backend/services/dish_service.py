import csv
import re
import hashlib
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.config import CSV_PATH


def _extract_serving_unit(price_text: str) -> str:
    match = re.search(r"元/([^\s/]+)", price_text)
    return match.group(1).strip() if match else ""


def parse_price(price_str: str) -> tuple[str, float, bool, str]:
    """解析价格字符串 → (price_text, price, is_market_price, serving_unit)"""
    if not price_str or price_str.strip() == "":
        return "", 0.0, False, ""

    price_str = price_str.strip()

    if price_str == "时价" or price_str.startswith("时价"):
        # 时价(参考180元)/例 or 时价
        ref_match = re.search(r"参考(\d+\.?\d*)", price_str)
        ref_price = float(ref_match.group(1)) if ref_match else 0.0
        price_text = price_str if "参考" in price_str else f"时价(参考0元)/例"
        return price_text, ref_price, True, _extract_serving_unit(price_text)

    # 标准价格: 99元/例、53元/只、13.9元/件
    match = re.match(r"^(\d+\.?\d*)元/(.+)$", price_str)
    if match:
        serving_unit = match.group(2).strip()
        return price_str, float(match.group(1)), False, serving_unit

    # 尝试直接提取数字
    num_match = re.search(r"(\d+\.?\d*)", price_str)
    if num_match:
        return price_str, float(num_match.group(1)), False, _extract_serving_unit(price_str)

    return price_str, 0.0, False, _extract_serving_unit(price_str)


def infer_category(name: str, cooking_method: str, scene: str) -> str:
    """根据菜名、烹饪方式、场景推断分类"""
    cooking_method = cooking_method or ""
    scene = scene or ""
    name = name or ""

    # 凉菜
    if cooking_method in ("凉拌", "腌制", "冷盘") or "前菜" in scene:
        return "凉菜"

    # 汤羹
    if "羹" in name or cooking_method in ("煮/羹",):
        return "汤羹"

    # 主食
    staple_keywords = ["炒饭", "米粉", "河", "伊面", "粉丝", "飞饼", "炒面"]
    if any(kw in name for kw in staple_keywords):
        return "主食"

    # 甜品
    dessert_keywords = ["双皮奶", "糕", "酸奶", "官燕", "杨枝甘露"]
    if any(kw in name for kw in dessert_keywords):
        return "甜品"

    # 点心
    dim_sum_keywords = ["包", "酥", "饼", "饺"]
    if any(kw in name for kw in dim_sum_keywords):
        return "点心"

    # 默认热菜
    return "热菜"


def build_tags(row: dict) -> str:
    """合并标签: 食材分类|口味|烹饪方式|场景"""
    parts = []
    for field in ["食材分类", "口味标签", "烹饪方式", "场景推荐"]:
        val = row.get(field, "").strip()
        if val:
            parts.append(val)
    return "|".join(parts)


def import_dishes_from_csv(session: Session) -> int:
    """从 CSV 导入菜品数据，返回导入数量"""
    # 如果已有数据则跳过
    existing = session.exec(select(Dish)).first()
    if existing:
        return 0

    count = 0
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("菜品名称", "").strip()
            price_raw = row.get("价格", "").strip()
            tag_col = row.get("标签", "").strip()

            # 跳过空行
            if not name:
                continue

            # 跳过宴席菜（无价格且标签为宴席）
            if tag_col == "宴席" or (not price_raw and "宴席" in row.get("待确认", "")):
                continue

            # 跳过没有价格的菜品
            if not price_raw:
                continue

            price_text, price, is_market_price, serving_unit = parse_price(price_raw)

            cooking_method = row.get("烹饪方式", "").strip()
            scene = row.get("场景推荐", "").strip()
            category = infer_category(name, cooking_method, scene)

            tags = build_tags(row)

            # 成本按品类基准 + 菜品名哈希微调，模拟真实差异
            base_cost_ratio = {
                "凉菜": 0.28,   # 毛利高，~72%
                "热菜": 0.38,   # 中等，~62%
                "汤羹": 0.30,   # 汤水成本低，~70%
                "主食": 0.25,   # 毛利最高，~75%
                "甜品": 0.32,   # ~68%
                "点心": 0.30,   # ~70%
            }
            ratio = base_cost_ratio.get(category, 0.35)
            # 用菜名哈希生成 ±0.08 的浮动，让每道菜不一样
            name_hash = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
            jitter = ((name_hash % 160) - 80) / 1000  # -0.08 ~ +0.08
            cost = round(price * max(0.15, min(0.55, ratio + jitter)), 2)

            dish = Dish(
                name=name,
                price_text=price_text,
                price=price,
                is_market_price=is_market_price,
                cost=cost,
                category=category,
                tags=tags,
                is_active=True,
                serving_unit=serving_unit,
                serving_split=0,
            )
            session.add(dish)
            count += 1

    session.commit()
    return count


def get_all_active_dishes(session: Session) -> list[Dish]:
    """获取所有启用的菜品"""
    return list(session.exec(select(Dish).where(Dish.is_active == True)).all())


def get_dishes_by_category(session: Session) -> dict[str, list[Dish]]:
    """按类别分组获取菜品"""
    dishes = get_all_active_dishes(session)
    grouped: dict[str, list[Dish]] = {}
    for dish in dishes:
        grouped.setdefault(dish.category, []).append(dish)
    return grouped
