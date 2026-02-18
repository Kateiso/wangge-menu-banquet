
import { useState, useEffect, useMemo } from 'react';
import { Table, Button, Switch, Modal, Form, InputNumber, Input, Select, message, Tag, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getDishes, updateDish, createDish } from '../api/menuApi';
import type { Dish, User, DishCreateData } from '../api/menuApi';

interface DishManagerProps {
    user: User;
}

const DishManager = ({ user }: DishManagerProps) => {
    const [dishes, setDishes] = useState<Dish[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingDish, setEditingDish] = useState<Dish | null>(null);
    const [searchKeyword, setSearchKeyword] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
    const [form] = Form.useForm();

    const isAdmin = user.role === 'admin';
    const categoryOptions = ['凉菜', '热菜', '汤羹', '主食', '甜品', '点心'];

    const fetchDishes = async () => {
        setLoading(true);
        try {
            const data = await getDishes();
            setDishes(data);
        } catch (e: any) {
            message.error(e.message || "加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDishes();
    }, []);

    const filteredDishes = useMemo(() => {
        const keyword = searchKeyword.trim().toLowerCase();
        return dishes.filter((dish) => {
            const categoryOk = selectedCategory ? dish.category === selectedCategory : true;
            const keywordOk = !keyword || dish.name.toLowerCase().includes(keyword);
            return categoryOk && keywordOk;
        });
    }, [dishes, searchKeyword, selectedCategory]);

    const handleToggleActive = async (dish: Dish, checked: boolean) => {
        try {
            const updated = await updateDish(dish.id, { is_active: checked });
            message.success(`${dish.name} 已${checked ? '上架' : '下架'}`);
            setDishes((prev) => prev.map((d) => (d.id === dish.id ? { ...d, ...updated } : d)));
        } catch (e: any) {
            message.error(e.message || "操作失败");
            fetchDishes();
        }
    };

    const handleToggleTag = async (
        dish: Dish,
        field: 'is_signature' | 'is_must_order',
        checked: boolean
    ) => {
        try {
            const updated = await updateDish(dish.id, { [field]: checked });
            message.success(`${dish.name} 已${checked ? '设置' : '取消'}${field === 'is_signature' ? '招牌菜' : '必点菜'}`);
            setDishes((prev) => prev.map((d) => (d.id === dish.id ? { ...d, ...updated } : d)));
        } catch (e: any) {
            message.error(e.message || "操作失败");
            fetchDishes();
        }
    };

    const openEditModal = (dish: Dish) => {
        setEditingDish(dish);
        form.setFieldsValue({
            name: dish.name,
            category: dish.category,
            price: dish.price,
            cost: dish.cost,
            min_price: dish.min_price,
            price_text: dish.price_text,
            serving_unit: dish.serving_unit || "例",
            serving_split: dish.serving_split || 0,
            is_signature: !!dish.is_signature,
            is_must_order: !!dish.is_must_order,
        });
        setIsModalOpen(true);
    };

    const openCreateModal = () => {
        setEditingDish(null);
        form.resetFields();
        form.setFieldsValue({
            name: '',
            category: '热菜',
            price: undefined,
            price_text: '',
            serving_unit: '例',
            serving_split: 0,
            is_signature: false,
            is_must_order: false,
        });
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setEditingDish(null);
        form.resetFields();
    };

    const handleSave = async () => {
        try {
            const values = await form.validateFields();
            if (editingDish) {
                await updateDish(editingDish.id, values);
                message.success("更新成功");
            } else {
                const payload: DishCreateData = {
                    name: values.name,
                    category: values.category,
                    price: values.price,
                    price_text: values.price_text,
                    serving_unit: values.serving_unit || '例',
                    serving_split: values.serving_split || 0,
                    is_signature: !!values.is_signature,
                    is_must_order: !!values.is_must_order,
                };
                await createDish(payload);
                message.success("新增成功");
            }
            closeModal();
            fetchDishes();
        } catch (e: any) {
            if (e?.errorFields) {
                return;
            }
            message.error(e.message || "保存失败");
        }
    };

    const columns = [
        { title: 'ID', dataIndex: 'id', width: 60, align: 'center' as const },
        {
            title: '菜名',
            dataIndex: 'name',
            width: 150,
            render: (text: string, record: Dish) => (
                <Space>
                    {text}
                    {!record.is_active && <Tag color="default">已下架</Tag>}
                    {record.is_signature && <Tag color="gold">招牌</Tag>}
                    {record.is_must_order && <Tag color="volcano">必点</Tag>}
                </Space>
            )
        },
        {
            title: '分类',
            dataIndex: 'category',
            width: 80,
        },
        { title: '售价描述', dataIndex: 'price_text', width: 120 },
        {
            title: '售价(¥)',
            dataIndex: 'price',
            width: 100,
            render: (price: number) => `¥${price}`
        },
        {
            title: '成本(¥)',
            dataIndex: 'cost',
            width: 100,
            render: (cost: number) => (
                isAdmin ? <span style={{ color: '#faad14', fontWeight: 'bold' }}>¥{cost}</span> : '***'
            )
        },
        {
            title: '底价(¥)',
            dataIndex: 'min_price',
            width: 100,
            render: (min_price: number) => (
                isAdmin ? <span style={{ color: '#fa8c16' }}>¥{min_price}</span> : '***'
            )
        },
        {
            title: '上菜单位',
            dataIndex: 'serving_unit',
            width: 90,
            render: (unit?: string) => unit || '-',
        },
        {
            title: '一开几',
            width: 90,
            render: (_: any, record: Dish) => {
                if (!record.serving_split || record.serving_split <= 0) {
                    return '-';
                }
                return <Tag color="cyan">一开{record.serving_split}</Tag>;
            },
        },
        {
            title: '招牌菜',
            width: 90,
            render: (_: any, record: Dish) => (
                <Switch
                    checked={!!record.is_signature}
                    onChange={(checked) => handleToggleTag(record, 'is_signature', checked)}
                    disabled={!isAdmin}
                />
            ),
        },
        {
            title: '必点菜',
            width: 90,
            render: (_: any, record: Dish) => (
                <Switch
                    checked={!!record.is_must_order}
                    onChange={(checked) => handleToggleTag(record, 'is_must_order', checked)}
                    disabled={!isAdmin}
                />
            ),
        },
        {
            title: '毛利率',
            width: 100,
            render: (_: any, record: Dish) => {
                if (!isAdmin) return '***';
                const margin = ((record.price - record.cost) / record.price * 100).toFixed(1);
                return `${margin}%`;
            }
        },
        {
            title: '状态 / 操作',
            width: 150,
            render: (_: any, record: Dish) => (
                <Space>
                    <Switch
                        checked={record.is_active}
                        onChange={(checked) => handleToggleActive(record, checked)}
                        checkedChildren="上架"
                        unCheckedChildren="下架"
                    />
                    {isAdmin && <Button size="small" type="link" onClick={() => openEditModal(record)}>编辑</Button>}
                </Space>
            )
        }
    ];

    return (
        <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>菜品数据管理 ({filteredDishes.length}/{dishes.length})</h2>
                <Space>
                    <Select
                        allowClear
                        style={{ width: 120 }}
                        placeholder="分类筛选"
                        value={selectedCategory}
                        onChange={(value) => setSelectedCategory(value)}
                        options={categoryOptions.map((c) => ({ value: c, label: c }))}
                    />
                    <Input.Search
                        allowClear
                        placeholder="搜索菜名"
                        style={{ width: 220 }}
                        value={searchKeyword}
                        onChange={(e) => setSearchKeyword(e.target.value)}
                    />
                </Space>
                <Space>
                    <Button onClick={fetchDishes}>刷新列表</Button>
                    {isAdmin && (
                        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
                            新增菜品
                        </Button>
                    )}
                </Space>
            </div>

            <Table
                dataSource={filteredDishes}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={{ pageSize: 50, showSizeChanger: true }}
                size="small"
                scroll={{ y: 600 }}
            />

            <Modal
                title={editingDish ? `编辑: ${editingDish.name}` : "新增菜品"}
                open={isModalOpen}
                onOk={handleSave}
                onCancel={closeModal}
                okText="保存"
                cancelText="取消"
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="name" label="菜名" rules={[{ required: true, message: '请输入菜名' }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="category" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
                        <Select options={categoryOptions.map((c) => ({ value: c, label: c }))} />
                    </Form.Item>
                    <Form.Item name="price" label="售价 (¥)" rules={[{ required: true }]}>
                        <InputNumber style={{ width: '100%' }} precision={2} />
                    </Form.Item>
                    {isAdmin && editingDish && (
                        <Form.Item name="cost" label="成本 (¥)" rules={[{ required: true }]}>
                            <InputNumber style={{ width: '100%' }} precision={2} />
                        </Form.Item>
                    )}
                    {isAdmin && editingDish && (
                        <Form.Item name="min_price" label="底价 (¥) — 宴会模式定价下限">
                            <InputNumber style={{ width: '100%' }} precision={2} min={0} />
                        </Form.Item>
                    )}
                    <Form.Item name="price_text" label="价格描述 (如: 98元/例)" rules={[{ required: true, message: '请输入价格描述' }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="serving_unit" label="上菜单位 (例/只/件/份)">
                        <Input placeholder="如：只" maxLength={8} />
                    </Form.Item>
                    <Form.Item name="serving_split" label="一开几">
                        <Select
                            options={[
                                { value: 0, label: '不适用/不确定' },
                                { value: 2, label: '一开二' },
                                { value: 4, label: '一开四' },
                            ]}
                        />
                    </Form.Item>
                    <Space size={24}>
                        <Form.Item name="is_signature" label="招牌菜" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                        <Form.Item name="is_must_order" label="必点菜" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                    </Space>
                </Form>
            </Modal>
        </div>
    );
};

export default DishManager;
