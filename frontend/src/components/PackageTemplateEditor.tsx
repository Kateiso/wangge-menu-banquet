import { useState, useEffect } from 'react';
import {
  Input, InputNumber, Button, Table, Space, message, Popconfirm,
  Form, Modal, Tag, Typography, Divider, Spin, Select,
} from 'antd';
import { PlusOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import {
  getPackageDetail, updatePackage, addPackageItem, updatePackageItem, removePackageItem,
  getDishes,
} from '../api/menuApi';
import type { PackageDetail, PackageItemDetail, Dish, User } from '../api/menuApi';

const { Text } = Typography;

interface Props {
  packageId: number;
  user: User;
  onClose: () => void;
}

export default function PackageTemplateEditor({ packageId, user }: Props) {
  const [pkg, setPkg] = useState<PackageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editBasePrice, setEditBasePrice] = useState(0);
  const [editingItem, setEditingItem] = useState<PackageItemDetail | null>(null);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [itemSaving, setItemSaving] = useState(false);
  const [itemForm] = Form.useForm();

  // 添加菜品
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [allDishes, setAllDishes] = useState<Dish[]>([]);
  const [dishSearch, setDishSearch] = useState('');
  const [dishLoading, setDishLoading] = useState(false);

  const fetchDetail = async () => {
    setLoading(true);
    try {
      const data = await getPackageDetail(packageId);
      setPkg(data);
      setEditName(data.name);
      setEditDesc(data.description);
      setEditBasePrice(data.base_price);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDetail(); }, [packageId]);

  const handleSaveMeta = async () => {
    try {
      await updatePackage(packageId, {
        name: editName,
        description: editDesc,
        base_price: editBasePrice,
      });
      message.success('套餐信息已更新');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    try {
      await removePackageItem(itemId);
      message.success('已移除');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message);
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
      await addPackageItem(packageId, { dish_id: dishId });
      message.success('已添加');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const openItemModal = (item: PackageItemDetail) => {
    setEditingItem(item);
    itemForm.setFieldsValue({
      default_spec_id: item.default_spec_id ?? undefined,
      default_quantity: item.default_quantity,
      override_price: item.override_price ?? undefined,
    });
    setItemModalOpen(true);
  };

  const closeItemModal = () => {
    setItemModalOpen(false);
    setEditingItem(null);
    itemForm.resetFields();
  };

  const handleSaveItem = async () => {
    if (!editingItem) return;

    try {
      const values = await itemForm.validateFields();
      setItemSaving(true);
      await updatePackageItem(editingItem.id, {
        default_spec_id: values.default_spec_id ?? null,
        default_quantity: values.default_quantity,
        override_price: values.override_price ?? null,
      });
      message.success('套餐项已更新');
      closeItemModal();
      fetchDetail();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e.message || '保存失败');
    } finally {
      setItemSaving(false);
    }
  };

  const isAdmin = user.role === 'admin';

  const columns = [
    {
      title: '菜名',
      dataIndex: 'dish_name',
      width: 160,
      render: (name: string, record: PackageItemDetail) => (
        <Space>
          {name}
          <Tag color="blue">{record.category}</Tag>
        </Space>
      ),
    },
    {
      title: '使用规格',
      dataIndex: 'default_spec_name',
      width: 120,
      render: (v: string) => v || '-',
    },
    {
      title: '数量',
      dataIndex: 'default_quantity',
      width: 60,
      align: 'center' as const,
    },
    {
      title: '套餐售价覆盖',
      dataIndex: 'override_price',
      width: 100,
      render: (v: number | null) => (
        v !== null && v !== undefined ? <Tag color="gold">¥{v}</Tag> : <Text type="secondary">-</Text>
      ),
    },
    {
      title: '当前生效售价',
      dataIndex: 'price',
      width: 100,
      render: (v: number) => <Text strong>¥{v}</Text>,
    },
    ...(isAdmin ? [{
      title: '当前生效成本',
      dataIndex: 'cost',
      width: 100,
      render: (v: number) => <Text type="warning">¥{v}</Text>,
    }] : []),
    {
      title: '操作',
      width: 120,
      render: (_: any, record: PackageItemDetail) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => openItemModal(record)}>
            编辑
          </Button>
          <Popconfirm title="确认移除？" onConfirm={() => handleRemoveItem(record.id)}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const filteredDishes = allDishes.filter((d) => {
    const kw = dishSearch.trim().toLowerCase();
    if (!kw) return true;
    return d.name.toLowerCase().includes(kw) || d.category.includes(kw);
  });

  if (loading && !pkg) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
  if (!pkg) return null;

  return (
    <div>
      {/* 套餐元数据编辑 */}
      <Form layout="vertical" style={{ marginBottom: 16 }}>
        <Form.Item label="套餐名称">
          <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
        </Form.Item>
        <Form.Item label="描述">
          <Input.TextArea rows={2} value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
        </Form.Item>
        <Form.Item label="套餐基础价（固定价模式使用）">
          <InputNumber
            value={editBasePrice}
            onChange={(v) => setEditBasePrice(v || 0)}
            min={0}
            style={{ width: 200 }}
            addonAfter="元/桌"
          />
        </Form.Item>
        <Button type="primary" onClick={handleSaveMeta}>保存套餐信息</Button>
      </Form>

      <Divider />

      <div style={{ marginBottom: 12 }}>
        <Text type="secondary">
          套餐项的“当前生效售价”由使用规格与套餐售价覆盖共同决定，覆盖价只影响当前套餐。
        </Text>
      </div>

      {/* 菜品列表 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Text strong>套餐菜品 ({pkg.items.length}道)</Text>
        <Button size="small" icon={<PlusOutlined />} onClick={openAddDish}>
          添加菜品
        </Button>
      </div>

      <Table
        dataSource={pkg.items}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={false}
      />

      {/* 添加菜品 Modal */}
      <Modal
        title="添加菜品到套餐"
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
                  <span>{dish.name}</span>
                  <Tag>{dish.category}</Tag>
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

      <Modal
        title={editingItem ? `编辑套餐项：${editingItem.dish_name}` : '编辑套餐项'}
        open={itemModalOpen}
        onOk={handleSaveItem}
        onCancel={closeItemModal}
        confirmLoading={itemSaving}
        okText="保存"
        cancelText="取消"
      >
        {editingItem && (
          <Form form={itemForm} layout="vertical">
            <Form.Item label="菜品">
              <Input value={editingItem.dish_name} disabled />
            </Form.Item>
            <Form.Item label="使用规格" name="default_spec_id">
              <Select
                allowClear
                placeholder={editingItem.specs.length > 0 ? '选择使用规格' : '暂无可选规格'}
                disabled={editingItem.specs.length === 0}
                options={editingItem.specs.map((spec) => ({
                  value: spec.id,
                  label: spec.spec_name,
                }))}
              />
            </Form.Item>
            <Form.Item label="数量" name="default_quantity" rules={[{ required: true, message: '请输入数量' }]}>
              <InputNumber min={1} precision={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="套餐售价覆盖" name="override_price">
              <InputNumber min={0} precision={2} style={{ width: '100%' }} addonAfter="元/份" />
            </Form.Item>
            <div style={{ padding: 12, borderRadius: 12, background: '#fafafa' }}>
              <Space direction="vertical" size={4}>
                <Text strong>当前生效售价：¥{editingItem.price}</Text>
                {isAdmin && <Text type="warning">当前生效成本：¥{editingItem.cost}</Text>}
              </Space>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  );
}
