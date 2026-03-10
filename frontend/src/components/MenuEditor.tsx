import { useState, useMemo, useEffect } from 'react';
import {
  Card, Table, InputNumber, Button, Space, Tag, Radio, Statistic,
  Modal, Input, Select, message, Popconfirm, Typography, Spin, Row, Col,
} from 'antd';
import {
  DeleteOutlined, PlusOutlined, DownloadOutlined, ArrowLeftOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import {
  updateMenuItem, addMenuItem, removeMenuItem, updateMenuPricing,
  downloadExcel, getMenuDetail, getDishes, getDishSpecs,
} from '../api/menuApi';
import type { MenuData, MenuItemData, User, Dish, DishSpec } from '../api/menuApi';
import MenuAdjustChat from './MenuAdjustChat';

const { Text, Title } = Typography;

const CATEGORY_ORDER = ['凉菜', '热菜', '汤羹', '主食', '甜品', '点心'];

interface Props {
  menu: MenuData;
  user: User;
  onBack: () => void;
  onMenuUpdated: (menu: MenuData) => void;
}

export default function MenuEditor({ menu, user, onBack, onMenuUpdated }: Props) {
  const [downloading, setDownloading] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [allDishes, setAllDishes] = useState<Dish[]>([]);
  const [dishSearch, setDishSearch] = useState('');
  const [dishLoading, setDishLoading] = useState(false);
  const [specCache, setSpecCache] = useState<Record<number, DishSpec[]>>({});

  const isAdmin = user.role === 'admin';

  const sortedItems = useMemo(() => {
    return [...menu.items].sort((a, b) => {
      const ai = CATEGORY_ORDER.indexOf(a.category);
      const bi = CATEGORY_ORDER.indexOf(b.category);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  }, [menu.items]);

  const refreshMenu = async () => {
    try {
      const updated = await getMenuDetail(menu.id);
      onMenuUpdated(updated);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const fetchSpecsForDish = async (dishId: number) => {
    try {
      const specs = await getDishSpecs(dishId);
      setSpecCache((prev) => ({ ...prev, [dishId]: specs }));
    } catch (e: any) {
      message.error(e.message);
    }
  };

  useEffect(() => {
    const uniqueDishIds = [...new Set(menu.items.map((item) => item.dish_id))];
    uniqueDishIds
      .filter((dishId) => specCache[dishId] === undefined)
      .forEach((dishId) => {
        void fetchSpecsForDish(dishId);
      });
  }, [menu.items, specCache]);

  const handlePriceChange = async (itemId: number, price: number) => {
    try {
      await updateMenuItem(menu.id, itemId, { adjusted_price: price });
      await refreshMenu();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleSpecChange = async (itemId: number, specId: number) => {
    try {
      await updateMenuItem(menu.id, itemId, { spec_id: specId });
      await refreshMenu();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleQuantityChange = async (itemId: number, qty: number) => {
    try {
      await updateMenuItem(menu.id, itemId, { quantity: qty });
      await refreshMenu();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    try {
      await removeMenuItem(menu.id, itemId);
      await refreshMenu();
      message.success('已删除');
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handlePricingModeChange = async (mode: string) => {
    try {
      const updated = await updateMenuPricing(menu.id, { pricing_mode: mode });
      onMenuUpdated(updated);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleFixedPriceChange = async (price: number) => {
    try {
      const updated = await updateMenuPricing(menu.id, { fixed_price: price });
      onMenuUpdated(updated);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDownload = async (format: 'simple' | 'margin') => {
    setDownloading(true);
    try {
      await downloadExcel(menu.id, format);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setDownloading(false);
    }
  };

  const openAddDish = async () => {
    setAddModalOpen(true);
    setDishLoading(true);
    try {
      const dishes = await getDishes({ active_only: true });
      setAllDishes(dishes);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setDishLoading(false);
    }
  };

  const handleAddDish = async (dishId: number) => {
    try {
      await addMenuItem(menu.id, { dish_id: dishId });
      await refreshMenu();
      message.success('已添加');
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const filteredDishes = allDishes.filter((d) => {
    const kw = dishSearch.trim().toLowerCase();
    if (!kw) return true;
    return d.name.toLowerCase().includes(kw) || d.category.includes(kw);
  });

  const tableCount = menu.table_count || 1;
  const perTablePrice = menu.pricing_mode === 'fixed' && menu.fixed_price > 0
    ? menu.fixed_price
    : (menu.total_price / tableCount);
  const totalPrice = menu.pricing_mode === 'fixed' && menu.fixed_price > 0
    ? menu.fixed_price * tableCount
    : menu.total_price;

  const columns = [
    {
      title: '菜名',
      dataIndex: 'dish_name',
      width: 160,
      render: (name: string, record: MenuItemData) => (
        <Space>
          <Tag color={getCategoryColor(record.category)}>{record.category}</Tag>
          {name}
        </Space>
      ),
    },
    {
      title: '规格',
      width: 180,
      render: (_: any, record: MenuItemData) => {
        const specs = specCache[record.dish_id] || [];
        if (specs.length === 0) return '-';

        return (
          <Select
            value={record.spec_id ?? undefined}
            placeholder="选择规格"
            size="small"
            style={{ width: 160 }}
            options={specs.map((spec) => ({
              value: spec.id,
              label: `${spec.spec_name} ¥${spec.price}`,
            }))}
            onChange={(value) => record.id && handleSpecChange(record.id, value)}
          />
        );
      },
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      width: 80,
      render: (qty: number, record: MenuItemData) => (
        <InputNumber
          min={1}
          max={99}
          value={qty}
          size="small"
          onChange={(v) => v && record.id && handleQuantityChange(record.id, v)}
          style={{ width: 60 }}
        />
      ),
    },
    ...(isAdmin ? [{
      title: '成本',
      dataIndex: 'cost',
      width: 80,
      render: (v: number) => <Text type="warning">¥{v}</Text>,
    }] : []),
    {
      title: '售价',
      width: 100,
      render: (_: any, record: MenuItemData) => {
        const price = record.adjusted_price && record.adjusted_price > 0
          ? record.adjusted_price
          : record.price;
        return (
          <InputNumber
            min={0}
            value={price}
            size="small"
            onChange={(v) => v !== null && record.id && handlePriceChange(record.id, v)}
            style={{ width: 90 }}
            precision={0}
          />
        );
      },
    },
    {
      title: '小计',
      dataIndex: 'subtotal',
      width: 80,
      render: (v: number) => `¥${v}`,
    },
    {
      title: '',
      width: 40,
      render: (_: any, record: MenuItemData) => (
        <Popconfirm title="确认删除？" onConfirm={() => record.id && handleDeleteItem(record.id)}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      {/* 左列：菜品表格 */}
      <div style={{ flex: '1 1 70%', minWidth: 0 }}>
        {/* 顶部信息栏 */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <Space>
              <Button type="text" icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
              <Text strong>{menu.customer_name || '贵宾'}</Text>
              <Text type="secondary">{menu.party_size}人</Text>
              {tableCount > 1 && <Text type="secondary">{tableCount}桌</Text>}
              {menu.date && <Text type="secondary">{menu.date}</Text>}
            </Space>
            <Space>
              <Text>定价模式：</Text>
              <Radio.Group
                value={menu.pricing_mode || 'additive'}
                onChange={(e) => handlePricingModeChange(e.target.value)}
                size="small"
              >
                <Radio.Button value="additive">加法价</Radio.Button>
                <Radio.Button value="fixed">固定价</Radio.Button>
              </Radio.Group>
              {menu.pricing_mode === 'fixed' && (
                <InputNumber
                  value={menu.fixed_price}
                  onChange={(v) => v !== null && handleFixedPriceChange(v)}
                  min={0}
                  size="small"
                  style={{ width: 100 }}
                  addonAfter="元/桌"
                />
              )}
            </Space>
          </div>
        </Card>

        {/* 菜品表格 */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <Table
            dataSource={sortedItems}
            columns={columns}
            rowKey={(r) => r.id || r.dish_id}
            size="small"
            pagination={false}
            scroll={{ y: 400 }}
          />
          <Button
            type="dashed"
            block
            icon={<PlusOutlined />}
            onClick={openAddDish}
            style={{ marginTop: 8 }}
          >
            添加菜品
          </Button>
        </Card>

        {/* 汇总栏 */}
        <Card size="small" style={{ marginBottom: 12 }}>
          <Row gutter={24}>
            <Col>
              <Statistic title="单桌价" value={perTablePrice} precision={0} prefix="¥" />
            </Col>
            {tableCount > 1 && (
              <Col>
                <Statistic title={`总价(${tableCount}桌)`} value={totalPrice} precision={0} prefix="¥" />
              </Col>
            )}
            {isAdmin && (
              <Col>
                <Statistic title="总成本" value={menu.total_cost} precision={0} prefix="¥" />
              </Col>
            )}
            <Col>
              <Statistic
                title="毛利率"
                value={menu.margin_rate}
                precision={1}
                suffix="%"
                valueStyle={{ color: menu.margin_rate >= 55 ? '#3f8600' : '#cf1322' }}
              />
            </Col>
          </Row>
        </Card>

        {/* 导出按钮 */}
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleDownload('simple')}
            loading={downloading}
          >
            下载推荐菜单
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleDownload('margin')}
            loading={downloading}
          >
            下载毛利核算表
          </Button>
        </Space>
      </div>

      {/* 右列：AI 对话助手 */}
      <div style={{ flex: '0 0 320px', minHeight: 500 }}>
        <MenuAdjustChat
          menuId={menu.id}
          onMenuUpdated={(updated) => onMenuUpdated(updated)}
        />
      </div>

      {/* 添加菜品 Modal */}
      <Modal
        title="添加菜品"
        open={addModalOpen}
        onCancel={() => { setAddModalOpen(false); setDishSearch(''); }}
        footer={null}
        width={500}
      >
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索菜名或分类"
          value={dishSearch}
          onChange={(e) => setDishSearch(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        <Spin spinning={dishLoading}>
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            {filteredDishes.map((dish) => (
              <div
                key={dish.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 4px',
                  borderBottom: '1px solid #f0f0f0',
                }}
              >
                <Space>
                  <Tag color={getCategoryColor(dish.category)}>{dish.category}</Tag>
                  <span>{dish.name}</span>
                  <Text type="secondary">¥{dish.price}</Text>
                </Space>
                <Button size="small" type="link" onClick={() => handleAddDish(dish.id)}>
                  添加
                </Button>
              </div>
            ))}
          </div>
        </Spin>
      </Modal>
    </div>
  );
}

function getCategoryColor(cat: string): string {
  const map: Record<string, string> = {
    '凉菜': 'cyan', '热菜': 'red', '汤羹': 'blue',
    '主食': 'orange', '甜品': 'pink', '点心': 'purple',
  };
  return map[cat] || 'default';
}
