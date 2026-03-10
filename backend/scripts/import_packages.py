from __future__ import annotations

from sqlmodel import SQLModel, Session, select

from backend.database import engine
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec  # noqa: F401
from backend.models.menu import Menu, MenuItem  # noqa: F401
from backend.models.package import Package, PackageGroup, PackageItem
from backend.models.user import User  # noqa: F401
from backend.services.dish_service import get_category_cost_ratio

PACKAGE_GROUPS = [
    {
        "name": "婚宴套餐",
        "sort_order": 100,
        "packages": [
            {
                "name": "良辰美景宴",
                "price": 1888,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运烧卤大拼盆",
                    "大红灼游水生虾",
                    "家乡炒双脆",
                    "花胶海参拆鱼羹",
                    "金牌蒜香T骨",
                    "旺阁第一鸡",
                    "金银蒜粉丝蒸带子",
                    "清蒸深海青斑",
                    "鲍汁红腰豆花胶肚",
                    "鸡汤浸时蔬",
                    "五谷杂粮炒饭",
                    "顺德伦教糕",
                    "岭南佳果",
                ],
            },
            {
                "name": "金玉满堂宴",
                "price": 2688,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运烧鹅大拼盘",
                    "大红灼生猛九节虾",
                    "XO酱荷塘花枝双脆",
                    "花旗参炖老鸽",
                    "秘制烤羊排",
                    "鲍汁花胶肚扣鹅掌",
                    "当红一品吊烧鸡",
                    "蒜茸粉丝蒸元贝",
                    "清蒸大海斑",
                    "上汤浸时蔬",
                    "富贵炒饭",
                    "点心三喜拼",
                    "岭南佳果",
                ],
            },
            {
                "name": "天赐良缘宴",
                "price": 3988,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运均安烧中猪",
                    "芝士伊面焗波士顿龙虾",
                    "XO酱碧绿游龙吊片",
                    "原盅土鸡炖花胶肚",
                    "脆皮鱼饼拼京都骨",
                    "招牌葱油清远鸡",
                    "鲍汁花菇扣海参",
                    "金银蒜蒸大元贝",
                    "清蒸沙巴大海斑",
                    "鸡汤浸时蔬",
                    "金银炒饭",
                    "百年鸿运",
                    "点心四喜拼",
                    "岭南佳果",
                ],
            },
            {
                "name": "龙凤呈祥宴",
                "price": 5988,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运有米金猪全体",
                    "芝士伊面焗龙虾",
                    "金巢美果海皇带子丁",
                    "山珍螺头炖花胶肚",
                    "报喜当红炸子鸡",
                    "黄金百花球",
                    "宝贝鲍汁扣澳洲海参",
                    "金银蒜蒸大连青边鲍",
                    "清蒸深海珍珠斑",
                    "鸡汁浸时蔬",
                    "甜甜蜜蜜",
                    "幸福美点双辉",
                    "吉祥佳果",
                ],
            },
            {
                "name": "百年好合宴",
                "price": 6988,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运乳猪全体",
                    "高汤芝士焗龙虾",
                    "碧绿花枝虾球",
                    "鲍参翅肚羹",
                    "山珍卷拼黄金条",
                    "当红三宝鸽",
                    "鲍汁花胶筒拼澳洲参",
                    "陈皮蒸原只五头南非鲜鲍",
                    "清蒸深海老虎斑",
                    "高汤云腿浸时蔬",
                    "幸福美满炒饭",
                    "连生贵子",
                    "佳偶甜美点",
                    "呈祥生果盆",
                ],
            },
            {
                "name": "佳偶天成宴",
                "price": 7988,
                "dishes": [
                    "凉菜四小碟",
                    "报喜鸿运乳猪全体",
                    "金汤芝士焗龙虾(伊面底)",
                    "如意翡翠桂花蚌带子",
                    "火瞳土鸡炖鲍翅",
                    "富贵百花让蟹钳",
                    "当红脆皮鸡",
                    "蟹黄扒酿羊肚菌",
                    "鲍汁花菇扣三头南非鲜鲍",
                    "清蒸东星斑",
                    "金华浸时蔬",
                    "金瑶蛋白炒饭",
                    "珍珠双皮奶",
                    "佳偶甜美点",
                    "岭南佳果",
                ],
            },
            {
                "name": "珠联璧合宴",
                "price": 8988,
                "dishes": [
                    "凉菜四小碟",
                    "鸿运乳猪全体",
                    "法式芝士焗龙虾",
                    "爱巢碧绿澳参玉带",
                    "花胶筒老鸡炖鲍翅",
                    "星光灿烂百花酿蟹钳",
                    "当红脆皮三宝鸽",
                    "发财多子花菇瑶柱脯",
                    "鲍汁鹅掌扣南非吉品鲍",
                    "清蒸大红东星斑",
                    "竹笙浸时蔬",
                    "健康山珍炒饭",
                    "燕窝双皮奶",
                    "豪华点心拼盆",
                    "岭南佳果",
                ],
            },
            {
                "name": "幸福美满宴",
                "price": 14888,
                "dishes": [
                    "凉菜四小碟",
                    "金牌鲜果菠萝猪",
                    "至尊青龙炒鲜奶",
                    "松露野菌明虾球",
                    "红烧大鲍翅",
                    "避风塘鹅肝拼三葱和牛粒",
                    "经典金华玉树鸡",
                    "蚝皇花菇扣八头南非吉品鲍",
                    "五谷丰登烩花胶筒",
                    "清蒸进口大红东星斑",
                    "金瑶扇影蔬",
                    "健康山珍炒饭",
                    "冰花炖官燕",
                    "豪华点心拼盘",
                    "环球生果拼盘",
                ],
            },
        ],
    },
    {
        "name": "团年套餐",
        "sort_order": 200,
        "packages": [
            {
                "name": "财运亨通宴",
                "price": 1688,
                "dishes": [
                    "鸿运烧卤拼盘",
                    "鲜花椒焗海明虾",
                    "XO酱尖椒藕带炒牛肉",
                    "渔村三鲜海皇汤",
                    "旺阁当红炸子鸡",
                    "脆云吞拼果咕噜肉",
                    "虎皮尖椒红烧肉",
                    "重庆啤酒鸭",
                    "蒜蓉胜瓜蒸大连鲍",
                    "豉汁蒸红鲷鱼",
                    "鸡汤浸时蔬",
                    "扬州炒饭",
                    "三色糕拼盘",
                    "岭南佳果",
                ],
            },
            {
                "name": "金银满堂宴",
                "price": 1988,
                "dishes": [
                    "鸿运烧鹅大拼盘",
                    "避风塘游水生虾",
                    "发财年年好就手",
                    "客家猪肉菌汤",
                    "旺阁第一鸡",
                    "脆皮鱼饼鲜果咕肉",
                    "客家香芋扣肉",
                    "蒜蓉粉丝蒸元贝",
                    "清蒸深海大海斑",
                    "香辣山城毛血旺",
                    "鸡汤浸时蔬",
                    "锦绣炒饭",
                    "健康燕麦包",
                    "岭南佳果",
                ],
            },
            {
                "name": "花开富贵宴",
                "price": 2288,
                "dishes": [
                    "鸿运烧味四喜拼",
                    "大红灼游水生虾",
                    "发财大财好就手",
                    "西洋菜炖生鱼",
                    "当红一品炸子鸡",
                    "金牌蒜香骨",
                    "年年大丰收",
                    "秘制烤羊排",
                    "石盘蒜香焗带子",
                    "鲜花椒蒸大海斑",
                    "上汤浸时蔬",
                    "金银炒饭",
                    "步步高升",
                    "岭南佳果",
                ],
            },
            {
                "name": "前程锦绣宴",
                "price": 2688,
                "dishes": [
                    "旺阁至尊烧鹅",
                    "大红灼海明虾",
                    "发财好市就手",
                    "养生虫草花炖鸭",
                    "招牌当红三喜鸽",
                    "古法扣羊腩煲",
                    "石盘蒜香焗生蚝",
                    "香橙骨拼脆皮鱼饼",
                    "野山椒焖娃娃牛肉",
                    "清蒸深海珍珠斑",
                    "鱼滑浸时蔬",
                    "飘香糯米腊味饭",
                    "点心拼盘",
                    "岭南佳果",
                ],
            },
            {
                "name": "大展鸿图宴",
                "price": 3988,
                "dishes": [
                    "鸿运发财有米金猪",
                    "芝士伊面焗波士顿龙虾",
                    "发财好市大大利",
                    "原盅土鸡炖花胶肚",
                    "葱油乡下大阉鸡",
                    "成吉思汗烤羊排",
                    "荷芹炒生晒腊味",
                    "鲍汁花菇扣海参",
                    "金蒜银丝蒸凤鲜鲍",
                    "特色蒸大海斑",
                    "花菇扒生菜",
                    "红豆沙汤丸",
                    "美点双辉",
                    "岭南佳果",
                ],
            },
        ],
    },
]


def infer_category(name: str) -> str:
    if "凉菜" in name or "四小碟" in name:
        return "凉菜"
    if "炒饭" in name or "腊味饭" in name:
        return "主食"
    if "点心" in name or "美点" in name or "燕麦包" in name:
        return "点心"
    if (
        "双皮奶" in name
        or "官燕" in name
        or "佳果" in name
        or "生果" in name
        or "汤丸" in name
        or "甜" in name
        or "糕" in name
    ):
        return "甜品"
    if "炖" in name or "汤" in name or "羹" in name:
        return "汤羹"
    return "热菜"


def find_or_create_dish(session: Session, name: str) -> Dish:
    dish = session.exec(select(Dish).where(Dish.name == name)).first()
    if dish:
        return dish

    category = infer_category(name)
    cost_ratio = get_category_cost_ratio(category)
    price = 0.0

    dish = Dish(
        name=name,
        price=price,
        price_text="",
        cost=round(price * cost_ratio, 2),
        min_price=0.0,
        category=category,
        is_active=True,
    )
    session.add(dish)
    session.flush()
    return dish


def import_group(session: Session, group_seed: dict) -> tuple[int, int]:
    existing = session.exec(
        select(PackageGroup).where(PackageGroup.name == group_seed["name"])
    ).first()
    if existing:
        print(f"跳过分组: {group_seed['name']}")
        return 0, 0

    group = PackageGroup(
        name=group_seed["name"],
        sort_order=group_seed["sort_order"],
        is_active=True,
    )
    session.add(group)
    session.flush()

    package_count = 0
    dish_create_count = 0
    for package_index, package_seed in enumerate(group_seed["packages"]):
        package = Package(
            group_id=group.id,  # type: ignore[arg-type]
            name=package_seed["name"],
            description="",
            base_price=float(package_seed["price"]),
            default_pricing_mode="fixed",
            dish_count=0,
            sort_order=package_index,
            is_active=True,
            created_by="system-import",
        )
        session.add(package)
        session.flush()

        for dish_index, dish_name in enumerate(package_seed["dishes"]):
            existing_dish = session.exec(select(Dish).where(Dish.name == dish_name)).first()
            dish = existing_dish or find_or_create_dish(session, dish_name)
            if existing_dish is None:
                dish_create_count += 1

            session.add(
                PackageItem(
                    package_id=package.id,  # type: ignore[arg-type]
                    dish_id=dish.id,  # type: ignore[arg-type]
                    default_quantity=1,
                    sort_order=dish_index,
                )
            )

        package.dish_count = len(package_seed["dishes"])
        session.add(package)
        package_count += 1

    session.commit()
    return package_count, dish_create_count


def main() -> None:
    SQLModel.metadata.create_all(engine)

    imported_groups = 0
    imported_packages = 0
    created_dishes = 0

    with Session(engine) as session:
        for group_seed in PACKAGE_GROUPS:
            package_count, dish_count = import_group(session, group_seed)
            if package_count > 0:
                imported_groups += 1
                imported_packages += package_count
                created_dishes += dish_count

    print(
        f"导入完成: 分组 {imported_groups} 个, 套餐 {imported_packages} 个, 自动补菜 {created_dishes} 道"
    )


if __name__ == "__main__":
    main()
